from utils import r, docker_clean

import subprocess
import inspect
import syslog
import random
import ctypes
import time
import sys
import os

#try to import netifaces install if not available via pip or apt-get
try:
    import netifaces

except:

    try:
        subprocess.check_call(['pip', 'install', 'netifaces'])
        import netifaces
    except:
        subprocess.check_call(['apt-get', 'install', 'python-netifaces'])
        import netifaces


#check if we are root
if os.geteuid() != 0:
    print('[*] Script must be run as root! Exiting')
    sys.exit(-1)




libc = ctypes.CDLL('libc.so.6')


class root_ns(object):

    def __init__(self):
        
        self.nics = []
        self.ns = []
        self.name = 'root'
        self.pid = '1'
        self.proc_path = '/proc/%s/ns/' % self.pid
        
        self.mnt_fd = open(self.proc_path + 'mnt', 'ro')
        
        
    def register_ns(self, name, image):

        self.ns.append(container(name, image))

    
    def enter_ns(self,ns='net'):
        """use ctypes to call setns to enter a network namespace
           should check setns source, I remember one libc version
           I had didn't have setns, pretty sure it is just bind mounting
           to set the inode for the current process ns"""

        try:
       
            if ns == 'mnt':
                ret = libc.setns(self.mnt_fd.fileno(), 0)

            else:
                ns_fd = open(self.proc_path + 'net', 'ro')
                ret = libc.setns(ns_fd.fileno(), 0)
                ns_fd.close()

        except:
            print('[*] Failed to setns %s' % self.name)
            ns_fd.close()



    def get_nics(self):
        """return all of the nics in the namespace"""

        self.enter_ns()
        ############################################

        for interface in netifaces.interfaces():
            #we don't care about loopback
            if interface != 'lo':
                yield interface

        ############################################
        self.exit_ns()



    def _get_addrs(self):
        """returns netifaces.ifaddresses for all nics on the container"""

        self.enter_ns()
        #########################################

        for interface in netifaces.interfaces():
            #we don't care about loopback
            if interface != 'lo':    
                addrs = {}
                addrs[interface] = netifaces.ifaddresses(interface)
                yield addrs

        ##########################################
        self.exit_ns()
      


    def get_ips(self):
        """returns the ip addresses for all of the interfaces"""

        self.enter_ns()
        #################################################

        for interface in netifaces.interfaces():
            ips = {}
            #we don't care about loopback
            if interface != 'lo':
                nic = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in nic.keys():
                    ips[interface] = nic[netifaces.AF_INET][0]['addr']
                    yield ips
                    
        #################################################
        self.exit_ns()



    def get_macs(self):
        """ return all of the mac_addrs (or AF_LINK addrs whatever they may be"""

        self.enter_ns()
        #######################################################################################
 
        for interface in netifaces.interfaces():
            #we don't care about loopback
            if interface != 'lo':
                macs = {}
                #set the nic name to the nic AF_LINK address (first one only)
                macs[interface] = netifaces.ifaddresses(interface)[netifaces.AF_LINK][0]['addr']
                yield macs

        #######################################################################################
        self.exit_ns()
 

    def exit_ns(self):
        """return to the root namespace"""        

        #we want exit to always mean go to the root ns
        self.enter_ns()


    def connect(self, container):
        """This will create a ethernet connection to another ns"""

        #creating a local var for the r() call
        pid = container.pid

        #count up our nics for naming scheme of container name + _number
        tmp_n = 0
        for nic in container.nics:
            tmp_n +=1

        #nicname = self.name + '_' + str(tmp_n)
        nicname = container.name + '_' + str(tmp_n)

        r('ip link add $nicname type veth peer name tmp')
        r('ip link set tmp netns $self.pid')
        r('ip link set $nicname netns $pid')

        #need to research more, but pretty sure checksum offloading was
        #screwing up udp packets.....
        #http://lists.thekelleys.org.uk/pipermail/dnsmasq-discuss/2007q3/001506.html
        #this disables offloading....
        if self.name != 'root':
            r('ip netns exec $self.name ethtool -K tmp rx off tx off')

        self.enter_ns()
        ###########################################

        #rename tmp to match veth peer in other ns
        r('ip link set dev tmp name $nicname')
        r('ethtool -K $nicname rx off tx off')

        self.exit_ns()

        #now append the nics to our list and the other containers
        self.nics.append(nicname)
        container.nics.append(nicname)
        return nicname


    def setup_wifi(self, phy):
        """mov phy into this containers network namespace"""

        r('iw phy $phy set netns $self.pid')


    def shutdown(self):
        """only for root ns"""
   
        self.enter_ns() 
        self.ns = []
        docker_clean()

    def __del__(self):
    
        self.mnt_fd.close()


    
class container(root_ns):

    def __init__(self, name, image):

        self.nics = []
        self.name = name

        #start the container and record the container id sleeping randomly to try and improve performance at start
        #time.sleep(random.uniform(1,3))
        self.id = r('docker run -id --privileged --name $name --hostname $name --net=none $image').strip()
        self.pid = r("docker inspect -f '{{.State.Pid}}' $self.id").strip().strip("'")

        self.proc_path = '/proc/%s/ns/' % self.pid
        self.mnt_fd = open(self.proc_path + 'mnt', 'ro')
        self.var_run = '/var/run/netns/' + self.name     

        if not os.path.exists('/var/run/netns'):
            os.mkdir('/var/run/netns')

        netns = self.proc_path + 'net'
        #link this to /var/run/netns so ip tool can identify the network ns
        r('ln -s $netns $self.var_run')


    def dexec(self, cmd):
        """wrapper around docker exec"""
    
        #docker exec needs cmd a seperate args, not a single string
        cmd = 'docker exec -d $self.id ' + cmd

        r(cmd)


    def exit_ns(self):
   
        ns_root.enter_ns()
        ns_root.enter_ns(ns='mnt')


    def __del__(self):
        """stop and delete the container"""

        r('docker rm -f $self.id')

        try:
            #kill container and remove if it isn't a 'root' container
            self.mnt_fd.close()
            ns_root.ns.remove(self)
            #r('docker kill $self.id')
            #r('docker rm -f $self.id')
           
            os.remove(self.var_run)
        except:
            pass


global ns_root
ns_root = root_ns()


def c(name):
    """this function just returns the container object that has a name attribute set to name"""

    try:
        return [d for d in ns_root.ns if getattr(d, 'name') == name][0]

    except:
        return False


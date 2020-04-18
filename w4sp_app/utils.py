import subprocess
import inspect
import socket
import ctypes
import fcntl
import struct
import os


def check_dumpcap():
    """function to ensure that dumpcap has the right capabilities set"""

    dumpcap = r('which dumpcap').strip()
    caps = r('getcap $dumpcap')

    if caps == b'':
        print('[*] Error, capabilities not set on dumpcap, setting capabilities')
        subprocess.call(['setcap', 'CAP_NET_RAW+eip CAP_NET_ADMIN+eip', dumpcap])
        return

    if b'cap_net_admin' and b'cap_net_raw' in caps.split(b'=')[1]:
        print('[*] Caps set correctly on dumpcap')
        return

    else:
        print('[*] Error, capabilities not set correctly on dumpcap, setting capabilities')
        #first lets remove all caps
        r('setcap -r $dumpcap') 
        subprocess.call(['setcap', 'CAP_NET_RAW+eip CAP_NET_ADMIN+eip', dumpcap])
        return




def get_base_subnet(ip):
    """convenience function to get a /24 subnet base"""

    return '.'.join(ip.split('.')[:-1])


#http://stackoverflow.com/questions/24196932/how-can-i-get-the-ip-address-of-eth0-in-python
def get_ip(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])


def r(cmd):
    """simple wrapper so I can copy and paste bash commands
       the gist is it tokenizes a string, pulls out bash vars
       and then it replaces it with the value of the var from the
       callers locals()"""

    #we are going to pull out the calling context local variables 
    ol = inspect.stack()[1][0].f_locals

    #tokenize the command
    cmd = cmd.split(' ')

    for n,s in enumerate(cmd):
        #first check to see if we are referencing an object property (self)
        if '$self' in s:
            #get the self object and return the specified attr
            v = getattr(ol['self'], s[1:].split('.')[1])
            #remove original val
            cmd.remove(s)
            #insert new val in its place
            cmd.insert(n,v)

        #check if there is a regular 'bash' var in the string
        elif '$' in s:
            #pull out the value of the var from the caller locals
            v = ol[s[1:]]
            #remove the original value
            cmd.remove(s)
            #insert our new one in its place
            cmd.insert(n,v)

    print(cmd)
    return subprocess.check_output(cmd)


def docker_build(image_path):
    """this will build all of the lab images"""

    orig_dir = os.getcwd()
    os.chdir(image_path)
    print(os.getcwd())
    curdir = os.getcwd()

    #first we need to build the base image so we can build the rest
    r('docker build -t w4sp/labs:base base')

    for image in next(os.walk( os.path.join(curdir,'.')))[1]:

        #no point in rebuilding the base image
        if image != 'base':
            image_name = 'w4sp/labs:' + image
            r('docker build -t $image_name $image')

    #go back to the working dir
    os.chdir(orig_dir)

def docker_clean():
    """clean up our mess, this will remove all w4sp related containers
    and will try to cleanup all of the network related stuff"""


    #docker rm -f $(docker ps -aq --filter 'label=w4sp=true')

    out = r('docker ps -aq --filter label=w4sp=true').split(b'\n')[:-1]
    for c_id in out:
        r('docker rm -f $c_id')

    for nic in r('ifconfig -a').split(b'\n\n')[:-1]:
        nic = nic.split(b' ')[0]
        if nic != b'docker0' and nic != b'eth0' and nic != b'lo' and b'root' not in nic:
            #try to delete the link, if it fails don't worry about it
            try:
                r('ip link delete $nic')
            except:
                pass

    for netns in r('ip netns').split(b'\n')[:-1]:
        r('ip netns delete $netns')

    #kill old dhclients
    try:
        r('pkill dhclient')
    except:
        pass

    #rename root nic to eth0
    for nic in r('ifconfig -a').split(b'\n\n')[:-1]:
        nic = nic.split(b' ')[0]
        if b'root' in nic:
            try:
                r('ip link set $nic down')
                r('ip link set $nic name eth0')
            except:
                pass

    r('service network-manager start')
    r('service networking restart')
    r('service docker restart')




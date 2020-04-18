import time
import random
from w4sp_app.container import *
from w4sp_app.utils import *

from subprocess import call
from multiprocessing import Process


def runshark(name):
    """runs wireshark in the network namespace of a container by name"""

    if name == 'root':
        p1 = Process(target=r, args=('su - w4sp-lab -c wireshark',))
        p2 = Process(target=r, args=(['xterm', '-fn', '10x20', '-fa', 'Liberation Mono:size=12:antialias=true', '-xrm', 'XTerm.vt100.allowTitleOps: false', '-T', name],))
        p1.start()
        p2.start()
        return 

    #start wireshark in a different process
    wireshark = 'ip netns exec %s su - w4sp-lab -c wireshark' % name
    p = Process(target=r, args=(wireshark,))
    p.start()

    #start terminal in another process
    terminal = ['ip', 'netns', 'exec', name, 'xterm', '-fn', '10x20', '-fa', 'Liberation Mono:size=12:antialias=true', '-xrm', 'XTerm.vt100.allowTitleOps: false', '-T', name]
    p = Process(target=call, args=(terminal,))
    p.start()




def setup_sw(sw, base_ip, clients):
    """make all the connections for sw1 as well as ip for clients
       base ip only works with /24s and you have to specify the .0 address 
       for right now and there is no sanity checking, routers are on .1 and 
       switches are on .2 and all others start at .11"""

    sw = c(sw)
    #would need to add logic here to handle variable length subnetting
    #hardcoded to /24 for now and expects .0 address
    base_ip = base_ip.replace('0/24', '%d/24')
    default_gw = (base_ip % 1).strip('/24')
    sw_ip = base_ip % 2

    print('aaaaarrrrgggggssss')
    print(clients)

    #connect each container/docker up with a veth
    for conn in clients:
        #print conn
        sw.connect(c(conn))

    
    #drop into netns to configure the bridge
    sw.enter_ns()
    #########################################

    #dont need this anymore switched automatically connect stuff
    """
    #now add and configure the bridge
    r('brctl addbr br0')
    for nic in sw.nics:
        r('brctl addif br0 $nic')
        r('ip link set $nic up')

    """

    #getting weird failures
    print('added sleep')
    time.sleep(2)
    r('ip addr add $sw_ip dev br0')
    r('ip link set br0 up')

    #set default gw
    r('route add default gw $default_gw')

    #need to research more, but pretty sure checksum offloading was
    #screwing up udp packets.....
    #http://lists.thekelleys.org.uk/pipermail/dnsmasq-discuss/2007q3/001506.html
    #this disables offloading....
    #r('ethtool -K br0 rx off tx off')


    #########################################
    sw.exit_ns()

    sw_name = sw.name
    #startup dhcpserver
    router_opt = '--dhcp-option=option:router,%s' % default_gw
    min_ip = (base_ip % 100).strip('/24')
    max_ip = (base_ip % 200).strip('/24')
    range_opt = '--dhcp-range=%s,%s' % (min_ip, max_ip)
    r('docker exec $sw_name dnsmasq -E --domain=labs -s labs $router_opt $range_opt')

    #configure the other hosts
    for tmp_n,nicname in enumerate(sw.nics):
        #get the container associated with this nic and drop into ns
        client = c(nicname.split('_')[0])

        
        for nic in [i for i in client.nics if i in sw.nics]:
            client.enter_ns()
            ##########################################################

            c_ip = base_ip % (11 + tmp_n)
            r('ip link set $nic down')
            r('ip addr add $c_ip dev $nic')
            r('ip link set $nic up')
    
            #lets set the routes, hardcoding dfgw to host .1 in a /24
            r('route add default gw $default_gw')
            
            ##########################################################
            client.exit_ns()

    #cleanup by exiting netns

    ##########################################################################      
    sw.exit_ns()



def setup_vrrp(routers):
    """this is going to call vrrpd for every host passed in
        setting the vip to .1 of the /24 subnet"""

    priority_base = 100

    for tmp_n,name in enumerate(routers):
        vid_base = 10
        pri = str(priority_base + tmp_n)
        router = c(name)
  
        for nic in router.nics:
            print('ARGHHHHHH ', nic)
            #enter_ns so we can get currently configured ips
            #maybe consider adding handy get_ip func to container class?
            router.enter_ns()
            ####################

            #get ip for the nic
            vip = get_ip(nic)

            #delete default route set during setup_sw()
            r('ip route del 0/0')

            ####################
            router.exit_ns()

            #parse out the ip and set the last octet to .1 (our gw)
            vip = get_base_subnet(vip) + '.1'
            #now parse out the nic id and get the number to add to vid_base
            #i.e. nic = 'sw1' vid = 10 + 1
            #this ensures that the vid matches on the routers for nic...
            vid = int(''.join([l for l in nic.split('_')[0] if l.isdigit()]))
            vid = str(vid + vid_base)

            #vrrpd -D -i sw2_2 -v 1 -a pw/0xdeadbeef -p 120 10.100.200.1
            r('docker exec $name vrrpd -d 15 -D -i $nic -v $vid -a pw/0xdeadbeef -p $pri $vip')


def setup_inet(inet, h_if, subnet):
    """this will pull the h_if interface into inet and will setup NAT
        then it will set the appropriate default gw for all of the other containers"""

    #make sure we are in the root ns
    ns_root.enter_ns()

    #we are setting our special mac so dfgw doesn't get overwritten
    base_mac = 'de:ad:be:ef:%2x:%2x'
    nic_mac = base_mac % (random.randrange(1,255),random.randrange(1,255))

    inet = c(inet)
    name = inet.name
    #should only have one nic
    inet_nic = inet.nics[0]
    #move host interface into container netns and delete docker0
    r('ip link set $h_if netns $name')
    
    #now delete all other interfaces
    for nic in r('ifconfig -a').split('\n\n')[:-1]:
        nic = nic.split(' ')[0]
        if nic != 'lo':
            r('ip link delete dev $nic')


    inet.enter_ns()
    #########################################################################################

    #set the special mac and get ip addr
    r('ip link set dev $inet_nic address $nic_mac')
    r('dhclient $inet_nic')
    #time.sleep(1)
    sub = subnet.strip('/24') 
    old_gw = get_base_subnet(sub) + '.1'
    #delete the old default gw
    #r('ip route del 0/0')
   
    r('ip route add $subnet via $old_gw')
 
    r('iptables -t nat -A POSTROUTING -o $h_if -j MASQUERADE')
    r('iptables -A FORWARD -i $h_if -o $inet_nic -m state --state RELATED,ESTABLISHED -j ACCEPT')
    r('iptables -A FORWARD -i $inet_nic -o $h_if -j ACCEPT')

    #########################################################################################
    inet.exit_ns()

    r('docker exec -d $name dhclient $h_if')
    


def get_hosts_net(net):

    hosts = []

    for hub in net['hubs']:
        for tag in hub.keys():
            if tag != 'clients':
                for name in hub[tag]:
                    hosts.append(name)
            else:
                for clients in hub[tag]:
                    for tag in clients.keys():
                        for name in clients[tag]:
                            hosts.append(name)
                            
    return hosts


def create_netx(net):
    """connect switches to clients and adds ip addresses and routes"""

    subnet = net['subnet']
    image = 'w4sp/labs:%s'
    sw = ''
    sw_clients = []

    #lets create all containers

    for hub in net['hubs']:
        for tag in hub.keys():
            if tag != 'clients':
                for name in hub[tag]:
                    d_image = image % tag
                    sw = name
                    #if container doesn't already exist create it
                    if not c(name):
                        ns_root.register_ns(name, d_image)
            else:
                for clients in hub[tag]:
                    for tag in clients.keys():
                        for name in clients[tag]:
                            d_image = image % tag
                            #print c, tag
                            sw_clients.append(name)
                            if not c(name):
                                ns_root.register_ns(name, d_image)

        
        #setup_sw(sw, subnet, sw_clients)
        for client in sw_clients:
            c(sw).connect(c(client))

        #we are now going to assign a random ip address to the br0 (dhcp server)
        base = '.'.join(subnet.split('.')[:-1])
        sw_ip = base + '.' + str(random.randrange(2,99)) + '/24'

        c(sw).enter_ns()
        #################################

        #getting random failures, adding sleep
        time.sleep(2)
        r('ip addr add $sw_ip dev br0')    
    
        #################################
        c(sw).exit_ns()
       

        sw = ''
        sw_clients = []



def create_net(net):
    """connect switches to clients and adds ip addresses and routes"""

    subnet = net['subnet']
    image = 'w4sp/labs:%s'
    sw = ''
    sw_clients = []

    #lets create all containers

    for hub in net['hubs']:
        for tag in hub.keys():
            if tag != 'clients':
                for name in hub[tag]:
                    d_image = image % tag
                    sw = name
                    #if container doesn't already exist create it
                    if not c(name):
                        ns_root.register_ns(name, d_image)
            else:
                for clients in hub[tag]:
                    for tag in clients.keys():
                        for name in clients[tag]:
                            d_image = image % tag 
                            #print c, tag
                            sw_clients.append(name)
                            if not c(name):
                                ns_root.register_ns(name, d_image)

        #print('[*] hub: %s, client: %s' % (sw, ','.join(sw_clients)))
        setup_sw(sw, subnet, sw_clients)
        sw = ''
        sw_clients = []


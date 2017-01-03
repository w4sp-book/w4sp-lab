import sys
import time
import syslog
import netifaces

import subprocess as sp

from threading import Thread



def nics_nbr():
    """returns nics attached to a bridge, screenscraping brctl show"""

    showbr = sp.check_output(['brctl', 'show'])

    for line in showbr.split('\n'):
        nic = line.split('\t')[-1]

        if len(nic) > 0 and nic != 'interfaces':
            yield nic



def connector():
    """meant to be spun off in a different thread so it will continue to connect devices
        all this does is continually poll for new nics that haven't been added to br0 yet.
        when it finds ones it adds it to br0 and brings the interface up"""

    while True:

        for nic in netifaces.interfaces():
            if nic not in nics_nbr() and nic != 'lo' and nic != 'br0' and nic != 'tmp':
                try:
                    sp.check_call(['brctl', 'addif', 'br0', nic])
                    sp.check_call(['ip', 'link', 'set', nic, 'up'])

                except:
                    print('[*] Error failed to add interface to bridge')
                    time.sleep(1)

        time.sleep(1)



if __name__ == "__main__":

    #if there is no br0 device we need to create it
    if 'br0' not in netifaces.interfaces():
        try:
            sp.check_call(['brctl', 'addbr', 'br0'])
            #had an issue where router interface would flap on the bridges with stp enabled
            #sp.check_call(['brctl', 'stp', 'br0', 'on'])
            #sp.check_call(['brctl', 'setfd', 'br0', '2'])
            #sp.check_call(['brctl', 'sethello', 'br0', '10'])

            sp.check_call(['ip', 'link', 'set', 'br0', 'up'])
            #disable checksum offloading
            sp.check_call(['ethtool', '-K', 'br0', 'rx', 'off', 'tx', 'off'])

        except:
            syslog.syslog('[*] Error trying to create bridge')
            #just bail and supervisord should try to restart
            sys.exit(-1)

    #add localhost entry and google to /etc/resolv.conf - for dnsmasq
    #sp.check_call(['bash', '-c', 'echo nameserver 127.0.0.1 >> /etc/resolv.conf'])
    #sp.check_call(['bash', '-c', 'echo nameserver 8.8.8.8 >> /etc/resolv.conf'])

    #kickoff the connector thread
    p = Thread(target=connector)
    p.start()

    #while br0 does not have an ip
    ip = False
    while not ip:
        time.sleep(1)    
        nic = netifaces.ifaddresses('br0')
        if netifaces.AF_INET in nic.keys():
            ip = nic[netifaces.AF_INET][0]['addr']
    
    #add localhost entry and google to /etc/resolv.conf - for dnsmasq
    #sp.check_call(['bash', '-c', 'echo nameserver 127.0.0.1 >> /etc/resolv.conf'])
    #sp.check_call(['bash', '-c', 'echo nameserver 8.8.8.8 >> /etc/resolv.conf'])
                
    #we should have an ip on br0 now
    base = '.'.join(ip.split('.')[:-1])
    #we are creating dhcp ranges, we are assuming we
    #are dealing with a /24 subnet (so swapping out last octet
    #first range is for routers (who won't be gettting dfgw option
    r_min = base + '.20'
    r_max = base + '.99'
    #these are for clients who are going to get a dfgw option of '.1'
    c_min = base + '.100'
    c_max = base + '.200'
    #dfgw for clients
    dhcp_gw = base + '.1'

    #lets go ahead and add our dfgw now so we can query upstream dns later
    sp.check_call(['route', 'add', 'default', 'gw', dhcp_gw])

    #any mac starting with deadbeef is tagged as a router
    dhcp_hosts = '--dhcp-host=de:ad:be:ef:*:*,set:routers'
    #give routers the router dhcp range ip
    dhcp_range_r = '--dhcp-range=tag:routers,%s,%s' % (r_min, r_max)
    #give anyone not a router the client dhcp ip range
    dhcp_range = '--dhcp-range=tag:!routers,%s,%s' % (c_min, c_max)
    #anyone not routers have a dfgw option set to '.1'
    dhcp_opt = '--dhcp-option=tag:!routers,option:router,%s' % dhcp_gw
    #routers don't get a dfgw (router is dhcp option 3)
    dhcp_opt_r = '--dhcp-option=tag:routers,3'

    #finally run dnsmasq
    sp.check_call(['dnsmasq', 
                    '-E', '--domain=labs', 
                    '-s', 'labs',
                    dhcp_hosts, '--server=8.8.8.8', 
                    dhcp_range_r, dhcp_range, 
                    dhcp_opt, dhcp_opt_r])


    #we should just hang out here as our thread is going to continue to run


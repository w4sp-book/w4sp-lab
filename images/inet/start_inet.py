import time
import random
import netifaces

import subprocess as sp




if __name__ == "__main__":
    """this sets up the vrrpd instances"""

    host_nic = False
    inet_nic = False

    while not host_nic or not inet_nic:

        for nic in netifaces.interfaces():
            #we don't care about loopback
            if nic != 'lo' and 'root' not in nic:
                #we need to set our special macs so dfgw doesn't get overwritten
                #could add more randomness here but I think we will be ok
                base_mac = 'de:ad:be:ef:%2x:%2x'
                nic_mac = base_mac % (random.randrange(1,255),random.randrange(1,255))
                sp.check_call(['ip', 'link', 'set', 'dev', nic, 'address', nic_mac])
                #now delete whatever default gw we currently have as from now on dhclient shouldn't update it
                try:
                    sp.check_call(['ip', 'route', 'del', '0/0'])

                except:
                    pass

                inet_nic = nic
               
            elif nic != 'lo' and 'root' in nic:
                host_nic = nic

        time.sleep(2)



    sp.check_call(['iptables', '-t', 'nat', '-A', 'POSTROUTING', '-o', host_nic, '-j' 'MASQUERADE'])
    sp.check_call(['iptables', '-A', 'FORWARD', '-i', host_nic, '-o', inet_nic, '-m', 'state', '--state', 'RELATED,ESTABLISHED', '-j', 'ACCEPT'])
    sp.check_call(['iptables', '-A', 'FORWARD', '-i', inet_nic, '-o', host_nic, '-j', 'ACCEPT'])
 





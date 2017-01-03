import time
import random
import logging
import traceback
import netifaces

import subprocess as sp



logging.basicConfig(filename="vrrd_logger.log", level=logging.DEBUG)


def setup_vrrpd(nic):

    logging.debug('[*] Setting up vrrpd on %s' % nic)
    addrs = netifaces.ifaddresses(nic)

    ip = addrs[netifaces.AF_INET][0]['addr']
    logging.debug('[*] nic %s has ip %s' % (nic, ip))
    base = '.'.join(ip.split('.')[:-1])
    #set the vip to '.1'
    vip = base + '.1'

    #lets add up the ip to derive our vrid
    adder = 0
    for i in vip.split('.'):
	adder += int(i)

    #so this probably isn't sound...but
    #vrid is 1-255, so doing addr % 255 to get unique
    #vrid per nic/ip
    vrid = str(adder % 255)

    #this may end up biting me...but just randomizing priority
    prio = str(random.randrange(1,255))

    #vrrpd -D -i sw2_2 -v 1 -a pw/0xdeadbeef -p 120 10.100.200.1
    logging.debug('[*] Calling vrrpd on nic %s' % nic)
    sp.check_call(['vrrpd', '-D', '-i', nic, '-v', vrid, '-a', 'pw/0xdeadbeef', '-p', prio, vip])



if __name__ == "__main__":
    """this sets up the vrrpd instances"""

    setup = False
    vrrpds = []
    dfgw = False
    base_mac = 'de:ad:be:ef:%2x:%2x'

    while not setup:
        #logging.debug('stating checking for stuff')

        for nic in netifaces.interfaces():
            #we don't care about loopback
            if nic != 'lo' and nic not in vrrpds:
                logging.debug('[*] for nics nic = %s and vrrpds = %s' % (nic, vrrpds))
                #we need to set our special macs so dfgw doesn't get overwritten
                #could add more randomness here but I think we will be ok
                nic_mac = base_mac % (random.randrange(1,255),random.randrange(1,255))

                sp.check_call(['ip', 'link', 'set', nic, 'down'])
                sp.check_call(['ip', 'link', 'set', 'dev', nic, 'address', nic_mac])
                sp.check_call(['ip', 'link', 'set', nic, 'up'])

                with open('/etc/dhcp/dhclient.conf', 'a') as f:
                    f.write('send dhcp-client-identifier 1:%s;' % nic_mac)

                #was getting random failures so making sure mac matches before continuing
                match = False
                while not match:
                    logging.debug('[*] Checking mac for nic %s' % nic)
                    if 'de:ad:be:ef' in netifaces.ifaddresses(nic)[17][0]['addr']:
                        logging.debug('[*] Matched nic %s' % nic)
                        match = True

                    else:
                        logging.debug('[*] mac on nic %s did not stick, trying again' % nic)
                        nic_mac = base_mac % (random.randrange(1,255),random.randrange(1,255))
                        sp.check_call(['ip', 'link', 'set', nic, 'down'])
                        sp.check_call(['ip', 'link', 'set', 'dev', nic, 'address', nic_mac])      
                        sp.check_call(['ip', 'link', 'set', nic, 'up'])

                #we want to delete any default gw that may get set
                try:
                    sp.check_call(['ip', 'route', 'del', '0/0'])

                except:
                    pass

                if netifaces.AF_INET in netifaces.ifaddresses(nic).keys():
                    setup_vrrpd(nic)
                    vrrpds.append(nic)

                #else we should try dhclient again
                else:
                    logging.debug('[*] Calling dhclient for each nic')
                    sp.check_call(['dhclient', nic])
                    setup_vrrpd(nic)
                    vrrpds.append(nic)



        #keep checking to see if we can ping inet, if so set it as our default gw
        #to the host 'inet'
        #logging.debug('[*********] dfgw is %s' % dfgw)
        if not dfgw:
            try:
                logging.debug('[********] Checking if I can ping inet....')
                sp.check_call(['ping', '-c', '1', 'inet'])
                sp.check_call(['route', 'add', 'default', 'gw', 'inet'])
                dfgw = True
                 
            except Exception, err:
                logging.debug('[*******] Failed to ping inet')
                logging.debug(traceback.format_exc())
                pass

        time.sleep(2)


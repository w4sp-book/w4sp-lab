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
        when it finds ones it adds it to br0 and brings the interface up -- extended to work with wireless"""

    found_nic = False

    while not found_nic:
        #ignore iw warning and screenscrape to get interface names

        try:
            #get the first phy interface
            phy = sp.check_output(['iw', 'list']).split()[1].strip()    
            #get the first dev interface
            dev = sp.check_output(['iw', 'dev']).split()[2].strip()

            if dev and phy:
                found_nic = True

        except:
            time.sleep(0.01)


    #at this point the wifi nic should be in the namespace and we have references to the name
    cmd1 = 'iw dev %s del' % dev
    cmd2 = 'iw phy %s interface add __ignore_me type station' % phy
    cmd3 = 'iw phy %s interface add mon0 type monitor' % phy

    #delete the default created station VIP
    sp.call(cmd1.split(' '))
    #create a VIP station called __ignore_me to be used with hostapd
    sp.call(cmd2.split(' '))
    #add a monitor mode VIP called mon0
    sp.call(cmd3.split(' '))

    no_addif = ['lo', 'br0', 'tmp', '__ignore_me', 'wlan0', 'mon0']


    #this should connect whatever nic is attached to sw2
    while True:

        for nic in netifaces.interfaces():
            if nic not in nics_nbr() and nic not in no_addif:
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
            sp.check_call(['brctl', 'stp', 'br0', 'on'])
            sp.check_call(['brctl', 'setfd', 'br0', '2'])
            sp.check_call(['brctl', 'sethello', 'br0', '10'])

            sp.check_call(['ip', 'link', 'set', 'br0', 'up'])
            #disable checksum offloading
            sp.check_call(['ethtool', '-K', 'br0', 'rx', 'off', 'tx', 'off'])

        except:
            syslog.syslog('[*] Error trying to create bridge')
            #just bail and supervisord should try to restart
            sys.exit(-1)

    #kickoff the connector thread
    p = Thread(target=connector)
    p.start()


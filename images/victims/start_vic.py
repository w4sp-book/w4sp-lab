import re
import sys
import time
import socket
import string
import random
import requests
import netifaces
import smbclient
import telnetlib
import subprocess as sp

from ftplib import FTP
from threading import Thread
from scapy.all import srp, Ether, ARP, IP, UDP 



def get_baseip():
    """this just gets the base ip for the nic other than lo"""

    nic = socket.gethostname() + '_0'
    addrs = netifaces.ifaddresses(nic)

    ip = addrs[netifaces.AF_INET][0]['addr']
    return '.'.join(ip.split('.')[:-1])



def arp_scan():
    """send a broadcast arp"""

    nic = socket.gethostname() + '_0'

    while True:
        ips = []

	base = get_baseip()
	for n in xrange(1,255):
		ip = base + '.' + str(n)
		ips.append(ip)

	random.shuffle(ips)
	for ip in ips:
		time.sleep(random.uniform(2,10))        
		#send a raw ethernet arp packet
		srp(Ether(dst='ff:ff:ff:ff:ff:ff')/ARP(pdst=ip),timeout=0.001, iface=nic)

        time.sleep(1)

def do_udp():
    """spam out some random UDP broadcasts"""

    nic = socket.gethostname() + '_0'

    while True:    
        rnd = random.uniform(5,10)
        time.sleep(rnd)
        payload = '12345678' + str(rnd)
        #build and send the packet
        srp(Ether(dst='ff:ff:ff:ff:ff:ff')/
            IP(dst="255.255.255.255")/
            UDP(sport=9898,dport=9898)/
            payload,timeout=0.001,
            iface=nic)
        
    

def broad_ping():
    """sends out a broadcast ping"""

    time.sleep(random.uniform(1,3))
    base = get_baseip()
    ip = base + '.' + str(255)

    rnd = str(random.randint(15,20))

    cmd = ['ping', '-i', rnd, '-b', ip]
    sp.call(cmd)



#http://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits-in-python
get_randstr = lambda N: ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(N))



def nmblookup():
    """uses nmblookup to trigger netbios requests"""

    while True:
        rnd = random.uniform(5,10)
        time.sleep(rnd)
        sp.call(['nmblookup', get_randstr(int(rnd))])



def make_http():
    """going to generate http traffic to various sites"""

    #some random urls to go out and hit at random
    urls = [ 'https://ftp1/',
            'http://ftp1/', 
            'https://ftp2/',
            'http://ftp2/']

    while True:
        random.shuffle(urls)
        for url in urls:
            try:
                time.sleep(random.uniform(30,60))
                #don't want to verify the ssl certificate
                requests.get(url, verify=False)
            except:
                print('[*] Error couldn''t connect')


ftps = ['ftp1', 'ftp2']
user = 'w4sp'
passwd = 'w4spbook'


def do_ftps():
    """this will make ftp requests to the ftp server"""    

    while True:
        rnd = random.uniform(5,10)
       
        for ftp in ftps:
            time.sleep(rnd)
            try:
                ftp = FTP(ftp, 'w4sp', 'w4spbook')
                time.sleep(1)
                ftp.dir()
                time.sleep(1)
                ftp.quit()
            except:
                print('[*] Failed to do ftp')

        

def do_telnets():
    """telnets to machines and just does ps -ef"""

    while True:

        for tel in ftps:
            time.sleep(random.uniform(10,15))
            try:
                tn = telnetlib.Telnet(tel)
                tn.read_until('login: ')
                tn.write(user + '\n')
                tn.read_until('Password: ')
                tn.write(passwd + '\n')
                tn.write('ps -ef\n')
                tn.write('exit\n')
            except:
                print('[*] Failed to do telnet')
            
                
def do_smb():
    """reaches out and connects to a secured smb share and reads a file"""

    smbs = ['smb1', 'smb2']

    while True:

        for smb_host in smbs:

            time.sleep(random.uniform(10,20))
            smb = smbclient.SambaClient(server=smb_host, share='secured', username='w4sp', password='w4spbook')
            smb.listdir('/')
            time.sleep(1)

            with smb.open('/secret.txt') as f:
                f.read()

            smb.close()
            del(smb)



def do_dhcpinform():
    """randomly does a dhcpinform request"""

    """
    #get current dhcp server
    rip = re.compile("\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")

    s_ip = False
    while not s_ip:

        with open('/var/lib/dhcp/dhclient.leases') as f:
            for line in f:
                if 'dhcp-server-identifier' in line:
                    s = rip.search(line)
                    s_ip = line[s.start():s.end()]
                    break
    """
            
    while True:

        time.sleep(random.uniform(10,20))

        for nic in netifaces.interfaces():
            if nic != 'lo':
                addrs = netifaces.ifaddresses(nic)
                c_ip = addrs[netifaces.AF_INET][0]['addr']


        try:
            #dhcping -i -c 192.100.200.198 -s 192.100.200.77
            sp.call(['dhcping', '-i', '-c', c_ip, '-s', '255.255.255.255'])

        except:
            pass
 


def do_dhcpinform2():
    """this does a dhcpinform to the broadcast address"""

    while True:
        time.sleep(random.uniform(10,20))

        sp.call(['dhcping', '-i', '-s', '255.255.255.255'])


if __name__ == "__main__":

    threads = []

    #create the arp scan thread
    arps = Thread(target=arp_scan)
    threads.append(arps)
    #create the broadcast udp'er
    udp = Thread(target=do_udp)
    threads.append(udp)          
    #create the ping broadcaster
    pinger = Thread(target=broad_ping)
    threads.append(pinger)
    #create the nmblookup thread
    nmb = Thread(target=nmblookup)
    threads.append(nmb)
    #create the http'er thread
    http = Thread(target=make_http)
    threads.append(http)
    #create the ftp thread
    ftper = Thread(target=do_ftps)
    threads.append(ftper)
    #create the telnet'er thread
    telnet = Thread(target=do_telnets)
    threads.append(telnet)
    #create the smber thread
    smber = Thread(target=do_smb)
    threads.append(smber)
    #create the dhcpinform thread
    informer = Thread(target=do_dhcpinform)
    threads.append(informer)

    has_ip = False
    #wait until there is an IP addr
    while not has_ip:
        for nic in netifaces.interfaces():
            if nic != 'lo':
                #get a dict of ifaddresses for the interface and see if it has an IP addr (#2 key)
                has_ip = netifaces.ifaddresses(nic).has_key(2)
    
        time.sleep(random.uniform(20,30))    

    #mix it up so everyone starts a different one
    random.shuffle(threads)
    for t in threads:
        time.sleep(random.uniform(2,5))
        t.start()




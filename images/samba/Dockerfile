#import from w4sp base
FROM w4sp/labs:base

#install samba
RUN apt-get install -y samba

#set a samba password for the w4sp user to w4spbook
RUN PASS=w4spbook ; echo ${PASS} | tee - | smbpasswd -a -s w4sp

#add the smbgrp group and add w4sp to the group
RUN addgroup smbgrp && usermod -a -G smbgrp w4sp

#create the file share directories
RUN mkdir -p /file_shares/anon && mkdir -p /file_shares/secured

#set perms for anonymous share
RUN chmod -R 0755 /file_shares/anon && chown -R nobody:nogroup /file_shares/anon
#set perms for w4sp user
RUN chmod -R 0755 /file_shares/secured && chown -R w4sp:smbgrp /file_shares/secured

#add configs
ADD smb.conf /etc/samba/smb.conf
ADD supervisor_samba.conf /etc/supervisor/conf.d/supervisor_samba.conf

#going to create some files
RUN /bin/bash -c "echo 'super secret' >> /file_shares/secured/secret.txt"
RUN /bin/bash -c "echo 'bar' >> /file_shares/secured/tmp.txt"



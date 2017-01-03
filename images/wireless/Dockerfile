#FROM kalilinux/kali-linux-docker
FROM w4sp/labs:base

#RUN apt-get -y update && apt-get -y upgrade

#install hostapd and dnsmasq
#RUN apt-get -y install hostapd dnsmasq supervisor

RUN apt-get -y install hostapd iw

#add our configuration files and startup scripts
ADD hostapd_clear.conf hostapd_clear.conf
ADD hostapd_wpa2.conf hostapd.wpa2.conf
ADD setup_wifi.py setup_wifi.py

#add the supervisor.conf and scripts
ADD supervisor_wifi.conf /etc/supervisor/conf.d/supervisor_wifi.conf




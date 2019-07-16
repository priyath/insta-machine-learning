#!/bin/sh

#change permissions /var/lib/tor

chown root:root /var/lib/tor

for i in 0 1 2 3 4 5 6 7 8 9
do

#LOG NEEDED FOLDERS

rm -r /var/log/privoxy$i

rm -r /var/lib/tor$i

chown privoxy:adm /var/log/privoxy$i

#TOR CONFIGS

rm /etc/tor/torrc$i

#PRIVOXY CONFIGS

rm /etc/privoxy/config$i

done
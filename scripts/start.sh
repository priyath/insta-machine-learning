#!/bin/sh

for i in 0 1 2 3 4 5 6 7 8 9
do

#RUN TOR

tor -f /etc/tor/torrc$i &

#RUN PRIVOXY

/usr/sbin/privoxy --user privoxy /etc/privoxy/config$i

done
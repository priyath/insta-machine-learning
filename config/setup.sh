#!/bin/sh

#change permissions /var/lib/tor

chown root:root /var/lib/tor

for i in 0 1 2 3 4 5 6 7 8 9
do

#TOR CONFIGS

if [ ! -f /etc/tor/torrc$i ]; then

touch /etc/tor/torrc$i

echo 'SocksPort 9'$(($i))'50' >> /etc/tor/torrc$i

echo 'DataDirectory /var/lib/tor'$i >> /etc/tor/torrc$i

echo 'ControlPort 9'$(($i))'51' >> /etc/tor/torrc$i

echo 'HashedControlPassword 16:3AF1F35D3C474BF460F2C6ACCF54D916BB7958DFE22D8100E9F09F9E3E' >> /etc/tor/torrc$i

echo 'CookieAuthentication 1' >> /etc/tor/torrc$i

fi

#PRIVOXY CONFIGS

if [ ! -f /etc/privoxy/config$i ]; then

touch /etc/privoxy/config$i

echo 'logdir /var/log/privoxy'$i >> /etc/privoxy/config$i

echo 'listen-address localhost:8'$i'18' >> /etc/privoxy/config$i

echo 'forward-socks5t / 127.0.0.1:9'$(($i))'50 .' >> /etc/privoxy/config$i

fi

done

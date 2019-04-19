from urllib.request import ProxyHandler, build_opener, install_opener, Request, urlopen
from stem import Signal
from stem.control import Controller
import concurrent.futures
import time
import configparser

#load configurations from  config.ini
config = configparser.ConfigParser()
config.read("config.ini")
proxy_ports = config.get('Ports', 'proxy_ports').split(',')
control_ports = config.get('Ports', 'control_ports').split(',')
MAX_TOR_INSTANCES = int(config.get('Instances', 'tor_instances').strip())

QUIT_APP = False

headers = {
  'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'}

def build_proxy_list():
  proxy_list = []
  for i in range(len(proxy_ports)):
    proxy_port = proxy_ports[i].strip()
    control_port = control_ports[i].strip()
    proxy_list.append({
      "proxy_port": proxy_port,
      "control_port": control_port
    })
  return proxy_list

proxy_data= build_proxy_list()

max_workers = 10
number_of_ip_rotations = 10000
wait_time = 5

def renew_connection(control_port):
  with Controller.from_port(port=control_port) as controller:
    controller.authenticate(password='your_password')
    controller.signal(Signal.NEWNYM)
    controller.close()

def open_url(url, proxy_port):
  def _set_url_proxy():
    proxy_support = ProxyHandler({'http': '127.0.0.1:' + str(proxy_port)})
    opener = build_opener(proxy_support)
    install_opener(opener)

  _set_url_proxy()
  request = Request(url, None, headers)
  return urlopen(request).read().decode('utf-8')

def rotate_ip(proxy_port, control_port, thread_number):
  print(proxy_port)
  ip = open_url('http://icanhazip.com/', proxy_port)
  print('[Thread' + str(thread_number) + ':' + str(proxy_port) + '] My first IP: {}'.format(ip).strip())

  # Cycle through the specified number of IP addresses via TOR
  for i in range(0, number_of_ip_rotations):
    if QUIT_APP:
      break

    old_ip = ip
    seconds = 0

    renew_connection(control_port)
    # Loop until the 'new' IP address is different than the 'old' IP address,
    # It may take the TOR network some time to effect a different IP address
    while ip == old_ip:
      time.sleep(wait_time)
      seconds += wait_time

      if int(seconds) > 20:
        print('[Thread' + str(thread_number) + ':' + str(proxy_port) + '] Wait time too long. Renewing connection..')
        renew_connection(control_port)

      print('[Thread' + str(thread_number) + ':' + str(proxy_port) + '] {} seconds elapsed awaiting a different IP '
                                                                     'address.'.format(seconds))

      ip = open_url('http://icanhazip.com/', proxy_port)

    print('[Thread' + str(thread_number) + ':' + str(proxy_port) + '] My new IP: {}'.format(ip).strip())


def setup():
  future_set = []

  with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
    thread_number = 0
    for proxy in proxy_data:
      thread_number = thread_number + 1
      if thread_number > MAX_TOR_INSTANCES:
        break
      p_port = int(proxy['proxy_port'])
      c_port = int(proxy['control_port'])
      future_set.append(executor.submit(rotate_ip, p_port, c_port, thread_number))

    while (True):
      print('[Main Thread] Keep alive. Ctrl + C to quit')
      time.sleep(10)


if __name__ == "__main__":
  try:
    setup()
  except KeyboardInterrupt:
    print('Quitting.. cleaning up worker threads..')
    QUIT_APP = True


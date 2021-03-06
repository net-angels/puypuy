import pycurl
import socket
import lib.puylogger
import lib.pushdata

# import requests
# from requests.auth import HTTPBasicAuth


class CurlBuffer:
   def __init__(self):
       self.contents = ''

   def body_callback(self, buf):
       self.contents = self.contents + buf

# def httpget2(name, url, auth=None):
#     try:
#         if auth is not None:
#             response = requests.get(url, auth=HTTPBasicAuth(auth.split(':')[0], auth.split(':')[1]))
#         else:
#             response = requests.get(url)
#         return response.content
#     except Exception as err:
#         lib.puylogger.print_message(name + ' ' + str(err))
#         lib.pushdata.print_error(name, err)


def httpget(name, url, auth=None):
    try:
        t = CurlBuffer()
        c = pycurl.Curl()
        c.setopt(c.URL, url)
        c.setopt(c.WRITEFUNCTION, t.body_callback)
        c.setopt(c.FAILONERROR, True)
        c.setopt(pycurl.CONNECTTIMEOUT, 10)
        c.setopt(pycurl.TIMEOUT, 10)
        c.setopt(pycurl.NOSIGNAL, 5)
        if auth is not None:
            c.setopt(pycurl.USERPWD, auth)
        c.perform()
        c.close()
        return t.contents
    except Exception as err:
        if name == 'check_oddeye':
            lib.pushdata.print_error(name, err)
        else:
            lib.puylogger.print_message(name + ' ' + str(err))
            lib.pushdata.print_error(name, err)


def socketget(name, buff, host, port, message):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((host, port))
        s.send(message)
        raw_data = s.recv(buff)
        s.close()
        return raw_data
    except Exception as err:
        lib.puylogger.print_message(name + ' ' + str(err))
        lib.pushdata.print_error(name, err)

# def hostname():
#     return socket.getfqdn()
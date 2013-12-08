import urllib.parse
import urllib.request
import time

username = 'asis'
password = 'asis'

tm = 60


url = "http://localhost:9990/login"
values = {'username': username, 'password': password}
data = urllib.parse.urlencode(values)
binary_data = data.encode('ascii')
req = urllib.request.Request(url, binary_data)
page = urllib.request.urlopen(req).read()
print(page)
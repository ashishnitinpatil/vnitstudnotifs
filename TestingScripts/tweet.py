import urllib
#values = {'username':'asis','password':'asis'}
#request.urlopen("https://www.twitter.com/",data={'signin-email':'ashishnpatil','signin-password':''})
values = {'session[username_or_email]':'VNITStudNotifs','session[password]':''}
data = urllib.parse.urlencode(values)
#url = "http://localhost:9990/login"
url = "http://www.twitter.com/login"
binary_data = data.encode('ascii')
req = urllib.request.Request(url, binary_data)
response = urllib.request.urlopen(req)
the_page = response.read()
text = the_page.decode("utf8")
print(text)
hist_page = request.urlopen("http://www.twitter.com/").read()
print(hist_page)

from urllib import urlopen
import urlparse
main_url = "http://www.vnit.ac.in"
vnit_homepage = urlopen(main_url).read()
from bs4 import BeautifulSoup
vnit_home = BeautifulSoup(vnit_homepage)
for spans in vnit_home.findAll('span'):
    if spans.text.lower() == "student notice board":
        notice_board = spans.previous.get('href')
        break
else:
    print "Error"
snb_url = urlparse.urljoin(main_url, notice_board)
print snb_url


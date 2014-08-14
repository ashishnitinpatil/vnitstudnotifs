import urllib
import logging
import datetime
import tweepy
import bitly_api
import re
import urlparse
from bs4 import BeautifulSoup
from google.appengine.api import memcache
from django.conf import settings


def get_page(url, proxy=False):
    """Fetches the content displayed on the page of given url."""

    # page = urlfetch.fetch(url).content
    # logging.info(page)
    last_checked = datetime.datetime.utcnow() + datetime.timedelta(hours=5.5)
    memcache.set("last_checked", last_checked)
    # Crude Proxy setup to get around Project Honeypot bans.
    if proxy:
        memcache.set("proxy", "YES")
        proxy_url_main = 'http://vnitstudnotb.herokuapp.com/get/'
        dont = False
        if url in ['http://www.vnit.ac.in', 'http://www.vnit.ac.in/']:
            what = '1'
        elif 'id=448' in url:
            what = '2'
        elif 'id=612' in url:
            what = '3'
        else:
            dont = True
            logging.critical('New url for proxy!!')
        if dont:
            return ""
        else:
            url = proxy_url_main + what
    try:
        page = urllib.urlopen(url)
        content = page.read()
        if 'Your IP address has recently been detected as' in content:
            logging.critical("Suspected honeypot blocking!!")
            memcache.set("blocking", "YES")
            assert False
        logging.info("Successfully fetched url - %s"%url)
        return str(content)
    except:
        logging.error('Unable to fetch Url - %s'%url)
        return ""


def get_all_links(main_url, content):
    """
    Fetches all the links with the corresponding text from the content.
    It also converts the relative urls like `/main`, etc. to complete url.
    """

    links = {}
    content = BeautifulSoup(content)
    for notice in content.findAll("a"):
        title = notice.text.strip()
        url = notice.get("href")
        if url:
            if url[0] == '/':
                url = urlparse.urljoin(main_url,url)
            if not title:
                title = url
            if not title.startswith("<!--"):
                title = re.sub("[^A-Za-z0-9().\-\s]+"," ",title)
                if not title in links:
                    links[title] = url
                else:
                    links["{0} ({1}) ".format(title,
                        urlparse.urlsplit(url).path.split('/')[-1])] = url
    return links


def get_marquee_links(main_url, content):
    """
    Fetches all the links with the corresponding text from the marquee.
    It also completes the half urls like /main, etc. to complete url.
    """

    links = {}
    tree = html.fromstring(content)
    for i in range(len(tree.xpath('//marquee/a/@href'))):
        turl = tree.xpath('//marquee/a[{0}]/@href'.format(i))
        ttitle = tree.xpath('//marquee/a[{0}]/b/text()'.format(i))
        if turl and ttitle:
            url = str(turl[0])
            title = str(ttitle[0])
            if url and title:
                if url[0] == '/':
                    url = urlparse.urljoin(main_url,url)
                if not title in links:
                    links[title] = url
    return links


def tweet(tweet, testing=False):
    """Tweets the "tweet" to @VNITStudNotifs on Twitter using tweepy"""

    # App key, secret, obtained from dev.twitter.com when app was registered.
    # To be kept secret.
    CONSUMER_KEY    = settings.TWITTER_CONSUMER_KEY
    CONSUMER_SECRET = settings.TWITTER_CONSUMER_SECRET

    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)

    # Access Tokens, obtained from dev.twitter, to be kept secret.
    token_key    = settings.TWITTER_TOKEN_KEY
    token_secret = settings.TWITTER_TOKEN_SECRET

    auth.set_access_token(token_key, token_secret)

    # Connect
    api = tweepy.API(auth)

    if testing:
        return api.me()
    else:
        # Update Status
        api.update_status(tweet[:140])


# Using the Bitly API, shorten the post url
def url_shortener(url):
    """Shortens the given url with the help of Bit.ly API using bitly_api."""

    # Register & obtain following from https://bitly.com/a/settings/advanced
    # Keep them secret
    LOGIN   = settings.BITLY_LOGIN
    API_KEY = settings.BITLY_API_KEY

    # Connect
    con = bitly_api.Connection(LOGIN, API_KEY)
    # Shorten
    response = con.shorten(url)

    return response['url']

import urllib
import logging
import urlparse
import re
import os
import sys
import datetime
import webapp2
from google.appengine.ext.webapp import template
from google.appengine.ext import db
from google.appengine.api import urlfetch
from google.appengine.api import memcache
from bs4 import BeautifulSoup
from lxml import html
import tweepy
import bitly_api


Student_Notifications_Url = ["http://www.vnit.ac.in"
            "/index.php?option=com_content&view=article&id=448&Itemid=214",
                             "http://www.vnit.ac.in"
            "/index.php?option=com_content&view=article&id=612&Itemid=214"
                            ]


class Posts(db.Model):
    """Database Model to store each update/notification."""

    url = db.StringProperty(required=True)
    title = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)


def get_page(url, proxy=True):
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


class MainHandler(webapp2.RequestHandler):
    """Displays latest (max. week old) updates, or all updates as per query."""

    def get(self):
        """GET http method"""

        q = self.request.get("q")
        if q == "all":
            posts = memcache.get("all_posts")
            if not posts:
                posts = db.GqlQuery(
                    "SELECT * FROM Posts ORDER BY created DESC").fetch(300)
                memcache.set(key="all_posts", value=posts, time=604800)
            template_values = {'posts': posts}
            template_values['all'] = True
        else:
            posts = memcache.get("latest_posts")
            if not posts:
                all_posts = db.GqlQuery(
                    "SELECT * FROM Posts ORDER BY created DESC").fetch(20)
                cur = datetime.datetime.now()
                posts = []
                for pst in all_posts:
                    if cur - pst.created < datetime.timedelta(days=7):
                        posts.append(pst)
                    else:
                        break
                if not posts:
                    posts = db.GqlQuery(
                        "SELECT * FROM Posts ORDER BY created DESC").fetch(10)
                memcache.set(key="latest_posts",value=posts,time=604800)
            template_values = {'posts': posts}
            template_values['all'] = False
        template_values['url'] = Student_Notifications_Url[-1]
        template_values['proxy'] = memcache.get('proxy')
        template_values['blocking'] = memcache.get('blocking')
        template_values['last_checked'] = memcache.get('last_checked')
        path = "templates/index.html"
        self.response.out.write(template.render(path, template_values))


class CronHandler(webapp2.RequestHandler):
    """The cron requests handler. Also contains required methods."""

    def get_all_links(self, main_url, content):
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

    def get_marquee_links(self, main_url, content):
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

    def get(self):
        """
        Fetches the Student_Notifications_Url page.
        Grabs all the relevant links & their titles.
        stores every new link & tweets it out!
        """

        for stud_url in Student_Notifications_Url[::-1]:
            # fetch page
            notifs = get_page(stud_url)
            # Now, extract the content from the page
            content = notifs[notifs.find('<!-- BEGIN: CONTENT -->'):
                            notifs.find('<!-- END: CONTENT -->')]
            cur_links = self.get_all_links('https://www.vnit.ac.in', content)
            # cur_links.update(self.get_marquee_links('https://www.vnit.ac.in',
                                                    # notifs))
            # logging.info(cur_links)

            # Gather pre-existing posts data
            All_Posts = memcache.get("all_posts")
            if not All_Posts:
                All_Posts = db.GqlQuery(
                    "SELECT * FROM Posts ORDER BY created DESC").fetch(500)
            All_Links = dict()
            All_Urls = set()
            All_Titles = set()
            for each_post in All_Posts:
                All_Links[each_post.title] = each_post.url
                All_Urls.add(each_post.url)
                All_Titles.add(each_post.title)

            # Check for "new posts" from the fetched content
            new_links = {}
            for title, url in cur_links.items():
                cur_title = " ".join(title.strip().split())
                cur_url = url.strip()
                if not cur_title in All_Titles:
                    new_links[cur_title] = cur_url
                elif not cur_url in All_Urls:
                    new_links["{0} ({1}) ".format(cur_title,
                        urlparse.urlsplit(cur_url).path.split('/')[-1])] = \
                            cur_url

            if new_links:
                self.response.out.write("<br><b>New links found on </b><br>"
                    + stud_url)
                memcache.delete("all_posts")
                memcache.delete("latest_posts")
            else:
                self.response.out.write("<br><b>No New links found on {0}...\
                </b><br>".format(stud_url))
            for new in new_links:
                title, url = new, new_links[new]
                All_Links[title] = url
                logging.info('Title -- '+title+'Url -- '+url)
                # Save the post
                pst = Posts(url = url, title = title)
                pst.put()
                # Shorten the url
                shortened_url = UrlShortener(url)
                # Tweet the Post
                TweetHandler(' - '.join((title, shortened_url)))
                # Display the new post in the response
                self.response.out.write(
                    "<br>Title --> {0}<br>Url --> <a href={1}>{1}</a><br>"
                    .format(title, url)
                    )


class ViewHandler(webapp2.RequestHandler):
    """Displays the Student Notifications page as fetched by app."""

    def get(self):
        """GET http method"""

        content = get_page(Student_Notifications_Url[-1])
        if content:
            self.response.out.write(str(content))
        else:
            self.response.out.write("Failed to get a response")


class CronUrlHandler(webapp2.RequestHandler):
    """Cron handler for checking the Notifications URL from the main page."""

    def verify_notifications_url(self):
        """
        To be safe, fetch the Notifications Url from the main page of vnit.
        Because, they once changed the url & the app was useless for a month.
        """

        global Student_Notifications_Url
        vnit_main_url = "http://www.vnit.ac.in"
        vnit_homepage = get_page(vnit_main_url)
        vnit_home = BeautifulSoup(vnit_homepage)
        for spans in vnit_home.findAll('span'):
            if spans.string.strip().lower() == "student notice board":
                notice_board_rel_link = spans.previous.get('href')
                logging.info("Got a rel link (verify_notifications_url)"
                              + notice_board_rel_link)
                break
        else:
            logging.error("Verify Notifications' Url failure")
            notice_board_rel_link = \
                "/index.php?option=com_content&view=article&id=612&Itemid=214"
        new_url = urlparse.urljoin(vnit_main_url, notice_board_rel_link)
        if not new_url in Student_Notifications_Url:
            logging.error("Change in Notification Url to {0}".format( new_url))
            Student_Notifications_Url.append(new_url)

    def get(self):
        """
        Fetches the main VNIT page.
        Parses & checks for change in Notifications Url & updates accordingly.
        """

        self.verify_notifications_url()


class AboutHandler(webapp2.RequestHandler):
    """Handles the requests for viewing the about page."""

    def get(self):
        """GET http method"""

        path = "templates/about.html"
        template_values = {'url': Student_Notifications_Url[-1]}
        self.response.out.write(template.render(path, template_values))


class ChangeLogHandler(webapp2.RequestHandler):
    """Handles the requests for viewing the changelog page."""

    def get(self):
        """GET http method"""

        path = "templates/changelog.html"
        template_values = {'url': Student_Notifications_Url[-1]}
        self.response.out.write(template.render(path, template_values))


class UrlHandler(webapp2.RequestHandler):
    """Displays the urls stored in the global var Student_Notifications_Url."""

    def get(self):
        """GET http method"""

        global Student_Notifications_Url
        self.response.out.write("The Notification Urls as of now are - "
        + str(Student_Notifications_Url))


class PostPermaHandler(webapp2.RequestHandler):
    """Handles the requests for viewing an individual post."""

    def get(self, post_id):
        """GET http method"""

        path = "templates/post.html"
        try:
            to_render = memcache.get("_post_"+str(post_id))
            if not to_render:
                key = db.Key.from_path('Posts', int(post_id))
                post = db.get(key)
                if not post: raise KeyError
                template_values = {'post': post}
                to_render = template.render(path, template_values)
                memcache.set(key="_post_"+str(post_id), value=to_render)
            self.response.out.write(to_render)
        except:
            self.response.out.write("The post ID is invalid.")


# The dude of all the functions!!!
def TweetHandler(tweet):
    """Tweets the "tweet" to @VNITStudNotifs on Twitter using tweepy"""

    # App key, secret, obtained from dev.twitter.com when app was registered.
    # To be kept secret.
    CONSUMER_KEY = 'API Key'
    CONSUMER_SECRET = 'API Secret'

    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)

    # Access Tokens, obtained from dev.twitter, to be kept secret.
    token_key = "access token_key"
    token_secret = "access token_secret"

    auth.set_access_token(token_key, token_secret)

    # Connect
    api = tweepy.API(auth)
    # Update Status
    api.update_status(tweet[:140])


# Using the Bitly API, shorten the post url
def UrlShortener(url):
    """Shortens the given url with the help of Bit.ly API using bitly_api."""

    # Register & obtain following from https://bitly.com/a/settings/advanced
    # Keep them secret
    LOGIN = 'o_login'
    API_KEY = 'R_apikey'

    # Connect
    con = bitly_api.Connection(LOGIN, API_KEY)
    # Shorten
    response = con.shorten(url)

    return response['url']


def handle_404(request, response, exception):
    """Custom 404 handler."""

    logging.exception(exception)
    response.write("Oops! You seem to have wandered off! "
                   "The requested page does not exist.")
    response.set_status(404)


def handle_500(request, response, exception):
    """Custom 505 handler."""

    logging.exception(exception)
    response.write("A server error occurred! "
                   "Report has been logged. Work underway asap.")
    response.set_status(500)


app = webapp2.WSGIApplication([('/?',                MainHandler),
                               ('/check/?',          CronHandler),
                               ('/checkurl/?',       CronUrlHandler),
                               ('/view/?',           ViewHandler),
                               (r'/post/(\d+)/?',    PostPermaHandler),
                               ('/about/?',          AboutHandler),
                               ('/changelog/?',      ChangeLogHandler),
                               ('/url/?',            UrlHandler)],
                              debug=True)

app.error_handlers[404] = handle_404
app.error_handlers[500] = handle_500

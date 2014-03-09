import urllib
import logging
import urlparse
import re
import os
import sys
import datetime
import tweepy
import webapp2
from google.appengine.ext.webapp import template
from google.appengine.ext import db
from google.appengine.api import urlfetch
from google.appengine.api import memcache
from bs4 import BeautifulSoup
from lxml import html

if os.environ.get('SERVER_SOFTWARE','').startswith('Devel'):
    # This is when testing the app on local server
    CALLBACK = 'http://localhost:9991/oauth/callback'
else:
    # Actual deployment data
    CALLBACK = 'https://vnitsiteupdates.appspot.com/oauth/callback'

Student_Notifications_Url = ["http://www.vnit.ac.in"
            "/index.php?option=com_content&view=article&id=448&Itemid=214",
                             "http://www.vnit.ac.in"
            "/index.php?option=com_content&view=article&id=612&Itemid=214"
                            ]

class Posts(db.Model):
    """
    Databasel Model to store each update on the Student_Notifications_Url.
    """
    url = db.StringProperty(required=True)
    title = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)

class MainHandler(webapp2.RequestHandler):
    def get(self):
        """
        Displays latest (max. week old) updates or all updates as per query.
        """
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
        path = "templates/index.html"
        self.response.out.write(template.render(path, template_values))

class CronHandler(webapp2.RequestHandler):
    def get_page(self, url):
        """
        Fetches the content displayed on the page of given url
        """
        #page = urlfetch.fetch(url).content
        #logging.info(page)
        try:
            page = urllib.urlopen(url)
            content = page.read()
            logging.info("Successfully fetched url - "+url)
            return str(content)
        except:
            logging.error('Unable to fetch Url - '+url)
            return ""

    def get_all_links(self, main_url, content):
        """
        Fetches all the links with the corresponding text from the content.
        It also completes the half urls like /main, etc. to complete url.
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
        Fetches the Student_Notifications_Url page. Grabs all the relevant links
        & their titles, stores every new link & tweets it out!
        """
        for stud_url in Student_Notifications_Url[::-1]:
            notifs = self.get_page(stud_url) # fetch page
            # Now, extract the content from the page
            content = notifs[notifs.find('<!-- BEGIN: CONTENT -->'):
                            notifs.find('<!-- END: CONTENT -->')]
            cur_links = self.get_all_links('https://www.vnit.ac.in', content)
            cur_links.update(self.get_marquee_links('https://www.vnit.ac.in',
                                                    notifs))
            #logging.info(cur_links)

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
                pst = Posts(url = url, title = title)
                pst.put()
                TweetHandler(' - '.join((title, url)))
                self.response.out.write(
                    "<br>Title --> {0}<br>Url --> <a href={1}>{1}</a><br>"
                    .format(title, url)
                    )

class CronUrlHandler(webapp2.RequestHandler):
    def get_page(self, url):
        """
        Fetches the content displayed on the page of given url
        """
        #page = urlfetch.fetch(url).content
        #logging.info(page)
        try:
            page = urllib.urlopen(url)
            content = page.read()
            logging.info("Successfully fetched url - "+url)
            return str(content)
        except:
            logging.error('Unable to fetch Url - '+url)
            return ""

    def verify_notifications_url(self):
        # To be safe, fetch the Notifications Url from the main page of vnit
        global Student_Notifications_Url
        vnit_main_url = "http://www.vnit.ac.in"
        vnit_homepage = self.get_page(vnit_main_url)
        vnit_home = BeautifulSoup(vnit_homepage)
        for spans in vnit_home.findAll('span'):
            if spans.string.strip().lower() == "student notice board":
                notice_board_rel_link = spans.previous.get('href')
                logging.info("Got a rel link (verify_notifications_url)")
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
    def get(self):
        path = "templates/about.html"
        template_values = {'url': Student_Notifications_Url[-1]}
        self.response.out.write(template.render(path, template_values))

class ChangeLogHandler(webapp2.RequestHandler):
    def get(self):
        path = "templates/changelog.html"
        template_values = {'url': Student_Notifications_Url[-1]}
        self.response.out.write(template.render(path, template_values))

class UrlHandler(webapp2.RequestHandler):
    def get(self):
        global Student_Notifications_Url
        self.response.out.write("The Notification Urls as of now are - "
        + str(Student_Notifications_Url))

class PostPermaHandler(webapp2.RequestHandler):
    def get(self, post_id):
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

# Tweepy requirements

class OAuthToken(db.Model):
    token_key = db.StringProperty(required=True)
    token_secret = db.StringProperty(required=True)

class OauthHandler(webapp2.RequestHandler):
    def get(self):
        # Build a new oauth handler and display authorization url to user.
        auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET, CALLBACK)
        try:
            path = "templates/auth.html"
            template_values = {"authurl": auth.get_authorization_url(),
                               "request_token": auth.request_token}
            self.response.out.write(template.render(path, template_values))
        except tweepy.TweepError, e:
            # Failed to get a request token
            self.response.out.write(template.render('templates/error.html',
                                                    {'message': e}))
            return

        # We must store the request token for later use in the callback page.
        request_token = OAuthToken(token_key=auth.request_token.key,
                                   token_secret=auth.request_token.secret)
        request_token.put()

# Callback page (/oauth/callback)
class CallbackHandler(webapp2.RequestHandler):
    def get(self):
        oauth_token = self.request.get("oauth_token", None)
        oauth_verifier = self.request.get("oauth_verifier", None)
        if oauth_token is None:
            # Invalid request!
            path = "templates/error.html"
            template_values = {'message': 'Missing required parameters!'}
            self.response.out.write(template.render(path, template_values))
            return

        # Lookup the request token
        request_token = OAuthToken.gql("WHERE token_key=:key",
                                        key=oauth_token).get()
        if request_token is None:
            # We do not seem to have this request token, show an error.
            path = "templates/error.html"
            template_values = {'message': 'Invalid token!'}
            self.response.out.write(template.render(path, template_values))
            return

        # Rebuild the auth handler
        auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth.set_request_token(request_token.token_key,
                               request_token.token_secret)

        # Fetch the access token
        try:
            auth.get_access_token(oauth_verifier)
        except tweepy.TweepError, e:
            # Failed to get access token
            path = "templates/error.html"
            template_values = {'message': e}
            self.response.out.write(template.render(path, template_values))
            return

        # So now we could use this auth handler.
        # Here we will just display the access token key&secret
        path = "templates/callback.html"
        template_values = {'access_token': auth.access_token}
        self.response.out.write(template.render(path, template_values))
        auth_api = tweepy.API(auth)

# The dude of all the functions!!!
def TweetHandler(tweet):
    """
    Tweet the "tweet" to @VNITStudNotifs on Twitter using tweepy
    """
    CONSUMER_KEY = 'Twitter Consumer key'
    # App key, obtained from dev.twitter.com when app was registered.
    CONSUMER_SECRET = 'Twitter Consumer secret'
    # App secret, to be kept so.
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    key = "Twitter App key"
    secret = "Twitter App secret"
    # Access Token secret obtained from running the CallbackHandler.
    auth.set_access_token(key, secret)
    api = tweepy.API(auth)
    api.update_status(tweet[:140])

def handle_404(request, response, exception):
    logging.exception(exception)
    response.write("Oops! You seem to have wandered off! " +
                   "The requested page does not exist.")
    response.set_status(404)

def handle_500(request, response, exception):
    logging.exception(exception)
    response.write("A server error occurred! " +
                   "Report has been logged. Work underway asap.")
    response.set_status(500)

app = webapp2.WSGIApplication([('/?', MainHandler),
                              ('/check/?', CronHandler),
                              ('/checkurl/?', CronUrlHandler),
                              (r'/post/(\d+)/?',PostPermaHandler),
                              ('/about/?', AboutHandler),
                              ('/changelog/?', ChangeLogHandler),
                              ('/url/?', UrlHandler),
                              ('/oauth/callback/?', CallbackHandler),
                              ('/oauth/?', OauthHandler)],
                              debug=True)

app.error_handlers[404] = handle_404
app.error_handlers[500] = handle_500
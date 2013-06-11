import urllib, logging, urlparse, re, os
import datetime
import tweepy
import webapp2
from google.appengine.ext.webapp import template
from google.appengine.ext import db
from google.appengine.api import urlfetch
from google.appengine.api import memcache

if os.environ.get('SERVER_SOFTWARE','').startswith('Devel'):
	# This is when testing the app on local server
    CONSUMER_KEY = 'iOZsPRzyaQXWTGAJfCI1Q'
    CONSUMER_SECRET = 'ZeFtG1JWV2TOeAB9FNoRwLqnKtDB5HsI2kl3tdAY'
    CALLBACK = 'http://localhost:9991/oauth/callback'
else:
	# Actual deployment data
    CONSUMER_KEY = 'iOZsPRzyaQXWTGAJfCI1Q'
    CONSUMER_SECRET = 'ZeFtG1JWV2TOeAB9FNoRwLqnKtDB5HsI2kl3tdAY'
    CALLBACK = 'https://vnitsiteupdates.appspot.com/oauth/callback'

Student_Notifications_Url = "http://www.vnit.ac.in/index.php?option=com_content&view=article&id=448&Itemid=214"

class Posts(db.Model):
	'''
	Databasel Model to store each update on the Student_Notifications_Url.
	'''
	url = db.StringProperty(required=True)
	title = db.StringProperty(required=True)
	content = db.TextProperty(required=True)
	created = db.DateTimeProperty(auto_now_add=True)

''' Needed for storing our access token. Since we already fetched it, it is not required.
class OAuthToken(db.Model):
    token_key = db.StringProperty(required=True)
    token_secret = db.StringProperty(required=True)
'''

class MainHandler(webapp2.RequestHandler):
    def get(self):
		'''
		Displays latest (max. week old) updates or all updates as per query.
		'''
		q = self.request.get("q")
		if q == "all":
			posts = memcache.get("all_posts")
			if not posts:
				posts = db.GqlQuery("SELECT * FROM Posts ORDER BY created DESC").fetch(50)
				memcache.set(key="all_posts",value=posts,time=604800)
		else:
			posts = memcache.get("latest_posts")
			if not posts:
				all_posts = db.GqlQuery("SELECT * FROM Posts ORDER BY created DESC").fetch(50)
				cur = datetime.datetime.now()
				posts = []
				for pst in all_posts:
					if cur - pst.created < datetime.timedelta(days=7):
						posts.append(pst)
					else:
						break
				memcache.set(key="latest_posts",value=posts,time=604800)
		path = "index.html"
		template_values = {'posts': posts}
		self.response.out.write(template.render(path, template_values))

class CronHandler(webapp2.RequestHandler):
	def get_page(self,url):
		'''
		Fetches the content displayed on the page of given url
		'''
		#page = urlfetch.fetch(url).content
		#logging.info(page)
		try:
			page = urlfetch.fetch(url,deadline=15)
			content = page.content
			return str(content)
		except:
			logging.error('Unable to fetch Url')
			return ""
	def get_next_target(self,page):
		'''
		Parses the page & returns the url, title text & the end position to get next target
		'''
		if page:
			start_link = page.find('href=')
			if start_link == -1:
				return None, None, 0
			start_quote = page.find('"', start_link)
			end_quote = page.find('"', start_quote + 1)
			url = page[start_quote + 1:end_quote]
			start_tag = page.find('">', end_quote)
			if '<' in page[start_tag+2:start_tag+3]:
				start_tag += page[start_tag+1:].find('">')
			end_tag = page.find('</', start_tag)
			title = page[start_tag+2:end_tag]
			if '>' in title:
				title = title[title.rfind('>')+1:]
			return title, url, end_quote
		else:
			return False, False, False
	def get_all_links(self,main_url,content):
		'''
		Fetches all the links with the corresponding text from the content.
		It also completes the half urls like /main, etc. to complete url.
		'''
		links = {}
		while True:
			title, url, endpos = self.get_next_target(content)
			if url:
				if url[0] == '/':
					url = urlparse.urljoin(main_url,url)
				if not title:
					title = url
				title = re.sub("[^A-Za-z0-9().\s]+"," ",title)
				links[title] = url
				content = content[endpos:]
			else:
				break
		return links
	def get(self):
		'''
		Fetches the Student_Notifications_Url page. Grabs all the relevant links & their titles,
		stores every new link & tweets it out!
		'''
		notifs = self.get_page(Student_Notifications_Url)
		notifs = notifs[notifs.find('<!-- BEGIN: CONTENT -->'):notifs.find('<!-- END: CONTENT -->')]
		cur_links = self.get_all_links('https://www.vnit.ac.in',notifs)
		All_Links = memcache.get('all_links')
		if All_Links in (None,'',[],{}):
			All_Posts = Posts.all()
			All_Links = {}
			for each_post in All_Posts:
				All_Links[each_post.title] = each_post.url
			memcache.set('all_links',All_Links)
		if not sorted(cur_links.keys()) == sorted(All_Links):
			new_links = {}
			for each in cur_links:
				if not each in All_Links:
					new_links[each] = cur_links[each]
			if new_links:
				self.response.out.write("<br/><b>New links found...</b><br/>")
			else:
				self.response.out.write("<br/><b>No New links found...</b><br/>")
			for new in new_links:
				url, title = new_links[new], new
				All_Links[title] = url
				logging.info('Title -- '+title+'Url -- '+url)
				pst = Posts(url=url,title=title,content=url)
				pst.put()
				TweetHandler('New update - '+title+'. Link - '+url)
				self.response.out.write("<br/>Title --> "+title)
				self.response.out.write("<br/>Url --> <a href="+url+">"+url+"</a><br/>")
			memcache.flush_all()
			memcache.set('all_links',All_Links)
		else:
			self.response.out.write("<br/><b>No New links found...</b><br/>")

'''Oauth & Callback Handlers (Twitter Stuff) are kinda useless, since we already have the key & the secret!'''
'''
class OauthHandler(webapp2.RequestHandler):
	def get(self):
        # Build a new oauth handler and display authorization url to user.
		auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET, CALLBACK)
		try:
			path = "oauth.html"
			template_values = {"authurl": auth.get_authorization_url(),"request_token": auth.request_token}
			self.response.out.write(template.render(path, template_values))
		except tweepy.TweepError, e:
			# Failed to get a request token
			self.response.out.write(template.render('error.html', {'message': e}))
			return

		# We must store the request token for later use in the callback page.
		request_token = OAuthToken(token_key=auth.request_token.key, token_secret=auth.request_token.secret)
		request_token.put()

# Callback page (/oauth/callback)
class CallbackHandler(webapp2.RequestHandler):
    def get(self):
        oauth_token = self.request.get("oauth_token", None)
        oauth_verifier = self.request.get("oauth_verifier", None)
        if oauth_token is None:
            # Invalid request!
			path = "error.html"
			template_values = {'message': 'Missing required parameters!'}
			self.response.out.write(template.render(path, template_values))
			return

        # Lookup the request token
        request_token = OAuthToken.gql("WHERE token_key=:key", key=oauth_token).get()
        if request_token is None:
            # We do not seem to have this request token, show an error.
			path = "error.html"
			template_values = {'message': 'Invalid token!'}
			self.response.out.write(template.render(path, template_values))
			return

        # Rebuild the auth handler
        auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth.set_request_token(request_token.token_key, request_token.token_secret)

        # Fetch the access token
        try:
            auth.get_access_token(oauth_verifier)
        except tweepy.TweepError, e:
            # Failed to get access token
			path = "error.html"
			template_values = {'message': e}
			self.response.out.write(template.render(path, template_values))
			return

        # So now we could use this auth handler.
        # Here we will just display the access token key&secret
        path = "callback.html"
        template_values = {'access_token': auth.access_token}
        self.response.out.write(template.render(path, template_values))
        auth_api = tweepy.API(auth)
'''

'''The dude of all the functions!!!'''
def TweetHandler(status):
	auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
	key = "1495763953-x3OrqBgJqwChB9sPWgeUrvJdZMZtNGkIoptPFN2"
	secret = "pYVEnD5nJCOZAPBp11FWxib91a8wsICvydVuyLyx1g"
	auth.set_access_token(key, secret)
	api = tweepy.API(auth)
	api.update_status(status)

#Some garbage...might come handy later...So didn't throw it out.
#class CleanHandler(webapp2.RequestHandler):
#	def get(self):
#		posts = db.GqlQuery("SELECT * FROM Posts ORDER BY created")
#		cur = datetime.datetime.now()
#		for pst in posts:
#			if cur - pst.created >= datetime.timedelta(days=7):
#				logging.info("Old entry")
#				if pst.title in All_Links:
#					memcache.delete('latest_posts')
#					logging.info("Deleting Index - "+pst.title)
#					del All_Links[pst.title] #Doing the wrong thingy...

#class PostPermaHandler(webapp2.RequestHandler):
#Need to add this --> (r'/(\d+)',PostPermaHandler) to 'app' handler list
#	def get(self, post_id):
#		path = "index.html"
#		key = db.Key.from_path('Posts', int(post_id))
#		post = db.get(key)
#		posts = [post]
#		template_values2 = {'posts':posts}
#		self.response.out.write(template.render(path, template_values2))

app = webapp2.WSGIApplication([('/?', MainHandler),('/check/?', CronHandler)], debug=True)

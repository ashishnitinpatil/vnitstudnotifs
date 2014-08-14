from django.shortcuts import render
from django.http import HttpResponse
from google.appengine.api import memcache
import datetime
import logging
from bs4 import BeautifulSoup
from vnitstudentnotifications.coreapp import utils
from vnitstudentnotifications.coreapp.models import Posts, Urls
from django.forms.models import model_to_dict
import urlparse


def home(request):
    """
    View for the landing page.
    Displays the latest posts according to query (all, latest).
    Displays latest (max. week old) updates, or all updates as per query.
    """
    q = request.GET.get("q")
    if q == "all":
        posts = memcache.get("all_posts")
        if not posts:
            # Need to use the memcache hacks (making a list of the QuerySet objects)
            posts = list(Posts.objects.all())
            memcache.set(key="all_posts", value=posts, time=604800)
        show_all_posts = True
    else:
        posts = memcache.get("latest_posts")
        if not posts:
            all_posts = Posts.objects.all()[:20]
            cur = datetime.datetime.now()
            posts = []
            for pst in all_posts:
                if cur - pst.added_on < datetime.timedelta(days=7):
                    posts.append(pst)
                else:
                    break
            if not posts:
                # Need to use the memcache hacks (making a list of the QuerySet objects)
                posts = list(Posts.objects.all()[:10])
            memcache.set(key="latest_posts", value=posts, time=604800)
        show_all_posts = False
    cur_url      = list(Urls.objects.all())[0]
    proxy        = memcache.get('proxy')
    blocking     = memcache.get('blocking')
    last_checked = memcache.get('last_checked')
    return render(request, "index.html", locals())


def cron(request):
    """
    Fetches the Student_Notifications_Url page.
    Grabs all the relevant links & their titles.
    stores every new link & tweets it out!
    """

    initialize = False
    testing = False
    if request.GET.get('initialize', "").lower() == 'true':
        initialize = True
    if request.GET.get('testing', "").lower() == 'true':
        testing = True
    response = []

    for stud_url in Urls.objects.all():
        cur_response = {"status": "Something's funny.", "links": list()}
        if not testing:
            # fetch page
            notifs = utils.get_page(stud_url.url)
            # Now, extract the content from the page
            content = notifs[notifs.find('<!-- BEGIN: CONTENT -->'):
                            notifs.find('<!-- END: CONTENT -->')]
            cur_links = utils.get_all_links('http://www.vnit.ac.in', content)
            # cur_links.update(utils.get_marquee_links('https://www.vnit.ac.in',
                                                    # notifs))
            # logging.info(cur_links)
        else:
            cur_links = dict()

        # Gather pre-existing posts data
        All_Posts = memcache.get("all_posts")
        if not All_Posts:
            All_Posts = Posts.objects.all()
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
            cur_response["status"] = "New links found on {0}".format(stud_url.url)
            memcache.delete("all_posts")
            memcache.delete("latest_posts")
        else:
            cur_response["status"] = "No new links found on {0}".format(stud_url.url)
        for new in new_links:
            title, url = new, new_links[new]
            url = urlparse.urlunparse(urlparse.urlparse(url))
            if url.startswith("https"):
                url = url.replace("https", "http")
            All_Links[title] = url
            logging.info('Title -- '+title+'Url -- '+url)
            # Save the post
            Posts.objects.create(url=url, title=title)
            # Shorten the url
            shortened_url = utils.url_shortener(url)
            # Tweet the Post
            shortened_title = title[:100]
            utils.tweet(' - '.join((shortened_title,shortened_url)), initialize)
            # Display the new post in the response
            cur_response["links"].append([title, url])
        response.append(cur_response)

    if not response:
        response = {"status": "Did not execute", "links": list()}
    return HttpResponse(str(response), content_type="application/json")


def cron_url(self):
    """
    To be safe, fetch the Notifications Url from the main page of vnit.
    Because, they once changed the url & the app was useless for a month.
    """

    response = []
    vnit_main_url = "http://www.vnit.ac.in"
    vnit_homepage = utils.get_page(vnit_main_url)
    vnit_home = BeautifulSoup(vnit_homepage)
    for spans in vnit_home.findAll('span'):
        if spans.string.strip().lower() == "student notice board":
            rel_link = spans.previous.get('href')
            msg = "Got a rel link " + rel_link
            response.append(msg)
            logging.info(msg)
            break
    else:
        msg = "Verify Notifications' Url failure"
        response.append(msg)
        logging.error(response)
        rel_link = "/index.php?option=com_content&view=article&id=612&Itemid=214"
    new_url = urlparse.urljoin(vnit_main_url, rel_link)
    if not new_url in (x.url for x in Urls.objects.all()):
        msg = "Change in Notification Url to {0}".format(new_url)
        response.append(msg)
        logging.error(response)
        Urls.objects.create(url=new_url)
    else:
        response.append("No change in notif url")

    return HttpResponse("\n".join(response), content_type="application/json")

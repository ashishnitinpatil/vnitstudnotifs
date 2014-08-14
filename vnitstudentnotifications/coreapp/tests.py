from django.test import TestCase
from vnitstudentnotifications.coreapp import utils
from django.core.urlresolvers import reverse
from vnitstudentnotifications.coreapp.models import Posts, Urls


class UtilsTests(TestCase):
    """Tests all the methods in utils"""

    def test_get_page(self):
        urls = [
            "http://www.vnit.ac.in",
            "http://www.vnit.ac.in/index.php?option=com_content&view=article&id=448&Itemid=214",
            "http://www.vnit.ac.in/index.php?option=com_content&view=article&id=612&Itemid=214",
        ]
        for url in urls:
            # TODO Comment the following "continue" when running final test.
            continue
            self.assertEqual(utils.get_page(url, proxy=True),
                             utils.get_page(url, proxy=False))

    def test_url_shortener(self):
        url = "http://www.vnit.ac.in/index.php?option=com_content&view=article&id=448&Itemid=214"
        self.assertTrue(len(utils.url_shortener(url)) < len(url))

    def test_tweet(self):
        self.assertIsNotNone(utils.tweet("testing",testing=True))


class ViewTests(TestCase):
    """Tests all the views for coreapp"""

    def setUp(self):
        for url in [
            "http://www.vnit.ac.in/index.php?option=com_content&view=article&id=448&Itemid=214",
            "http://www.vnit.ac.in/index.php?option=com_content&view=article&id=612&Itemid=214",
        ]:
            Urls.objects.create(url=url)

    def test_home_page(self):
        response1 = self.client.get("/")
        response2 = self.client.get("/?q=latest")
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response1.content, response2.content)
        response  = self.client.get("/?q=all")
        self.assertEqual(response.status_code, 200)

    def test_cron_check(self):
        response = self.client.get(reverse('coreapp:cron')+"?testing=True")
        self.assertEqual(response.status_code, 200)

    def test_about_page(self):
        response = self.client.get(reverse('coreapp:about'))
        self.assertEqual(response.status_code, 200)

    def test_changelog_page(self):
        response = self.client.get(reverse('coreapp:changelog'))
        self.assertEqual(response.status_code, 200)

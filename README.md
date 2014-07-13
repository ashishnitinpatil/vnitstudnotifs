Student Notifications Checker
=============================

**Author**  - Ashish Nitin Patil  
**Created** - 12th of June, 2013 (v2)  
**Updated** - 13th of July, 2014 (v5.2) [5-Apr v5.1, 9-Mar v5, 1-Jan v4]  
**Licence** - BSD License (Free for commercial use).


### Project Summary

- The app runs 'cron' jobs periodically (as per settings in [cron.yaml](/cron.yaml)), checking for any new updates on the [Student Notifications page](http://vnit.ac.in/index.php?option=com_content&view=article&id=612&Itemid=214).
- If there are any new updates/notifications, they are stored in the database.
- The corresponding *title - url* is then tweeted on [@VNITStudNotifs](http://www.twitter.com/VNITStudNotifs).
- With the help of [IFTTT](http://www.ifttt.com), we then post the tweets on our [FaceBook page](http://www.facebook.com/vnitstudnotifs).


### Key Components

- The [app.yaml](/app.yaml) contains url Handler settings, which runs the `main.py`.
- The `.html` files are templates used by the corresponding url Handlers.
- We use the [tweepy](https://github.com/tweepy/tweepy) python library for twitter API, to post our tweets.
- The [bs4 directory](https://github.com/ashishnitinpatil/vnitstudnotifs/tree/master/bs4) containing the [BeautifulSoup4](http://www.crummy.com/software/BeautifulSoup/) library is what we currently use to parse html of the [Student Notifications page](http://vnit.ac.in/index.php?option=com_content&view=article&id=612&Itemid=214).
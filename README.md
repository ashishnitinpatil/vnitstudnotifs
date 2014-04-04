Student Notifications Checker
=============================

**Author**  - Ashish Nitin Patil<br>
**Created** - 12th of June, 2013 (v2)<br>
**Updated** - 5th of April, 2014 (v5.1) [9-Mar-2014 v5, 1-Jan-2014 v4]
**Licence** - Creative Commons Attribution 4.0 Unported License.

### Project Summary ###
-----------------------
The app runs 'cron' jobs periodically (as per settings in `cron.yaml`),<br>
checking for any new updates on the Student Notifications page.<br>
If there are any new links, they are stored in the database,<br>
& the corresponding link title is tweeted on '@VNITStudNotifs' (Twitter).<br>
With the help of `IFTTT` recipe 137489, we post the tweets on the<br>
FaceBook page facebook.com/vnitstudnotifs.<br>
The `app.yaml` contains url Handler settings, which runs the `main.py`.<br>
The .html files are templates used by the corresponding url Handlers.<br>
The `tweepy` directory contains the `tweepy` twitter library for python.<br>
The `bs4` directory contains the `BeautifulSoup4` library for python.
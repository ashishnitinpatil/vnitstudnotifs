import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
Student_Notifications_Url = ["http://www.vnit.ac.in" + \
            "/index.php?option=com_content&view=article&id=448&Itemid=214",
                             "http://www.vnit.ac.in" + \
            "/index.php?option=com_content&view=article&id=612&Itemid=214"
                            ]

def verify_notifications_url():
    # To be safe, fetch the Notifications Url from the main page of vnit
    global Student_Notifications_Url
    vnit_main_url = "http://www.vnit.ac.in"
    vnit_homepage = urllib.request.urlopen(vnit_main_url).read()
    vnit_home = BeautifulSoup(vnit_homepage)
    for spans in vnit_home.findAll('span'):
        if spans.string.strip().lower() == "student notice board":
            notice_board_rel_link = spans.previous.get('href')
            break
    else:
        print("Student Notifications URL from homepage failure")
        notice_board_rel_link = \
            "/index.php?option=com_content&view=article&id=612&Itemid=214"
    new_url = urllib.parse.urljoin(vnit_main_url, notice_board_rel_link)
    if not new_url in Student_Notifications_Url:
        print("Change in Notification Url to {0}".format( new_url))
        Student_Notifications_Url.append(new_url)
verify_notifications_url()
print(Student_Notifications_Url)
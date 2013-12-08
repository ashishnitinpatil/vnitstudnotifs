import urllib.request, logging

All_Relevant_Links = []
#Student_Notifications_Url = "http://www.vnit.ac.in/"
Student_Notifications_Url = "http://localhost:9990/_index"

class abcd:
    def get_page(self,url):
    	try:
    		content = urllib.request.urlopen(url).read()
    		return str(content)
    	except:
    		logging.error('Unable to fetch Url')
    		return ""
    def get_next_target(self,page):
    	if page:
    		start_link = page.find('href=')
    		if start_link == -1:
    			return None, 0
    		start_quote = page.find('"', start_link)
    		end_quote = page.find('"', start_quote + 1)
    		url = page[start_quote + 1:end_quote]
    		return url, end_quote
    	else:
    		return False, False
    def get_all_links(self,main_url,content):
    	links = []
    	while True:
    		url, endpos = self.get_next_target(content)
    		if url:
    			if url[0] == '/':
    				url = urllib.request.urljoin(main_url,url)
    			if url not in links:
    				links.append(url)
    			content = content[endpos:]
    		else:
    			break
    	return links
    def get(self):
    	cur_links = self.get_all_links(Student_Notifications_Url,self.get_page(Student_Notifications_Url))
    	if not sorted(cur_links) == sorted(All_Relevant_Links):
    		new_links = []
    		for each in cur_links:
    			if not each in All_Relevant_Links:
    				new_links.append(each)
    		print(new_links)
a = abcd()
a.get()
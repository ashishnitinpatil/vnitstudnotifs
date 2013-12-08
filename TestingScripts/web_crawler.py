import urllib.request
import logging

def get_page(url):
    try:
        content = urllib.request.urlopen(url).read()
        return str(content)
    except:
        return ""

def union(a, b):
    for e in b:
        if e not in a:
            a.append(e)

def get_next_target(page):
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

def get_all_links(main_url,content):
    links = []
    while True:
        url, endpos = get_next_target(content)
        if url:
            if url[0] == '/':
                url = urllib.request.urljoin(main_url,url)
            links.append(url)
            content = content[endpos:]
        else:
            break
    return links

def crawl_web(seed):
    tocrawl = []
    tocrawl += initial_seed
    crawled = []
    while tocrawl:
        url = tocrawl.pop()
        if url not in crawled:
            content = get_page(url)
            add_page_to_index(url, content)
            union(tocrawl, get_all_links(url,content))
            crawled.append(url)

def add_page_to_index(url, content):
    index[url] = content

index = {}
logging.info('Started Crawler')
initial_seed = ['http://localhost:9990/index']
crawl_web(initial_seed)
print(index.keys())
logging.info('Crawling Finished')
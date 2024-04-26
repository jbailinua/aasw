# aasw.py script for generating AASWomen newsletter
# By Jeremy Bailin, 2022
# Last updated 15 Sept 2023

import sys
import re
import datetime
import calendar
import html
import requests
from PIL import Image
import io
from operator import itemgetter

# GLOBAL SETTINGS
# List of editors. Update when the editorial team changes.
editor_list = 'Jeremy Bailin, Nicolle Zellner, Sethanne Howard, and Hannah Jang-Condell'
# Should the code double-check that any URLs don't return 404? (takes a while)
confirm_urls = False
# File containing the boilerplate items at the bottom of the newsletter.
final_text_filename = 'final-items.jaml'
# User agent for web requests. Shouldn't need to change this until it gets very out of date.
user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:105.0) Gecko/20100101 Firefox/105.0'
# Beginning boilerplate for Job Opportunities listings
job_opp_boilerplate = """
For those interested in increasing excellence and diversity in their organizations, a list of resources and advice is here:

https://aas.org/comms/cswa/resources/Diversity#howtoincrease

"""


class aaswitems(object):

    def __init__(self, filename):
        self.items = []
        self.image = {'url':'', 'caption':''}
    	
        # read text into a variable
        with open(filename,'r', encoding='utf-8-sig') as f:
            fulltext = f.read()
        with open(final_text_filename,'r', encoding='utf-8-sig') as f:
            finaltext = f.read()
                
        for filetext in (fulltext, finaltext,):
            # Break it by ---
            itemtexts = re.split(r'---', filetext)
            
            for itemtext in itemtexts:
                # If the entire item is blank, just skip it
                mallwhitespace = re.match(' *$', itemtext)
                if mallwhitespace:
                    continue
                
                # Is this the header with image info?
                mimgurl = re.search('^img-url: ?(.*)$', itemtext, re.MULTILINE)
                mimgcaption = re.search('^img-caption: ?(.*)$', itemtext, re.MULTILINE)
                if mimgurl:
                    # Check to make sure it's not just blank.
                    mimgurl_is_just_whitespace = re.match('^ *$', mimgurl.group(1))
                    if not mimgurl_is_just_whitespace:
                        self.image['url'] = mimgurl.group(1)
                        if mimgcaption:
                            self.image['caption'] = texthtmlstr(mimgcaption.group(1))                    
                    continue #onto first real item
                    
                # Otherwise put together something for the items list
                this_item = {'title':"", 'text':None}
                
                # Look for title
                mtitle = re.search('^title: ?(.*)$', itemtext, re.MULTILINE | re.IGNORECASE)
                if mtitle:
                    this_item['title'] = mtitle.group(1).rstrip()
                else:
                    # Title is required
                    raise ValueError(f'Title could not be found for the following item:\n{itemtext}\n')
                
                # Look for from line
                mfrom = re.search('^from: ?(.*)$', itemtext, re.MULTILINE | re.IGNORECASE)
                if mfrom:
                    this_item['from'] = mfrom.group(1)
                    
                # Look for body
                mbody = re.search('^text:\s*(.*)', itemtext, re.MULTILINE | re.IGNORECASE | re.DOTALL)
                if mbody:
                    isjob = re.search(' *Job Opportunities *', this_item['title'], re.IGNORECASE) is not None
                    this_item['text'] = parsedstr(mbody.group(1).rstrip(), job=isjob)
                else:
                    # Text body is required
                    raise ValueError(f'Text body could not be found for the following item:\n{itemtext}\n')
                    
                # Add to items
                self.items.append(this_item)
            
    
    
    
class texthtmlstr(object):
    def __init__(self, s):
        self.text = s
        self.html = html.escape(s)
    
    def print_text(self):
        return self.text
        
    def print_html(self):
        return self.html    
    
                        
class urlstr(texthtmlstr):
    # URL string
    def __init__(self, url):
        self.text = url
        self.html = f'<a href="{url}">{url}</a>'
        
        # Check to make sure it works - give a warning if not
        if confirm_urls:
            headers = { 'User-Agent':user_agent }
            
            url_status = requests.head(url, headers=headers).status_code
            if url_status >= 400:
            	# Check if it needs a get
            	url_status = requests.get(url, headers=headers).status_code
            	if url_status >= 400:
            		print(f'Warning! The following URL might not be valid: {url}\n')
            
                
class parabreakstr(texthtmlstr):
    # paragraph break string
    html = '</p><p>'
    
    def __init__(self, after_single=False):
    	if after_single:
    		self.text = '\n'
    	else:
    		self.text = '\n\n'
        
class separator(texthtmlstr):
	# item separator
	text = '-------------------------------------------------------------------------------\n'
	html = '<hr />'
	
	def __init__(self):
		pass
    
class singleline(texthtmlstr):
	# Single line with a line break
	def __init__(self, s):
		self.text = f'{s.rstrip()}\n'
		self.html = f'{html.escape(s)}<br />\n'

class titleline(texthtmlstr):
	# Title with an internal link to or from the TOC
	def __init__(self, text, itemnumber, uniqident=None, from_toc=True):
		self.text = f'{itemnumber}. {text}\n'
		if uniqident:
		    itemstring = f'item{uniqident}-{itemnumber}'
		else:
		    itemstring = f'item{itemnumber}'
		if from_toc:
			self.html = f'<a href="#{itemstring}">{itemnumber}. {text}</a><br />\n'
		else:
			self.html = f'<div id="{itemstring}">{itemnumber}. {text}</div>\n'

class htmlonly(texthtmlstr):
	# something that will only appear in HTML, i.e. the image and caption
	def __init__(self, code):
		self.text = ''
		self.html = code

class mixedstr(object):
	def __init__(self):
		self.texthtml_strings = []
		
	def print_text(self):
		text_strings = [s.print_text() for s in self.texthtml_strings]
		return ''.join(text_strings)

	def print_html(self):
		html_strings = [s.print_html() for s in self.texthtml_strings]
		return r'<p>' + ''.join(html_strings) + r'</p>'
        
	def add(self, o):
		# If it's already a mixedstr then add its items, otherwise add as a single item
		if hasattr(o, 'texthtml_strings'):
			for s in o.texthtml_strings:
				self.texthtml_strings.append(s)
		else:
			self.texthtml_strings.append(o)
	

	
            
class parsedstr(mixedstr):
    url_regex = r'\b(?:https?|telnet|gopher|file|wais|ftp):[\w/#~:.?+=&%@!\-.:?\\-]+?(?=[.:?\-]*(?:[^\w/#~:.?+=&%@!\-.:?\-]|$))'
    # https://stackoverflow.com/questions/720113/find-hyperlinks-in-text-using-python-twitter-related
    parbreak_regex = r'\n\s*\n'
    
    def __init__(self, s, job=False):
        # parse string (1) substitute any URLs with internal representations, (2) find paragraph
        # breaks and store.
        self.texthtml_strings = []
        segments = []
        
        # For Job Opportunities section, prepend the boilerplate
        if job:
        	s = job_opp_boilerplate + s
        
        for paramatch in re.finditer(self.parbreak_regex, s):
            # Insert info about all paragraph breaks
            segments.append({'start':paramatch.start(), 'end':paramatch.end(), 'type':'p'})
        for urlmatch in re.finditer(self.url_regex, s):
            # Insert info about URLs
            segments.append({'start':urlmatch.start(), 'end':urlmatch.end(), 'type':'u', 'value':urlmatch.group(0)})
        if len(segments) == 0:
            # No text. Return
            return

        # Sort
        segments.sort(key=itemgetter('start'))

        # Add in plain text segments for any that are missing
        current_pos = 0
        # Loop through segments looking for gaps
        for segi in range(len(segments)):
            if segments[segi]['start'] > current_pos:
                segments.append({'start':current_pos, 'end':segments[segi]['start'], 'type':'t', \
                    'value':s[current_pos:segments[segi]['start']]})
            current_pos = segments[segi]['end']
        # Check for final gap
        if current_pos < len(s):
            segments.append({'start':current_pos, 'end':len(s), 'type':'t', \
                'value':s[current_pos:]})
                
        # Re-sort
        segments.sort(key=itemgetter('start'))
        
        # Add everything into texthtml_strings in order
        for seg in segments:
            if seg['type']=='p':
                self.texthtml_strings.append(parabreakstr())
            elif seg['type']=='u':
                self.texthtml_strings.append(urlstr(seg['value']))
            elif seg['type']=='t':
                if job:
                    # Special case: There will be lines that look like "- Jobinfo\nURL"
                    # Need to add the break between the job info and URL
                    for jobline in seg['value'].splitlines():                        
                        mjobline = re.match(' *- *(.*)$', jobline)
                        if mjobline:
                            jobstr = texthtmlstr(f'- {mjobline.group(1)}\n') # Also make sure this is consistent
                            jobstr.html += r'<br />'
                        else:
                            jobstr = texthtmlstr(jobline)
                        
                        self.texthtml_strings.append(jobstr)                        
                    
                else:
                    self.texthtml_strings.append(texthtmlstr(seg['value']))
            else:
                raise ValueError('Segment type unknown.')

        return
                    
        
        
            




def usage():
	print(f'Usage: {sys.argv[0]} infile\n')
	exit(1)

def build_newsletter(items):
	# Figure out the appropriate date
	today = datetime.date.today()
	friday = today + datetime.timedelta( (calendar.FRIDAY-today.weekday()) % 7 )
	issue_datestr = f'{friday:%B} {friday.day}, {friday:%Y}'
	uniqident = f'{friday:%y}{friday:%m}{friday:%d}'
	
	email_blog_title = f'AASWomen Newsletter for {issue_datestr}'
	print(email_blog_title)
	
	# Put it all together
	newsletter = mixedstr()

	if items.image['url']!='':
		# Add image and caption
		# First figure out image dimensions
		headers = { 'User-Agent':user_agent }
		r = requests.get(items.image['url'], headers=headers)
		img = Image.open(io.BytesIO(r.content))
		width,height = img.size
		img_html = htmlonly(f'<div class="separator" style="clear: both;"><a href="{items.image["url"]}" style="display: block; padding: 1em 0; text-align: center; clear: right; float: right;"><img alt="" border="0" width="320" data-original-height="{height}" data-original-width="{width}" src="{items.image["url"]}"><br />{items.image["caption"].print_html()}</a></div>')
		newsletter.add(img_html)

	newsletter.add(htmlonly(f'<div id="{uniqident}-top"></div>'))
	newsletter.add(singleline('AAS Committee on the Status of Women'))
	newsletter.add(singleline(f'Issue of {issue_datestr}'))
	newsletter.add(singleline(f'eds: {editor_list}'))
	newsletter.add(parabreakstr(after_single=True))
	newsletter.add(singleline('[We hope you all are taking care of yourselves and each other. --eds.]'))
	newsletter.add(parabreakstr(after_single=True))
	newsletter.add(singleline("This week's issues:"))
	newsletter.add(parabreakstr(after_single=True))
	for ti, item in enumerate(items.items, start=1):
		newsletter.add(titleline(item['title'], ti, uniqident, from_toc=True))
	newsletter.add(parabreakstr(after_single=True))
	newsletter.add(parsedstr('An online version of this newsletter will be available at http://womeninastronomy.blogspot.com/ at 3:00 PM ET every Friday.'))	
	newsletter.add(htmlonly('<!--more-->'))
	newsletter.add(parabreakstr(after_single=True))
	
	for ti, item in enumerate(items.items, start=1):
		newsletter.add(parabreakstr(after_single=True))
		newsletter.add(separator())
		newsletter.add(titleline(item['title'], ti, uniqident, from_toc=False))
		if 'from' in item:
			newsletter.add(texthtmlstr(f'From: {item["from"]}'))
			newsletter.add(parabreakstr(after_single=True))
		newsletter.add(parabreakstr(after_single=True))
		newsletter.add(item['text'])
		newsletter.add(parabreakstr(after_single=True))
		newsletter.add(htmlonly(f'<a href="#{uniqident}-top">Back to top.</a></p>'))
# 		newsletter.add(htmlonly(f'</p><p><a href="#{uniqident}-top">Back to top.</a></p>'))
		
	return newsletter
		
	
	
	
	

if __name__=='__main__':
	# Get input file name
	if (len(sys.argv) != 2):
		usage()
	input_fname = sys.argv[1]
	# Replace file extension if it exists with .html, or just add to end if
	# there is no extension
	out_html_fname = re.sub('(\.\S+)?$', '.html', input_fname, count=1)
	# Double check that we don't end up clobbering the original
	if re.match('\.txt$', input_fname):
		print('Warning! Rename input file to have a different extension so the .txt file does not get clobbered.\n')
		exit(1)
	out_txt_fname = re.sub('(\.\S+)?$', '.txt', input_fname, count=1)
		
	newsletter_items = aaswitems(input_fname)
	full_newsletter = build_newsletter(newsletter_items)
	with open(out_html_fname, 'w', encoding='utf-8-sig') as f:
		f.write(full_newsletter.print_html())
		print(f'HTML newsletter written to {out_html_fname}')
	with open(out_txt_fname, 'w', encoding='utf-8-sig') as f:
		f.write(full_newsletter.print_text())
		print(f'Text newsletter written to {out_txt_fname}')



import html.parser
import os.path
import re
import urllib, urllib.request, urllib.parse
import datetime, time
import logging

URL_BASE = 'http://www.letemps.ch/'
LOGIN_PAGE = '/Login'
LIST_PAGE = '/e_paper?periodMin=1m'

RE_SEARCH_PDF =  r'<div class="previewBox">\s*<div class="background">\s*<div class="heading">(?P<title>.*?)</div>\s*'
RE_SEARCH_PDF += r'<div class="content">\s*<h3><a href="[^\"]*">(?P<date>[0-9.]+)</a></h3>\s*'
RE_SEARCH_PDF += r'<div class="preview">\s*<a href="[^\"]*"><img [^>]*></a></div>\s*'
RE_SEARCH_PDF += r'<ul class="linkbox clear">\s*<li><a href="[^\"]*">Version ePaper</a></li>\s*'
RE_SEARCH_PDF += r'<li><a href="(?P<url>[^\"]*)"\s*onclick="[^\"]*">Version PDF</a></li>'

from nd.newspaper_api import NewspaperLoader, OnlineNewspaperIssue, NewspaperStream, LoaderException
from nd.scheduler import DailySchedule, SimpleNewspaperDownloadScheduler

class LeTempsLoaderNetAccess(object):
  '''
  A class to provide network access to the LeTemps loader.
  '''

  def login(self, username, password):
    '''
    Create a new session on the website with the given credentials.
    '''
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    PARAMS = {
      'username': username,
      'password': password
    }
    urllogin = urllib.parse.urljoin(URL_BASE, LOGIN_PAGE)
    query = urllib.request.Request(urllogin, urllib.parse.urlencode(PARAMS).encode('utf-8'))
    query.add_header('User-agent', 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.110 Safari/537.36')
    query.add_header('Referer', 'http://www.letemps.ch/login')
    loginPage = opener.open(query)
    loginPage.close()
    return opener

  def issues_page(self, opener):
    '''
    Returns the pages full of issues
    '''
    urllist = urllib.parse.urljoin(URL_BASE, LIST_PAGE)
    listPage = opener.open(urllist)
    lines = ''.join(map(lambda x : x.decode('utf-8'), listPage.readlines()))
    listPage.close()
    return lines

  def open(self, opener, url):
    return opener.open(url)

class LeTempsLoader(NewspaperLoader):

  def __init__(self, config, netaccess=LeTempsLoaderNetAccess()):
    self._netaccess = netaccess
    self._config = config
    self._opener = None

  def get_scheduler(self):
    schedule = DailySchedule()
    wait_evolution = (x*60*60 for x in (1, 12))
    return SimpleNewspaperDownloadScheduler(schedule, wait_evolution)

  def name(self):
    return 'Le Temps'
  
  def init(self):
    self._opener = None
    try:
      USERNAME = self._config.get("nd.plugin.letemps.username")
      PASSWORD = self._config.get("nd.plugin.letemps.password")

      if not USERNAME:
        raise LoaderException('Invalid username')

      self._opener = self._netaccess.login(USERNAME, PASSWORD)

      logger = logging.getLogger(__name__)
      logger.info('Login successfuly on %s', self.name())
    except urllib.request.HTTPError as e:
      raise LoaderException('HTTP error when logging on %s (Exception %s, HTTP code: %s)' % \
                          (self.name(), e, e.code))
    except urllib.request.URLError as e:
      raise LoaderException('Invalid URL to log on %s (Exception %s)' % \
                          (self.name(), e))
    
  def open(self, url):
    return self._netaccess.open(self._opener, url)

  def issues(self):
    logger = logging.getLogger(__name__)
    
    if not self._opener:
      raise LoaderException("The newspaper '%s' is not initialized" % self.name())

    # load the index page
    urllist = urllib.parse.urljoin(URL_BASE, LIST_PAGE)
    try:
      lines = self._netaccess.issues_page(self._opener)
    except urllib.request.HTTPError as e:
      raise LoaderException('HTTP error when logging on %s (Exception %s, HTTP code: %s)' % \
                          (self.name(), e, e.code))
    except urllib.request.URLError as e:
      raise LoaderException('Invalid URL to log on %s (Exception %s)' % \
                          (self.name(), e))
    
    # load the issues found
    h = html.parser.HTMLParser()
    
    issues = []
    for urlmatch in re.finditer(RE_SEARCH_PDF, lines, re.DOTALL):
      metadata = urlmatch.groupdict()

      relative_url = h.unescape(metadata['url'])
      url = urllib.parse.urljoin(URL_BASE, relative_url)

      date = re.sub('</?[^>]*?>', '', metadata['date'])
      date = h.unescape(date)
      try:
        date = datetime.datetime(*(time.strptime(date, '%d.%m.%Y')[0:6])).date()
      except ValueError:
        logger.warning('Invalid date %s in %s for an issue' % \
                       (date, self.name()))
        date = None

      if date:
        title = re.sub('</?[^>]*?>', '', metadata['title'])
        title = h.unescape(title)
        issues.append(LeTempsIssue(title, date, self, url))
    
    logger.info('%d issues found on the website', len(issues))
    issues.sort(key=lambda x : (x.date(), x.title()), reverse=True)
    return issues

class LeTempsIssue(OnlineNewspaperIssue):
  
  def __init__(self, title, date, loader, url):
    super(LeTempsIssue, self).__init__(title, date, loader)
    if url == None:
      raise ValueError('Invalid argument')
    self._url = url

  def url(self):
    return self._url

  def open(self):
    try:
        stream = self.loader().open(self.url())
        return LeTempsStream(stream, self)
    except urllib.request.HTTPError as e:
      raise LoaderException('HTTP error when downloading "%s" (HTTP code: %s)' % \
                          (self.title(), e.code))
    except urllib.request.URLError as e:
      raise LoaderException('Invalid URL to download issue "%s" for %s (Exception %s, URL %s)' % \
                          (self.title(), self.loader().name(), e.reason, self._url))

class LeTempsStream(NewspaperStream):
  
  def __init__(self, stream, issue):
    self._stream = stream
    self._issue = issue

  def close(self):
    try:
      self._stream.close()
    except IOError:
      pass

  def read(self, size=512):
    try:
      return self._stream.read(size)
    except:
      raise LoaderException('Error when downloading %s' % repr(self._issue))


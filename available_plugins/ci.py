# -*- coding: utf-8 -*-
import html.parser
import os.path
import re
import urllib, urllib.request, urllib.parse
import datetime, time
import logging

URL_BASE = 'http://www.courrierinternational.com/'
LOGIN_PAGE = '/login'

LIST_PAGE = '/magazines_overview'

RE_SEARCH_PDF =  r'<div class="hebdo-box_1"><span class="hebdo-mag_num">\s*'
RE_SEARCH_PDF += r'(?P<numero>[^<]*)</span>\s*<div class="hebdo-event_date_mag">'
RE_SEARCH_PDF += r'(?P<date>[^<]*)</div>\s*'
RE_SEARCH_PDF += r'<div class="hebdo-box_img"><a href="[^"]*"><img[^>]*/></a></div>\s*'
RE_SEARCH_PDF += r'<div class="hebdo-event_date_mag"><a href="(?P<url>[^"]*)">'
RE_SEARCH_PDF += r'(?P<title>[^<]*)</a></div>'

RE_GET_PDF = r'<a\s+href="(?P<url>[^"]+)" title="Téléchargez en PDF'

from nd.newspaper_api import NewspaperLoader, OnlineNewspaperIssue, NewspaperStream, LoaderException
from nd.scheduler import WeeklySchedule, SimpleNewspaperDownloadScheduler

class CourrierInternationalNetAccess(object):
  '''
  A class to provide network access to the Courrier International loader.
  '''

  def login(self, username, password):
    '''
    Create a new session on the website with the given credentials.
    '''
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    PARAMS = {
      'name': username,
      'pass': password,
      'form_id': 'user_login_block'
    }
    urllogin = urllib.parse.urljoin(URL_BASE, LOGIN_PAGE)
    query = urllib.request.Request(urllogin, urllib.parse.urlencode(PARAMS).encode('utf-8'))
    query.add_header('User-agent', 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.110 Safari/537.36')
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

class CourrierInternationalLoader(NewspaperLoader):

  def __init__(self, config, netaccess=CourrierInternationalNetAccess()):
    self._netaccess = netaccess
    self._config = config
    self._opener = None

  def get_scheduler(self):
    schedule = WeeklySchedule(4)
    wait_evolution = (x*60*60 for x in (1, 12))
    return SimpleNewspaperDownloadScheduler(schedule, wait_evolution)

  def name(self):
    return 'Courrier International'

  def init(self):
    self._opener = None
    try:
      USERNAME = self._config.get("nd.plugin.ci.username")
      PASSWORD = self._config.get("nd.plugin.ci.password")

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

    h = html.parser.HTMLParser()

    issues = []
    for urlmatch in re.finditer(RE_SEARCH_PDF, lines, re.DOTALL):
      metadata = urlmatch.groupdict()

      relative_url = h.unescape(metadata['url'])
      url = urllib.parse.urljoin(URL_BASE, relative_url)

      date = metadata['date']
      try:
        date = datetime.datetime.strptime(date, '%d %B %Y').date()
      except ValueError as e:
        logger.warning('Invalid date %s in %s for an issue' % \
                       (date, self.name()))
        date = None

      title = metadata['title']

      if date:
        issues.append(CourrierInternationalIssue(title, date, self, url))

    logger.info('%d issues found on the website', len(issues))
    issues.sort(key=lambda x : (x.date(), x.title()), reverse=True)
    return issues

class CourrierInternationalIssue(OnlineNewspaperIssue):

  def __init__(self, title, date, loader, url):
    super(CourrierInternationalIssue, self).__init__(title, date, loader)
    if url == None:
      raise ValueError('Invalid argument')
    self._url = url

  def url(self):
    return self._url

  def open(self):
    try:
      pdflinkPageStream = self.loader().open(self._url)
      pdflinkPage = ''.join(map(lambda x : x.decode('utf-8'), pdflinkPageStream.readlines()))

      pdf = re.compile(RE_GET_PDF, re.DOTALL)
      links = list(pdf.finditer(pdflinkPage))
      if links:
        if len(links) > 1:
          logger = logging.getLogger(__name__)
          logger.info('Several PDF link found for "%s" on "%s"', \
                      str(self), self.url())
        link = links[0].groupdict()['url']

        stream = self.loader().open(link)
        return CourrierInternationalStream(stream, self)
      else:
        raise LoaderException('No PDF link found for "%s" on "%s"' % \
                              (self.title(), self.url()))
    except urllib.request.HTTPError as e:
      raise LoaderException('HTTP error when downloading "%s" (HTTP code: %s)' % \
                          (self.title(), e.code))
    except urllib.request.URLError as e:
      raise LoaderException('Invalid URL to download issue "%s" for %s (Exception %s, URL %s)' % \
                          (self.title(), self.loader().name(), e.reason, self._url))

class CourrierInternationalStream(NewspaperStream):

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


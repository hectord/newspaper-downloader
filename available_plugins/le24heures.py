# -*- coding: utf-8 -*-
import os.path
import re
import shutil
import urllib, urllib.request, urllib.parse
import datetime, time
import logging

import distutils.spawn
import subprocess

import zipfile, tempfile

URL_BASE = 'http://journal.24heures.ch/'
LOGIN_PAGE = '/user'
TOKEN_PAGE = '/epsaepaper/epaper/1'

URL_VIEWER_BASE = 'http://epaper.tamedia.ch'
LIST_PAGE = '/lightpaper.aspx?product=VQH&edition={edition_type}'

RE_SEARCH_PDF =  r'<option (selected="selected" )?value="\d{8}">(?P<d>\d{2})\.(?P<m>\d{2})\.(?P<y>\d{2})</option>'

DOWNLOAD_PAGE = '/Products/VQH-{edition_type}/{date}/zip/full.zip'

# pdfconcat can be found here: http://pts-mini-gpl.googlecode.com/svn/trunk/pdfconcat/
#  you can compile it with gcc.
PDFCONCAT_PATH = 'pdfconcat'

from nd.newspaper_api import NewspaperLoader, OnlineNewspaperIssue, NewspaperStream, LoaderException
from nd.scheduler import DailySchedule, SimpleNewspaperDownloadScheduler

class Le24HeuresNetAccess(object):
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
      'form_id': 'user_login',
      'op': ''
    }
    urllogin = urllib.parse.urljoin(URL_BASE, LOGIN_PAGE)
    query = urllib.request.Request(urllogin, urllib.parse.urlencode(PARAMS).encode('utf-8'))
    query.add_header('User-agent', 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.110 Safari/537.36')
    loginPage = opener.open(query)
    loginPage.readlines()
    loginPage.close()

    urltoken = urllib.parse.urljoin(URL_BASE, TOKEN_PAGE)
    query = urllib.request.Request(urltoken)
    query.add_header('User-agent', 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.110 Safari/537.36')
    tokenPage = opener.open(query)
    tokenPage.readlines()
    tokenPage.close()

    return opener

  def issues_page(self, opener, issue_type):
    '''
    Returns the pages full of issues
    '''
    # load the index page
    url = LIST_PAGE.format(edition_type=issue_type)
    urllist = urllib.parse.urljoin(URL_VIEWER_BASE, url)
    listPage = opener.open(urllist)
    lines = ''.join(map(lambda x : x.decode('utf-8'), listPage.readlines()))
    listPage.close()
    return lines

  def load_zip(self, opener, issue_type, date):
    # load the index page
    url = DOWNLOAD_PAGE.format(edition_type=issue_type, date=date)
    urldownload = urllib.parse.urljoin(URL_VIEWER_BASE, url)
    return opener.open(urldownload)

class Le24HeuresLoader(NewspaperLoader):

  def __init__(self, config, netaccess=Le24HeuresNetAccess()):
    self._netaccess = netaccess
    self._config = config
    self._opener = None

  def get_scheduler(self):
    schedule = DailySchedule()
    wait_evolution = (x*60*60 for x in (6, 12))
    return SimpleNewspaperDownloadScheduler(schedule, wait_evolution)

  def name(self):
    return '24 Heures'

  def init(self):
    self._issue_types = {'LAUSANNE': "24 heures", 
                         'VQ_EMPLOI': "Emploi", 
                         'VQ_IMMO': "Immobilier", 
                         'VQ_FORM': "Formation", 
                         'VQSU': "Suppléments"}

    self._opener = None
    try:
      USERNAME = self._config.get("nd.plugin.24heures.username")
      PASSWORD = self._config.get("nd.plugin.24heures.password")

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

  def netaccess(self):
    return self._netaccess

  def _issues_by_type(self, id_type):
    issues = []
    issue_name = self._issue_types[id_type]

    try:
      htmlpage = self._netaccess.issues_page(self._opener, id_type)
    except urllib.request.HTTPError as e:
      raise LoaderException('HTTP error when logging on %s (Exception %s, HTTP code: %s)' % \
                          (self.name(), e, e.code))
    except urllib.request.URLError as e:
      raise LoaderException('Invalid URL to log on %s (Exception %s)' % \
                          (self.name(), e))

    for newspaper_match in re.finditer(RE_SEARCH_PDF, htmlpage, re.DOTALL):
      metadata = newspaper_match.groupdict()

      try:
        date = datetime.datetime(2000+int(metadata['y']), 
                                 int(metadata['m']), 
                                 int(metadata['d']))
      except ValueError as e:
        logger.warning('Invalid date %s in %s for an issue' % \
                       (date, self.name()))
        date = None

      if date:
        issues.append(Le24HeuresIssue(id_type, issue_name, date.date(), self))
    return issues

  def issues(self):
    logger = logging.getLogger(__name__)

    if not self._opener:
      raise LoaderException("The newspaper '%s' is not initialized" % self.name())

    issues = []
    for id_type in self._issue_types:
      issues.extend(self._issues_by_type(id_type))

    logger.info('%d issues found on the website', len(issues))
    issues.sort(key=lambda x : (x.date(), x.title()), reverse=True)
    return issues

  def opener(self):
    return self._opener

class Le24HeuresIssue(OnlineNewspaperIssue):

  def __init__(self, id_type, title, date, loader):
    super(Le24HeuresIssue, self).__init__(title, date, loader)
    if id_type == None:
      raise ValueError('Invalid argument')
    self._id_type = id_type

  def _create_PDF(self, pdfpathes):
    '''
    Create a new PDF from the files pointed by the pathes in
     pdfpathes.
    '''
    if not pdfpathes:
      raise ValueError('No file, no PDF!')

    try:
      filepath = tempfile.mktemp(suffix='.pdf')
    except IOError as e:
      raise LoaderException('Cannot create a temporary file (%s)' % e)

    # compression to be used
    params = ['-o', filepath]
    cmdline = [PDFCONCAT_PATH]+params+pdfpathes
    self._execute(cmdline)
    return filepath

  def _execute(self, params):
    try:
      code = subprocess.call(params)
      if code != 0:
        raise LoaderException('Error code %d when executing %s' % \
                              (code, ' '.join(params)))
    except OSError as e:
      raise LoaderException('Exception "%s" when executing %s' % \
                            (e, ' '.join(params)))

  def open(self):
    try:
      strdate = self.date().strftime('%Y%m%d')
      opener = self.loader().opener()

      stream = self.loader().netaccess().load_zip(opener, self._id_type, strdate)
      zipf = tempfile.NamedTemporaryFile(delete=True)
      shutil.copyfileobj(stream, zipf)
      stream.close()
      zipf.seek(0)

      myzip = zipfile.ZipFile(zipf)
      try:
        pages = myzip.namelist()
        pages.sort()

        pdfdir = tempfile.mkdtemp()
        pdfpathes = []
        for page in pages:
          pdfpathes.append(myzip.extract(page, pdfdir))
      finally:
        myzip.close()

      thepdf = self._create_PDF(pdfpathes)
      for pdfpath in pdfpathes:
        os.remove(pdfpath)
      shutil.rmtree(pdfdir)

      return Le24HeuresStream(thepdf, self)

    except zipfile.BadZipfile as e:
      raise LoaderException('Invalid ZIP file')
    except urllib.request.HTTPError as e:
      raise LoaderException('HTTP error when downloading "%s" (HTTP code: %s)' % \
                          (self.title(), e.code))
    except urllib.request.URLError as e:
      raise LoaderException('Invalid URL to download issue "%s" for %s (Exception %s, URL %s)' % \
                          (self.title(), self.loader().name(), e.reason, self._url))

class Le24HeuresStream(NewspaperStream):

  def __init__(self, path, issue):
    self._path = path
    self._stream = open(path, 'rb')
    self._issue = issue

  def close(self):
    try:
      self._stream.close()
      os.remove(self._path)
    except (IOError, OSError) as e:
      logger = logging.getLogger(__name__)
      logger.warning('Cannot close and remove file %s', self._path)

  def read(self, size=512):
    try:
      return self._stream.read(size)
    except:
      raise LoaderException('Error when downloading %s' % repr(self._issue))


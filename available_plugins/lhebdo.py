# -*- coding: utf-8 -*-
import os, os.path
import tempfile

import re

import html.parser
import urllib, urllib.request

import datetime
import logging

LIST_PAGE = 'http://admin7.iomedia.ch/system/client_data/hebdo/epaper/pageflip/getContent.php?id=%d'

RE_GET_NEWSPAPERS = 'edition=(?P<date>\d{8})_(?P<no>\d+)\'\s*/>.*?href="(?P<url>[^"]*)"'

from nd.newspaper_api import NewspaperLoader, OnlineNewspaperIssue, NewspaperStream, LoaderException
from nd.scheduler import WeeklySchedule, SimpleNewspaperDownloadScheduler

class LHebdoInternetAccess(object):
  '''
  A class to provide network access to the Courrier International loader.
  '''

  def issues_page(self):
    '''
    Returns the pages full of issues
    '''
    listPage = urllib.request.urlopen(LIST_PAGE % datetime.date.today().year)
    lines = ''.join(map(lambda x : x.decode('utf-8'), listPage.readlines()))
    listPage.close()
    return lines

  def download(self, url):
    return urllib.request.urlopen(url)

class LHebdoLoader(NewspaperLoader):

  def __init__(self, config, netaccess=LHebdoInternetAccess()):
    self._netaccess = netaccess
    self._config = config

  def get_scheduler(self):
    schedule = WeeklySchedule(4)
    wait_evolution = (x*60*60 for x in (4, 18))
    return SimpleNewspaperDownloadScheduler(schedule, wait_evolution)

  def name(self):
    return "L'Hebdo"

  def open(self, url):
    return self._netaccess.download(url)

  def init(self):
    pass

  def issues(self):
    logger = logging.getLogger(__name__)

    # load the index page
    try:
      lines = self._netaccess.issues_page()
    except urllib.request.HTTPError as e:
      raise LoaderException('HTTP error when logging on %s (Exception %s, HTTP code: %s)' % \
                          (self.name(), e, e.code))
    except urllib.request.URLError as e:
      raise LoaderException('Invalid URL to log on %s (Exception %s)' % \
                          (self.name(), e))

    h = html.parser.HTMLParser()
    issues = []
    for urlmatch in re.finditer(RE_GET_NEWSPAPERS, lines, re.DOTALL):
      metadata = urlmatch.groupdict()

      title = h.unescape('N&deg;'+metadata['no'])

      try:
        date = datetime.datetime.strptime(metadata['date'], '%Y%m%d').date()
      except ValueError as e:
        logger.warning('Invalid date %s in %s for an issue' % \
                       (date, self.name()))
        date = None

      if date:
        issues.append(LHebdoIssue(title, date, self, metadata['url']))

    logger.info('%d issues found on the website', len(issues))
    issues.sort(key=lambda x : (x.date(), x.title()), reverse=True)
    return issues

class LHebdoIssue(OnlineNewspaperIssue):

  def __init__(self, title, date, loader, url):
    super(LHebdoIssue, self).__init__(title, date, loader)
    if url == None:
      raise ValueError('Invalid argument')
    self._url = url

  def open(self):

    try:
      loader = self.loader()

      return LHebdoStream(loader.open(self._url), self)

    except urllib.request.HTTPError as e:
      raise LoaderException('HTTP error when downloading "%s" (HTTP code: %s)' % \
                            (self.title(), e.code))
    except urllib.request.URLError as e:
      raise LoaderException('Invalid URL to download issue "%s" for %s (Exception %s, URL %s)' % \
                            (self.title(), self.loader().name(), e.reason, self._url))

class LHebdoStream(NewspaperStream):

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


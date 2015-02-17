# -*- coding: utf-8 -*-

import unittest
from available_plugins.letemps import *
from mockito import mock, verify, when

import urllib

class LeTempsLoaderTest(unittest.TestCase):

  def setUp(self):
    self._config = mock()
    when(self._config).get('nd.plugin.letemps.username').thenReturn('a')
    when(self._config).get('nd.plugin.letemps.password').thenReturn('b')

  def testName(self):
    l = LeTempsLoader(self._config)
    self.assertEquals(l.name(), 'Le Temps')

  def testGetIssuesWithoutLogin(self):
    l = LeTempsLoader(self._config)
    try:
      l.issues()
      self.fail("No exception raised")
    except LoaderException:
      pass

  def testExceptionWhenLogin(self):
    networkAccess = mock()
    when(networkAccess).login('a', 'b').thenRaise(urllib.request.URLError(''))
    l = LeTempsLoader(self._config, networkAccess)
    try:
      l.init()
      self.fail("No exception raised")
    except LoaderException:
      pass

    error = urllib.request.HTTPError(*[None for i in range(5)])
    when(networkAccess).login('a', 'b').thenRaise(error)
    try:
      l.init()
      self.fail("No exception raised")
    except LoaderException:
      pass

  def testExceptionWhenFindIssues(self):
    networkAccess = mock()
    opener = mock()
    when(networkAccess).login("a", "b").thenReturn(opener)
    when(networkAccess).issues_page(opener).thenRaise(urllib.request.URLError(''))

    l = LeTempsLoader(self._config, networkAccess)
    l.init()
    try:
      l.issues()
      self.fail("No exception raised")
    except LoaderException:
      pass

    error = urllib.request.HTTPError(*[None for i in range(5)])
    when(networkAccess).issues_page(opener).thenRaise(error)
    l = LeTempsLoader(self._config, networkAccess)
    l.init()
    try:
      l.issues()
      self.fail("No exception raised")
    except LoaderException:
      pass

  def testLeTempsIssue(self):
    loader = mock()
    d= datetime.date.today()
    try:
      LeTempsIssue('test', d, loader, None)
      self.fail("No exception raised")
    except ValueError:
      pass

  def testFindIssuesInPage(self):
    htmlSrc = u'<div class="previewBox"><div class="background"><div class="heading"><strong>Le '
    htmlSrc += u'<i></i>Temps <span>Quotidienneé</span></strong></div>'
    htmlSrc += u'<div class="content"><h3><a href="http://letemps.ch/Page">14.09.2013</a></h3>'
    htmlSrc += u'<div class="preview">'
    htmlSrc += u'<a href="http://b.cj"><img src=""></a></div>'
    htmlSrc += u'<ul class="linkbox clear"><li><a href="http://a.html">Version ePaper</a></li>'
    htmlSrc += u'<li><a href="http://letemps.ch/rw/30914.pdf" onclick="">Version PDF</a></li>'

    networkAccess = mock()
    when(networkAccess).login('a', 'b').thenReturn(1)
    when(networkAccess).issues_page(1).thenReturn(htmlSrc)

    l = LeTempsLoader(self._config, networkAccess)
    l.init()
    issues = l.issues()

    self.assertEquals(len(issues), 1)
    self.assertEquals(issues[0].date(), datetime.date(2013,9,14))
    self.assertEquals(issues[0].title(), u"Le Temps Quotidienneé")
    self.assertEquals(issues[0].url(), "http://letemps.ch/rw/30914.pdf")

  def testFindIssuesInvalidDate(self):
    htmlSrc = '<div class="previewBox"><div class="background"><div class="heading"><strong>Le '
    htmlSrc += '<i></i>Temps <span>Quotidienne</span></strong></div>'
    htmlSrc += '<div class="content"><h3><a href="http://letemps.ch/Page">14092013</a></h3>'
    htmlSrc += '<div class="preview">'
    htmlSrc += '<a href="http://b.cj"><img src=""></a></div>'
    htmlSrc += '<ul class="linkbox clear"><li><a href="http://a.html">Version ePaper</a></li>'
    htmlSrc += '<li><a href="http://letemps.ch/rw/30914.pdf" onclick="">Version PDF</a></li>'

    networkAccess = mock()
    when(networkAccess).login('a', 'b').thenReturn(1)
    when(networkAccess).issues_page(1).thenReturn(htmlSrc)

    l = LeTempsLoader(self._config, networkAccess)
    l.init()
    issues = l.issues()

    self.assertEquals(len(issues), 0)

  def testGetStream(self):
    loader = mock()
    i = LeTempsIssue('a', datetime.date.today(), loader, 'http://???')

    i.open()
    verify(loader).open('http://???')

  def testGetStreamException(self):
    loader = mock()
    i = LeTempsIssue('a', datetime.date.today(), loader, 'http://???')

    when(loader).open('http://???').thenRaise(urllib.request.URLError(''))

    try:
      i.open()
      self.fail('No exception raised')
    except LoaderException:
      pass

    error = urllib.request.HTTPError(*[None for r in range(5)])
    when(loader).open('http://???').thenRaise(error)
    try:
      i.open()
      self.fail('No exception raised')
    except LoaderException:
      pass

  def testStreamExceptionWhenClosing(self):
    issue = mock()
    stream = mock()

    lts = LeTempsStream(stream, issue)
    when(stream).close().thenRaise(IOError)

    lts.close()

  def testStreamException(self):
    issue = mock()
    stream = mock()

    lts = LeTempsStream(stream, issue)
    when(stream).read(130).thenRaise(Exception)

    try:
      lts.read(130)
      self.fail("No exception raised")
    except LoaderException:
      pass

    lts.close()
    verify(stream).close()

if __name__ == '__main__':
  unittest.main()


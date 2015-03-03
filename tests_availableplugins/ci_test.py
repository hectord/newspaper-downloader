# -*- coding: utf-8 -*-

import unittest
from available_plugins.ci import *
from mockito import mock, verify, when

import urllib
import io

class CILoaderTest(unittest.TestCase):

  def setUp(self):
    self._config = mock()
    when(self._config).get('nd.plugin.ci.username').thenReturn('a')
    when(self._config).get('nd.plugin.ci.password').thenReturn('b')

  def testName(self):
    l = CourrierInternationalLoader(self._config)
    self.assertEquals(l.name(), 'Courrier International')

  def testGetIssuesWithoutLogin(self):
    l = CourrierInternationalLoader(self._config)
    try:
      l.issues()
      self.fail("No exception raised")
    except LoaderException:
      pass

  def testExceptionWhenLogin(self):
    networkAccess = mock()
    when(networkAccess).login('a', 'b').thenRaise(urllib.request.URLError(''))
    l = CourrierInternationalLoader(self._config, networkAccess)
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
    when(networkAccess).login('a', 'b').thenReturn(opener)
    when(networkAccess).issues_page(opener).thenRaise(urllib.request.URLError(''))

    l =CourrierInternationalLoader(self._config, networkAccess)
    l.init()
    try:
      l.issues()
      self.fail("No exception raised")
    except LoaderException:
      pass

    error = urllib.request.HTTPError(*[None for i in range(5)])
    when(networkAccess).issues_page(opener).thenRaise(error)
    l = CourrierInternationalLoader(self._config, networkAccess)
    l.init()
    try:
      l.issues()
      self.fail("No exception raised")
    except LoaderException:
      pass

  def testFindIssuesInPage(self):
    htmlSrc  = u'<div class="hebdo-box_1"><span class="hebdo-mag_num">N&deg; 1191</span>'
    htmlSrc += u'<div class="hebdo-event_date_mag">29 august 2013</div>'
    htmlSrc += u'<div class="hebdo-box_img"><a href="/magazine/2013/1191-vous-avez-dit-reprise">'
    htmlSrc += u'<img title="Vous avez dit reprise ?éé" alt="Vous avez dit reprise ?éé" src="/fil" '
    htmlSrc += u'alt="couverture" width="128" height="169" /></a></div>'
    htmlSrc += u'<div class="hebdo-event_date_mag"><a href="/magazine/2013/1191-vous-avez-dit-reprise">'
    htmlSrc += u'Vous avez dit reprise ?éé</a></div></div>'

    networkAccess = mock()
    when(networkAccess).login('a', 'b').thenReturn(1)
    when(networkAccess).issues_page(1).thenReturn(htmlSrc)

    l = CourrierInternationalLoader(self._config, networkAccess)
    l.init()
    issues = l.issues()

    self.assertEquals(len(issues), 1)
    self.assertEquals(issues[0].date(), datetime.date(2013,8,29))
    self.assertEquals(issues[0].title(), u"Vous avez dit reprise ?éé")
    self.assertEquals(issues[0].url(), "http://www.courrierinternational.com/magazine/2013/1191-vous-avez-dit-reprise")

  def testFindIssuesInvalidDate(self):
    htmlSrc  = u'<div class="hebdo-box_1"><span class="hebdo-mag_num">N&deg; 1191</span>'
    htmlSrc += u'<div class="hebdo-event_date_mag">29 ost 2013</div>'
    htmlSrc += u'<div class="hebdo-box_img"><a href="/magazine/2013/1191-vous-avez-dit-reprise">'
    htmlSrc += u'<img title="Vous avez dit reprise ?" alt="Vous avez dit reprise ?" src="/fil" '
    htmlSrc += u'alt="couverture" width="128" height="169" /></a></div>'
    htmlSrc += u'<div class="hebdo-event_date_mag"><a href="/magazine/2013/1191-vous-avez-dit-reprise">'
    htmlSrc += u'Vous avez dit reprise ?</a></div></div>'

    networkAccess = mock()
    when(networkAccess).login('a', 'b').thenReturn(1)
    when(networkAccess).issues_page(1).thenReturn(htmlSrc)

    l = CourrierInternationalLoader(self._config, networkAccess)
    l.init()
    issues = l.issues()

    self.assertEquals(len(issues), 0)

  def testInvalidCourrierInternationalIssue(self):
    loader = mock()
    d= datetime.date.today()
    try:
      CourrierInternationalIssue('test', d, loader, None)
      self.fail("No exception raised")
    except ValueError:
      pass


  def testDownloadPageWithNoLink(self):
    newspaper = mock()

    pageStream = io.BytesIO()
    when(newspaper).open('http://www.gigi.com').thenReturn(pageStream)
    d= datetime.date.today()
    issue = CourrierInternationalIssue('test', d, newspaper, 'http://www.gigi.com')
    try:
      issue.open()
      self.fail("No exception raised")
    except LoaderException:
      pass

  def testExceptionWhenDownloadPage(self):
    newspaper = mock()

    html = u'<a  href="http://www.ici.fr" title="Téléchargez en PDF">Download</a>'.encode('utf-8')
    html += html
    pageStream = io.BytesIO(html)
    when(newspaper).open('http://www.gigi.com').thenReturn(pageStream)

    stream = io.BytesIO(u"content".encode('utf-8'))
    when(newspaper).open('http://www.ici.fr').thenReturn(stream)

    d = datetime.date.today()
    issue = CourrierInternationalIssue('test', d, newspaper, 'http://www.gigi.com')
    self.assertEquals(b"content", issue.open().read())

  def testStreamExceptionWhenDownloadingPage(self):
    d = datetime.date.today()
    newspaper = mock()
    issue = CourrierInternationalIssue('test', d, newspaper, 'http://www.gigi.com')

    try:
      error = urllib.request.HTTPError(*[None for i in range(5)])
      when(newspaper).open('http://www.gigi.com').thenRaise(error)
      issue.open()
      self.fail("No exception raised")
    except LoaderException:
      pass
    try:
      when(newspaper).open('http://www.gigi.com').thenRaise(urllib.request.URLError(''))
      issue.open()
      self.fail("No exception raised")
    except LoaderException:
      pass

  def testStreamExceptionWhenClosing(self):
    issue = mock()
    stream = mock()

    lts = CourrierInternationalStream(stream, issue)
    when(stream).close().thenRaise(IOError)

    lts.close()

  def testStreamException(self):
    issue = mock()
    stream = mock()

    lts = CourrierInternationalStream(stream, issue)
    when(stream).read(130).thenRaise(Exception)

    try:
      lts.read(130)
      self.fail("No exception raised")
    except LoaderException:
      pass

    lts.close()
    verify(stream).close()

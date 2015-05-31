# -*- coding: utf-8 -*-

import unittest
from available_plugins.le24heures import *
from mockito import mock, verify, when
import mockito

import urllib

class Le24HeuresTest(unittest.TestCase):

    def setUp(self):
        self._config = mock()
        when(self._config).get('nd.plugin.24heures.username').thenReturn('a')
        when(self._config).get('nd.plugin.24heures.password').thenReturn('b')

    def testLogin(self):
        netaccess = mock()
        loader = Le24HeuresLoader(self._config, netaccess)

        loader.init()
        verify(netaccess).login('a', 'b')

        when(self._config).get('nd.plugin.24heures.username').thenReturn(None)
        loader = Le24HeuresLoader(self._config, netaccess)
        try:
            loader.init()
            self.fail("No username must raise a LoaderException")
        except LoaderException as e:
            pass

    def testLoadIssues(self):
        netaccess = mock()
        opener = mock()
        loader = Le24HeuresLoader(self._config, netaccess)
        when(netaccess).login('a', 'b').thenReturn(opener)

        loader.init()

        issue_lausanne = '<option selected="selected" value="20140201">01.02.14</option>'

        when(netaccess).issues_page(opener, mockito.any()).thenReturn('')
        when(netaccess).issues_page(opener, 'LAUSANNE').thenReturn(issue_lausanne)

        self.assertEquals(len(loader.issues()), 1)
        self.assertEquals(loader.issues()[0].date(), datetime.date(2014, 2, 1))
        self.assertEquals(loader.issues()[0].title(), '24 heures')



import unittest
from nd.newspaper_api import *
from mockito import mock, verify, when

class NewspaperAPITest(unittest.TestCase):

  def testConstructor(self):
    d = datetime.date(2014, 12, 13)
    ni = NewspaperIssue('abc', d)
    self.assertEquals(ni.title(), 'abc')
    self.assertEquals(ni.date(), d)
    self.assertEquals(str(ni), u'abc [2014-12-13]')

  def testInvalidDate(self):
    try:
      ni = NewspaperIssue('abc', None)
      self.fail("Invalid date not detected")
    except ValueError:
      pass

  def testInvalidLoader(self):
    try:
      d = datetime.date(2014, 12, 13)
      ni = OnlineNewspaperIssue('abc', d, None)
      self.fail("No exception raised")
    except ValueError:
      pass

  def testInvalidTitle(self):
    d = datetime.date(2014, 12, 13)
    try:
      ni = NewspaperIssue(None, d)
      self.fail("Invalid title not detected")
    except ValueError:
      pass

if __name__ == '__main__':
  unittest.main()


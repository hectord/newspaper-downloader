
import unittest
import io

import nd.config

from mockito import *

class TestConfig(unittest.TestCase):

  def testVariable(self):
    stream = io.StringIO("\r\n\r\ndsas=382")

    config = nd.config.Configuration()
    config.load(stream)

    self.assertEqual(config.get("titi"), "")

    self.assertEqual(config.get("dsas"), "382")

  def testComment(self):
    stream = io.StringIO("#ds")

    config = nd.config.Configuration()
    config.load(stream)

    self.assertEqual(config.get("titi"), "")

  def testIOException(self):
    mock_stream = mock()

    when(mock_stream).readall().thenRaise(IOError)

    config = nd.config.Configuration()
    config.load(mock_stream)

if __name__ == '__main__':
  unittest.main()


from nd.newspaper_loader import NewspaperDownloader
from nd.sender import SenderException
from nd.newspaper_api import *
import unittest
import datetime
import io

from mockito import *

class NewspaperDownloaderTest(unittest.TestCase):

    def testConstructor(self):
        try:
            NewspaperDownloader(None, None)
            self.fail("No exception raised")
        except ValueError:
            pass

    def testNoFileFound(self):
        sender = mock()

        repo, file = mock(), mock()
        when(repo).mkstemp().thenReturn(file)

        newspaper = mock()
        when(newspaper).issues().thenReturn([])

        d = NewspaperDownloader(sender, newspaper, repo)
        today = datetime.date(2013, 12, 14)

        ok = d(today)
        self.assertEquals(ok, False)

    def testDownloadFile(self):
        sender = mock()

        repo, file = mock(), mock()
        when(repo).mkstemp().thenReturn(file)
        when(file).close().thenRaise(Exception)

        today = datetime.date(2013, 12, 14)

        issue = mock()
        when(issue).date().thenReturn(today)
        when(issue).open().thenReturn(io.StringIO('hihi'))

        newspaper = mock()
        when(newspaper).issues().thenReturn([issue])

        d = NewspaperDownloader(sender, newspaper, repo)

        isOk = d(today)
        self.assertEquals(isOk, True)

        inorder.verify(file).write('hihi')
        inorder.verify(file).seek(0)
        inorder.verify(sender).upload_PDF(issue, file)
        inorder.verify(file).close()

    def testLoaderExcepion(self):
        sender = mock()

        today = datetime.date(2013, 12, 14)

        newspaper = mock()
        when(newspaper).init().thenRaise(LoaderException(''))
        when(sender).is_critical().thenReturn(False)

        d = NewspaperDownloader(sender, newspaper)
        isOk = d(today)
        self.assertEquals(isOk, True)

        when(sender).is_critical().thenReturn(True)
        isOk = d(today)
        self.assertEquals(isOk, False)

    def testSenderExcepion(self):
        sender = mock()
        today = datetime.date(2013, 12, 14)

        repo, file = mock(), mock()
        when(repo).mkstemp().thenReturn(file)

        issue = mock()
        when(issue).date().thenReturn(today)
        when(issue).open().thenReturn(file)

        newspaper = mock()
        when(newspaper).issues().thenReturn([issue])

        when(sender).upload_PDF(issue, any()).thenRaise(SenderException)

        d = NewspaperDownloader(sender, newspaper, repo)

        when(sender).is_critical().thenReturn(True)
        isOk = d(today)
        self.assertEquals(isOk, False)

        when(sender).is_critical().thenReturn(False)
        isOk = d(today)
        self.assertEquals(isOk, True)

    def testIOError(self):
        sender = mock()

        repo= mock()
        when(repo).mkstemp().thenRaise(IOError)

        today = datetime.date(2013, 12, 14)

        issue = mock()
        when(issue).date().thenReturn(today)

        newspaper = mock()
        when(newspaper).issues().thenReturn([issue])

        d = NewspaperDownloader(sender, newspaper, repo)

        when(sender).is_critical().thenReturn(True)
        isOk = d(today)
        self.assertEquals(isOk, False)

        when(repo).mkstemp().thenRaise(Exception)
        when(sender).is_critical().thenReturn(False)
        isOk = d(today)
        self.assertEquals(isOk, True)


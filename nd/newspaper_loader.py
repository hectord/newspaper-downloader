
from nd.newspaper_api import NewspaperLoader, NewspaperIssue, NewspaperStream, LoaderException
from nd.sender import SenderException

import tempfile, os, logging

class DocRepository(object):
  def mkstemp(self):
    return tempfile.NamedTemporaryFile()

class NewspaperDownloader(object):
  '''
  A downloader for a newspaper that send
   the new issues to the given sender.
  '''
  def __init__(self, senders, newspaper, repository=DocRepository()):
    '''
    Create a new newspaper downloader.
    '''
    if senders == None or newspaper == None or repository == None:
      raise ValueError
    self._senders = senders
    if not isinstance(self._senders, list):
      self._senders = [self._senders]
    self._newspaper = newspaper
    self._repository = repository

  def __repr__(self):
    return self._newspaper.name()

  def schedule(self):
    return self._newspaper.schedule()

  def wait_evolution(self):
    return self._newspaper.wait_evolution()

  def _save_locally(self, stream):
    '''
    Save the given "stream" in a temporary file and
     returns the path to this new file.
    (this file must be deleted after usage, if possible)
    '''
    file = self._repository.mkstemp()
    while True:
      data = stream.read()
      if not data:
        break
      file.write(data)
    stream.close()
    return file

  def get_scheduler(self):
    return self._newspaper.get_scheduler()

  def __call__(self, issue_date):
    '''
    Download the newspaper issues at the given date and send it
     to the sender.
    '''
    file = None
    logger = logging.getLogger(__name__)
    logger.info('Ready to download "%s" on %s',
                self._newspaper.name(), issue_date)
    success = True
    issue_found = False
    try:
      self._newspaper.init()
      for issue in self._newspaper.issues():
        if issue.date() == issue_date:
          logger.info('New issue found: %s', issue.title())
          file = self._save_locally(issue.open())
          issue_found = True

          for sender in self._senders:
            file.seek(0)
            try:
              sender.upload_PDF(issue, file)
            except SenderException:
              logger.exception('A sender cannot process the new issue')
              if sender.is_critical():
                success = False
      return success and issue_found
    except (IOError, OSError, LoaderException):
      logger.exception('Error when loading "%s" on %s',
                       self._newspaper.name(), issue_date)
    except Exception:
      logger.exception('Unknown exception when loading "%s"',
                       self._newspaper.name())
    finally:
      try:
        if file: file.close()
      except:
        logger.exception("Cannot close temporary file %s", file.name)
    return all(map(lambda x : not x.is_critical(), self._senders))

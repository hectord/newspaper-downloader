
import datetime

class NewspaperLoader(object):
  '''
  A loader for a particular newspaper.
  '''
  
  def get_scheduler(self):
    '''
    Return a new newspaper scheduler.
    '''
    raise NotImplementedError()

  def name(self):
    '''
    The newspaper name
    '''
    raise NotImplementedError()

  def init(self):
    '''
    Initialize the newspaper loader (for example: login on the website)
    '''
    raise NotImplementedError()

  def issues(self):
    '''
    Returns a list of all the issues at our disposal on the website
    '''
    raise NotImplementedError()

class NewspaperIssue(object):
  '''
  A newspaper issue (can be daily, monthly, ...)
  '''
  
  def __init__(self, title, date):
    '''
    Create a new newspaper issue.
    '''
    if title == None or not (isinstance(title, str) or isinstance(title, unicode)):
      raise ValueError('Invalid title')
    self._title = title
    if date == None or not isinstance(date, datetime.date):
      raise ValueError('Invalid date')
    self._date = date

  def __unicode__(self):
    return '%s [%s]' % (self._title, self._date)

  def __repr__(self):
    return '%s [%s]' % (self._title,
                        self._date)

  def title(self):
    '''
    The newspaper's title.
    '''
    return self._title

  def date(self):
    '''
    The newspaper release date.
    '''
    return self._date

class OnlineNewspaperIssue(NewspaperIssue):

  def __init__(self, title, date, loader):
    super(OnlineNewspaperIssue, self).__init__(title, date)
    if loader == None:
      raise ValueError('Invalid argument')
    self._loader = loader

  def loader(self):
    return self._loader

  def open(self):
    '''
    Open a new NewspaperStream
    '''
    raise NotImplementedError()

class NewspaperStream(object):
  '''
  A stream to download a newspaper
  '''

  def read(self):
    '''
    Read the stream or None if its end has been reached
    '''
    raise NotImplementedError()

  def close(self):
    '''
    Close and cleanup the stream (close the files?)
    '''
    pass

class LoaderException(Exception):
  '''
  En exception when a newspaper loader doesn't work.
  '''
  def __init__(self, msg):
    super(LoaderException, self).__init__(msg)


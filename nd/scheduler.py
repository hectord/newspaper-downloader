
import time

import datetime
from datetime import date, timedelta

import itertools, logging

class NewspaperSchedule(object):
  '''
  Define when a newspaper must be downloaded the next time (time and days of the week)
  '''
  def next_day(last_download):
    '''
    The next day the newspaper must be downloaded (after
     last_download)
    '''
    raise NotImplementedError()

class DailySchedule(NewspaperSchedule):
  '''
  Download the newspaper every day

  >>> d = DailySchedule()
  >>> d.next_day(datetime.date(day=7,month=6,year=2013))
  datetime.date(2013, 6, 8)
  >>> d = DailySchedule(also_saturday=False)
  >>> d.next_day(datetime.date(day=7,month=6,year=2013))
  datetime.date(2013, 6, 10)
  >>> d = DailySchedule()
  >>> d.next_day(datetime.date(day=8,month=6,year=2013))
  datetime.date(2013, 6, 10)
  '''
  def __init__(self, also_saturday=True):
    '''
    Constructor. also_saturday set if the newspaper is
     is published during the weekend (never on sunday)
    '''
    self._also_sunday = also_saturday

  def next_day(self, last_download):
    ret = last_download + timedelta(1)
    also_saturday = self._also_sunday
    while ret.isoweekday() == 7 or (ret.isoweekday() == 6 and not also_saturday):
      ret += timedelta(1)
    return ret

class WeeklySchedule(NewspaperSchedule):
  '''
  Download the newspaper every week

  >>> d = WeeklySchedule(7)
  >>> d.next_day(datetime.date(day=9,month=6,year=2013))
  datetime.date(2013, 6, 16)
  '''
  def __init__(self, publication_day):
    '''
    Constructor. publication_day defines when the newspaper
     is published and must be downloaded.
    '''
    self._publication_day = publication_day

  def next_day(self, last_download):
    ret = last_download + datetime.timedelta(1)
    publication_day = self._publication_day
    while ret.isoweekday() != publication_day:
      ret += datetime.timedelta(1)
    return ret

class Time(object):
  def today(self):
    return datetime.date.today()
  def now(self):
    return datetime.datetime.now()
  def sleep(self, wait_time):
    time.sleep(wait_time)

class NewspaperDownloadScheduler(object):

  NO_MORE_DOWNLOAD = 1
  NEW_ATTEMPT_IN_THE_FUTUR = 2

  def success(self):
    '''
    The last attempt is a success.
    '''
    raise NotImplementedError

  def failure(self):
    '''
    The last attempt is a failure.

    Return NO_MORE_DOWNLOAD if the issue won't be downloaded in the 
     futur (if it's a real failure). NEW_ATTEMPT_IN_THE_FUTUR otherwise
    '''
    raise NotImplementedError

  def wait_until(self):
    '''
    The datetime until when we have to sleep
     before trying to download the next issue.
    '''
    raise NotImplementedError

  def download_on_date(self):
    '''
    The issue date that must be downloaded next.
    '''
    raise NotImplementedError

class SimpleNewspaperDownloadScheduler(object):

  def __init__(self, newspaper_schedule, wait_evolution, time=Time()):

    self._next_download_date = time.today()

    self._newspaper_schedule = newspaper_schedule
    self._wait_evolution = wait_evolution

    self._reinit_try()

  def _next_try(self):
    try:
      self._current_wait_time += next(self._current_wait_evolution)

      next_download_date = self._newspaper_schedule.next_day(self._next_download_date)
      if self.wait_until().date() >= next_download_date:
        raise StopIteration

    except StopIteration:
      self._reinit_try()
      return NewspaperDownloadScheduler.NO_MORE_DOWNLOAD

    return NewspaperDownloadScheduler.NEW_ATTEMPT_IN_THE_FUTUR

  def _reinit_try(self):
    self._next_download_date = self._newspaper_schedule.next_day(self._next_download_date)
    self._current_wait_evolution, self._wait_evolution = itertools.tee(self._wait_evolution)
    self._current_wait_time = next(self._current_wait_evolution)

  def success(self):
    self._reinit_try()

  def failure(self):
    return self._next_try()

  def wait_until(self):
    midnight = datetime.time()
    wait_until = datetime.datetime.combine(self._next_download_date, midnight)
    wait_until += timedelta(seconds=self._current_wait_time)
    return wait_until

  def download_on_date(self):
    return self._next_download_date

def total_seconds(td):
  return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6

def download(downloaders, time=Time()):
  scheduler_downloader = list(map(lambda x : (x.get_scheduler(), x), downloaders))

  logger = logging.getLogger(__name__)

  while True:
    if len(scheduler_downloader) == 1:
      scheduler, downloader = scheduler_downloader[0]
    else:
      scheduler, downloader = min(*scheduler_downloader, key=lambda x : x[0].wait_until())

    wait_time = max(total_seconds(scheduler.wait_until() - time.now()), 0)

    logger.info("Wait for %d seconds", wait_time)
    time.sleep(wait_time)

    current_date = scheduler.download_on_date()
    if downloader(current_date):
      scheduler.success()
    else:
      failure_type = scheduler.failure()

      if failure_type == NewspaperDownloadScheduler.NO_MORE_DOWNLOAD:
        logger.critical('Failed to download %s on %s', downloader, current_date)

if __name__ == '__main__':
  import doctest
  doctest.testmod()


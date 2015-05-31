
import itertools

import unittest
from mockito import mock, when, verify, spy, inorder, any
import datetime

import nd.scheduler

class TestSchedule(unittest.TestCase):

    def setUp(self):

        class TimeMock(object):
            def __init__(self):
                self._base_date = datetime.datetime(hour=1, day=12, month=12, year=2014)
            def sleep(self, x):
                self._base_date += datetime.timedelta(seconds=x)
            def today(self):
                return self._base_date.date()
            def now(self):
                return self._base_date

        self._time = spy(TimeMock())

    class CallableMock(object):
        def __init__(self, mock):
            self.mock = mock
        def __call__(self, *args, **nargs):
            return self.mock.__call__(*args, **nargs)
        def __getattr__(self, method_name):
            return self.mock.__getattr__(method_name)

    def testNoError(self):
        time = mock()
        today = datetime.date(2012,12,22)
        download_date_1 = datetime.date(2012, 12, 13)
        download_date_2 = datetime.date(2012, 12, 15)
        when(time).today().thenReturn(today)

        schedule = mock()

        when(schedule).next_day(today).thenReturn(download_date_1)
        when(schedule).next_day(download_date_1).thenReturn(download_date_2)
        when(schedule).next_day(download_date_2).thenRaise(Exception)

        wait_evolution = (i for i in {44,45})

        scheduler = nd.scheduler.SimpleNewspaperDownloadScheduler(schedule, wait_evolution, time)

        self.assertEqual(scheduler.download_on_date(), download_date_1)
        w1 = datetime.datetime.combine(download_date_1, datetime.time(second=44))
        self.assertEqual(scheduler.wait_until(), w1)
        scheduler.success()
        self.assertEqual(scheduler.download_on_date(), download_date_2)
        w2 = datetime.datetime.combine(download_date_2, datetime.time(second=44))
        self.assertEqual(scheduler.wait_until(), w2)

    def testWithErrors(self):

        time = mock()
        today = datetime.date(2012,12,22)
        download_date_1 = datetime.date(2012, 12, 13)
        download_date_2 = datetime.date(2012, 12, 14)
        when(time).today().thenReturn(today)

        schedule = mock()

        when(schedule).next_day(today).thenReturn(download_date_1)
        when(schedule).next_day(download_date_1).thenReturn(download_date_2)
        when(schedule).next_day(download_date_2).thenReturn(datetime.date(2020,12,12))

        wait_evolution = (i for i in [44,45, 25*3600])

        scheduler = nd.scheduler.SimpleNewspaperDownloadScheduler(schedule, wait_evolution, time)

        NEW_ATTEMPT_IN_THE_FUTUR = nd.scheduler.NewspaperDownloadScheduler.NEW_ATTEMPT_IN_THE_FUTUR
        NO_MORE_DOWNLOAD = nd.scheduler.NewspaperDownloadScheduler.NO_MORE_DOWNLOAD

        self.assertEqual(scheduler.failure(), NEW_ATTEMPT_IN_THE_FUTUR)
        self.assertEqual(scheduler.download_on_date(), download_date_1)
        w1 = datetime.datetime.combine(download_date_1, datetime.time()) + \
                    datetime.timedelta(seconds=44+45)
        self.assertEqual(scheduler.wait_until(), w1)

        self.assertEqual(scheduler.failure(), NO_MORE_DOWNLOAD)
        self.assertEqual(scheduler.download_on_date(), download_date_2)
        w2 = datetime.datetime.combine(download_date_2, datetime.time()) + \
                    datetime.timedelta(seconds=44)
        self.assertEqual(scheduler.wait_until(), w2)

        self.assertEqual(scheduler.failure(), NEW_ATTEMPT_IN_THE_FUTUR)
        self.assertEqual(scheduler.failure(), NEW_ATTEMPT_IN_THE_FUTUR)
        self.assertEqual(scheduler.download_on_date(), download_date_2)
        w2 = datetime.datetime.combine(download_date_2, datetime.time()) + \
                    datetime.timedelta(seconds=44+45+25*3600)
        self.assertEqual(scheduler.wait_until(), w2)

    def testOneNewspaper(self):
        downloader, scheduler = mock(), mock()
        dcall = self.CallableMock(downloader)

        download_date_1 = datetime.date(2020,12,12)
        time_to_wait = 30883

        when(downloader).__call__(download_date_1).thenReturn(False).thenReturn(True)
        when(dcall).get_scheduler().thenReturn(scheduler)

        wait_until = self._time.now() + datetime.timedelta(seconds=time_to_wait)

        when(scheduler).wait_until().thenReturn(wait_until)
        when(scheduler).download_on_date().thenReturn(download_date_1)
        NO_MORE_DOWNLOAD = nd.scheduler.NewspaperDownloadScheduler.NO_MORE_DOWNLOAD
        when(scheduler).failure().thenReturn(NO_MORE_DOWNLOAD)
        when(scheduler).success().thenRaise(KeyboardInterrupt)

        try:
            nd.scheduler.download([dcall], self._time)
            self.fail("The exception should be raised")
        except KeyboardInterrupt as e:
            pass

        verify(self._time).sleep(time_to_wait)
        verify(self._time).sleep(0)

        verify(scheduler).failure()
        verify(scheduler).success()

    def testSeveralNewspaper(self):
        downloader1, scheduler1 = mock(), mock()
        dcall1 = self.CallableMock(downloader1)
        download_date_1 = datetime.date(2020,12,12)
        time_to_wait_1 = 200

        when(downloader1).__call__(download_date_1).thenReturn(True).thenRaise(KeyboardInterrupt)
        when(downloader1).get_scheduler().thenReturn(scheduler1)
        wait_until_1 = self._time.now() + datetime.timedelta(seconds=time_to_wait_1)

        when(scheduler1).wait_until().thenReturn(wait_until_1)
        when(scheduler1).download_on_date().thenReturn(download_date_1)

        downloader2, scheduler2 = mock(), mock()
        dcall2 = self.CallableMock(downloader2)
        download_date_2 = datetime.date(2020,12,11)
        time_to_wait_2 = 12

        when(downloader2).__call__(download_date_2).thenReturn(True).thenRaise(KeyboardInterrupt)
        when(downloader2).get_scheduler().thenReturn(scheduler2)
        wait_until_2 = self._time.now() + datetime.timedelta(seconds=time_to_wait_2)
        wait_until_after = self._time.now() + datetime.timedelta(seconds=max(time_to_wait_1,time_to_wait_2)+1)
        when(scheduler2).wait_until().thenReturn(wait_until_2).thenReturn(wait_until_after)
        when(scheduler2).download_on_date().thenReturn(download_date_2)

        try:
            nd.scheduler.download([dcall1, dcall2], self._time)
            self.fail("The exception should be raised")
        except KeyboardInterrupt as e:
            pass

        verify(scheduler1).success()
        verify(scheduler2).success()

    def testNoNewspaper(self):
        try:
            nd.scheduler.download([], self._time)
            self.fail("No exception raised")
        except TypeError:
            pass

    def testDailySchedule(self):
        d = nd.scheduler.DailySchedule()
        date = d.next_day(datetime.date(day=8,month=6,year=2013))
        self.assertEqual(date, datetime.date(2013, 6, 10))

        date = d.next_day(datetime.date(day=7,month=6,year=2013))
        self.assertEqual(date, datetime.date(2013, 6, 8))


    def testDailyScheduleWeekend(self):
        d = nd.scheduler.DailySchedule(also_saturday=False)
        date = d.next_day(datetime.date(day=7,month=6,year=2013))
        self.assertEqual(date, datetime.date(2013, 6, 10))

    def testWeeklySchedule(self):
        d = nd.scheduler.WeeklySchedule(7)
        date = d.next_day(datetime.date(day=9,month=6,year=2013))
        self.assertEqual(date, datetime.date(2013, 6, 16))

if __name__ == '__main__':
    unittest.main()

# -*- coding: utf-8 -*-

import unittest
from nd.sender import *
from nd.db import *
from mockito import mock, verify, when, any
import io, datetime

class DBSenderTest(unittest.TestCase):

    def testInvalidPersistedNewspaperIssueConstructor(self):

        try:
            PersistedNewspaperIssue(None, 'test', datetime.date.today(), None, None)
            self.fail("No exception thrown")
        except ValueError:
            pass

    def testDoubleInitialization(self):
        sqlite = sqlite3.connect(':memory:')
        dbs = DB(sqlite)

        c = sqlite.cursor()
        sql = "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='%s';"
        f = c.execute(sql % 'issue').fetchone()
        self.assertEquals(f, (1,))

        sql = "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='%s';"
        f = c.execute(sql % 'newspaper').fetchone()
        self.assertEquals(f, (1,))

        sql = "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='%s';"
        f = c.execute(sql % 'user').fetchone()
        self.assertEquals(f, (1,))
        c.close()

        other = DB(sqlite)

    def testAddIssues(self):
        sqlite = sqlite3.connect(':memory:')
        db = DB(sqlite)

        newspaperissue = mock()
        when(newspaperissue).title().thenReturn('LeTitré')
        d = datetime.date(2012, 12, 2)
        when(newspaperissue).date().thenReturn(d)
        newspaper = mock()
        when(newspaper).name().thenReturn('LT')
        when(newspaperissue).loader().thenReturn(newspaper)

        db.add_issue(newspaperissue, 'pathi.txt', 'lil.tot')
        db.add_issue(newspaperissue, 'pathi.txt')

        self.assertEquals(list(db.newspapers()), ['LT'])
        issues = db.issues()
        self.assertEquals(len(issues), 2)

        issue = issues[0]
        self.assertEquals(issue.path(), 'pathi.txt')
        self.assertTrue(isinstance(issue.id(), int))
        self.assertEquals(issue.newspaper(), 'LT')
        self.assertEquals(issue.title(), 'LeTitré')
        self.assertEquals(issue.thumbnail_path(), 'lil.tot')
        self.assertEquals(issue.date(), d)

        issue = issues[1]
        self.assertEquals(issue.thumbnail_path(), None)

        issues = db.issues(id=issue.id())
        self.assertEquals(len(issues), 1)

        issues = db.issues(id=-1)
        self.assertEquals(len(issues), 0)

        issues = db.issues(name=issue.newspaper())
        self.assertEquals(len(issues), 2)

        issues1 = db.issues(name=issue.newspaper(), from_nb=(0,1))
        self.assertEquals(len(issues1), 1)

        issues2 = db.issues(name=issue.newspaper(), from_nb=(1,1))
        self.assertEquals(len(issues2), 1)

        self.assertNotEquals(issues1[0].id(), issues2[0].id())

    def testInvalidValues(self):
        try:
            DBSender(None, None)
            self.fail("No exception raised")
        except ValueError:
            pass

    def testExceptionUploadPDF(self):
        dirmanager, db = mock(), mock()
        sender = DBSender(dirmanager, db)

        newspaperissue = mock()

        when(newspaperissue).title().thenReturn('abc')
        when(dirmanager).create_file(any()).thenRaise(OSError)
        try:
            sender.upload_PDF(newspaperissue,
                              io.StringIO())
            self.fail("No exception raised")
        except SenderException:
            pass

        ret = (io.StringIO(), 'test')
        when(dirmanager).create_file(any()).thenReturn(ret)
        when(db).add_issue(any(), any(), None).thenRaise(DBException)
        try:
            sender.upload_PDF(newspaperissue,
                              io.StringIO())
            self.fail("No exception raised")
        except SenderException:
            pass

    def testSaveNewspaper(self):
        dirmanager = mock()
        newfile = io.StringIO('')
        file = (newfile, 'content.txt')
        when(dirmanager).create_file('LeTitre').thenReturn(file)
        when(dirmanager).create_thumbnail('LeTitre', 'content.txt').thenReturn('thumb.png')

        newspaperissue = mock()
        when(newspaperissue).title().thenReturn('LeTitre')
        d = datetime.date(2012, 12, 2)
        when(newspaperissue).date().thenReturn(d)
        newspaper = mock()
        when(newspaper).name().thenReturn('LT')
        when(newspaperissue).loader().thenReturn(newspaper)

        db = mock()
        dbs = DBSender(dirmanager, db)

        stream = io.StringIO('TheContent')
        dbs.upload_PDF(newspaperissue, stream)

        verify(db).add_issue(newspaperissue, 'content.txt', 'thumb.png')
        #self.assertEquals(newfile.getvalue(), 'TheContent')

    def testExceptionWhenCreatingAThumbnails(self):
        dirmanager = mock()
        newfile = io.StringIO('')
        file = (newfile, 'content.txt')
        when(dirmanager).create_file('LeTitre').thenReturn(file)
        when(dirmanager).create_thumbnail(any(),any()).thenRaise(IOError)

        newspaperissue = mock()
        when(newspaperissue).title().thenReturn('LeTitre')
        d = datetime.date(2012, 12, 2)
        when(newspaperissue).date().thenReturn(d)
        newspaper = mock()
        when(newspaper).name().thenReturn('LT')
        when(newspaperissue).loader().thenReturn(newspaper)

        db = mock()
        dbs = DBSender(dirmanager, db)

        stream = io.StringIO('TheContent')
        dbs.upload_PDF(newspaperissue, stream)

        verify(db).add_issue(newspaperissue, 'content.txt', None)

    def testDirManager(self):
        d = DirManager('.')

    def testDirManagerInvalidDir(self):
        try:
            d = DirManager('in va lid')
            self.fail("No exception raised")
        except ValueError:
            pass

    def testCriticalSender(self):
        self.assertFalse(Sender(False).is_critical())
        self.assertTrue(Sender(True).is_critical())
        try:
            Sender(None)
            self.fail("No exception raised")
        except ValueError:
            pass

    def testAuthentification(self):
        sqlite = sqlite3.connect(':memory:')
        db = DB(sqlite)

        db.add_user('titi', 'lol')

        self.assertNotEquals(db.check_auth('titi', 'lol'), None)
        self.assertEqual(db.check_auth('sb', 'lol'), None)
        self.assertNotEquals(db.check_auth('titi'), None)
        self.assertEqual(db.check_auth('dbs'), None)

        db.add_user('titi', 'griis')
        self.assertNotEquals(db.check_auth('titi', 'griis'), None)
        self.assertEqual(db.check_auth('titi', 'lol'), None)

        db.delete_user('titi')
        self.assertEqual(db.check_auth('titi', 'griis'), None)

    def testDBExceptions(self):
        sqlite = mock()
        query = mock()

        when(sqlite).execute(any()).thenReturn(query)
        when(query).fetchone().thenReturn([1])
        dbs = DB(sqlite)

        when(query).fetchone().thenRaise(sqlite3.DatabaseError)
        when(sqlite).execute(any(), any()).thenRaise(sqlite3.DatabaseError)
        when(sqlite).execute(any()).thenRaise(sqlite3.DatabaseError)
        newspaperissue = mock()
        newspaper = mock()
        when(newspaper).name().thenReturn('LETEMPS')
        when(newspaperissue).loader().thenReturn(newspaper)

        try:
            dbs.add_issue(newspaperissue, 'tmp.txt')
            self.fail('No exception raised')
        except DBException:
            pass

        try:
            dbs.newspapers()
            self.fail('No exception raised')
        except DBException:
            pass

        try:
            dbs.issues()
            self.fail('No exception raised')
        except DBException:
            pass

        try:
            dbs.check_auth('ds')
            self.fail('No exception raised')
        except DBException:
            pass

        try:
            dbs = DB(sqlite)
            self.fail('No exception raised')
        except DBException:
            pass

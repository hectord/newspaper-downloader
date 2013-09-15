
import logging
import datetime
import hashlib

import sqlite3
import nd.newspaper_api
from contextlib import closing

class DBException(Exception):
  pass

class PersistedNewspaperIssue(nd.newspaper_api.NewspaperIssue):

  def __init__(self, id, title, date, path, newspaper, thumbnail_path=None):
    super(PersistedNewspaperIssue, self).__init__(title, date)
    if path == None or id == None or newspaper == None:
      raise ValueError('Invalid args')
    self._newspaper = newspaper
    self._path = path
    self._id = id
    self._thumbnail_path = thumbnail_path

  def path(self):
    return self._path

  def id(self):
    return self._id

  def newspaper(self):
    return self._newspaper
  
  def thumbnail_path(self):
    return self._thumbnail_path

class DB(object):
  def __init__(self, sqlhandle):
    self._sqlhandle = sqlhandle
    self._USER_TABLE = 'user'
    self._NEWSPAPER_TABLE = 'newspaper'
    self._ISSUE_TABLE = 'issue'
    
    try:
      user_fields = [('username', 'TEXT PRIMARY KEY'),
                     ('password', 'TEXT NOT NULL')]
      self._create_table(self._USER_TABLE, user_fields)

      newspaper_fields = [('name', 'TEXT PRIMARY KEY')]
      self._create_table(self._NEWSPAPER_TABLE, newspaper_fields)

      issue_fields = [('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
                      ('title', 'TEXT NOT NULL'),
                      ('date', 'DATE NOT NULL'),
                      ('newspaper', 'TEXT NOT NULL REFERENCES newspaper'),
                      ('path', 'TEXT NOT NULL'),
                      ('thumbnail_path', 'TEXT')]
      self._create_table(self._ISSUE_TABLE, issue_fields)
    except sqlite3.DatabaseError as e:
      raise DBException('Cannot initialize the database (%s)' % e)

  def close(self):
    self._sqlhandle.close()
  
  def _create_table(self, tableName, fields):
    sql_check = "SELECT COUNT(*) FROM sqlite_master " \
                "WHERE type='table' AND name='%s';"

    # we should'nt create a table twice (we don't check
    #  its schema, only if the table name already exists)
    if not self._sqlhandle.execute(sql_check % tableName).fetchone()[0]:
      fields = map(lambda x : '%s %s' % x, fields)
      sql = 'CREATE TABLE %s (%s)' \
                % (tableName, ','.join(fields))
      self._sqlhandle.execute(sql)

  def _ensure_newspaper_exists(self, newspaper_name):
    sql = 'SELECT COUNT(*) FROM %s WHERE name = ?'
    sql = sql % self._NEWSPAPER_TABLE

    nb_np = self._sqlhandle.execute(sql, (newspaper_name,)).fetchone()
    if nb_np[0] == 0:
      sql = 'INSERT INTO %s(name) VALUES(?)' % self._NEWSPAPER_TABLE
      self._sqlhandle.execute(sql, (newspaper_name,))

  def add_issue(self, newspaperissue, path, thumbnail_path=None):
    try:
      newspaper_name = newspaperissue.loader().name()
      self._ensure_newspaper_exists(newspaper_name)

      date = newspaperissue.date().strftime('%Y-%m-%d 00:00:00')
      title = newspaperissue.title()

      data = (title, date, path, newspaper_name, thumbnail_path)
      self._sqlhandle.execute("INSERT INTO %s(title, date, path, newspaper, thumbnail_path) VALUES(?, ?, ?, ?, ?)" \
                % self._ISSUE_TABLE, data)

      self._sqlhandle.commit()
    except sqlite3.DatabaseError as e:
      raise DBException('Cannot create an issue (%s)' % e)
  
  def newspapers(self):
    try:
      while self._sqlhandle:
        sql = 'SELECT name FROM %s ORDER BY name' % self._NEWSPAPER_TABLE
        names = self._sqlhandle.execute(sql).fetchall()
        return map(lambda x : x[0], names)
    except sqlite3.DatabaseError as e:
      raise DBException('Cannot fetch the newspapers (%s)' % e)

  def issues(self, name=None, id=None, from_nb=None):
    ret = []
    try:
      sql = 'SELECT id, title, DATE(date), path, newspaper, thumbnail_path FROM %s' \
              % self._ISSUE_TABLE

      data = ()
      if name != None:
        sql += ' WHERE newspaper = ?'
        data = (name,)
      elif id != None:
        sql += ' WHERE id = ?'
        data = (id,)

      sql += ' ORDER BY date DESC' 

      if from_nb != None:
        sql += ' LIMIT %d, %d' % from_nb

      query = self._sqlhandle.execute(sql, data)
      rows = query.fetchall()
      for row in rows:
        row = list(row)
        row[2] = datetime.datetime.strptime(row[2], '%Y-%m-%d').date()
        ret.append(PersistedNewspaperIssue(*row))
      return ret
    except sqlite3.DatabaseError as e:
      raise DBException('Cannot fetch the newspapers (%s)' % e)

  def __hashpassword(self, password):
      hash = hashlib.sha512()
      hash.update(password.encode('utf-8'))
      return hash.hexdigest()

  def user_exists(self, username):
    try:
      query = self._sqlhandle.execute('SELECT * FROM %s WHERE username = ?' % self._USER_TABLE, (username,))
      return query.fetchone() is not None
    except sqlite3.DatabaseError as e:
      raise DBException('Cannot access the database')

  def add_user(self, username, password):

    try:
      data = (self.__hashpassword(password), username)

      if not self.user_exists(username):
        sql = 'INSERT INTO %s(password, username) VALUES(?, ?)' % self._USER_TABLE
      else:
        sql = 'UPDATE %s SET password = ? WHERE username = ?' % self._USER_TABLE

      self._sqlhandle.execute(sql, data)
      self._sqlhandle.commit()
    except sqlite3.DatabaseError as e:
      raise DBException('Cannot create user %s. Does he already exist?' % username)

  def check_auth(self, username, password=None):
    sql = 'SELECT password FROM %s WHERE username = ?' % \
            self._USER_TABLE
    
    data = [username,]
    if password != None:
      sql += ' AND password = ?'
      data += [self.__hashpassword(password)]

    try:
      query = self._sqlhandle.execute(sql, data)
      row = query.fetchone()
      return row[0] if row else None
    except sqlite3.DatabaseError as e:
      raise DBException('Cannot authenticate')

  def delete_user(self, username):
    if not self.user_exists(username):
      raise DBException("User %s does not exist" % username)

    sql = 'DELETE FROM %s WHERE username = ?' % \
            self._USER_TABLE
    try:
      query = self._sqlhandle.execute(sql, (username,))
      self._sqlhandle.commit()
    except sqlite3.DatabaseError as e:
      raise DBException('Cannot delete this user')


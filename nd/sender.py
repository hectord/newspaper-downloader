
import smtplib
import email
import email.mime.text
import shutil

import logging

from nd.newspaper_api import LoaderException

import sqlite3
import os, os.path
import tempfile, subprocess
import nd.db

CONVERT_PATH = 'convert'

class SenderException(Exception):
    pass

class Sender(object):

    def __init__(self, critical):
        if critical == None or not isinstance(critical, bool):
            raise ValueError("Invalid argument")
        self._critical = critical

    def is_critical(self):
        return self._critical

    def upload_PDF(filename, filestream):
        '''
        Upload the content of filestream under the name
         "filename"
        '''
        raise NotImplementedError()

class GMailSender(Sender):

    def __init__(self, mail):
        super(GMailSender, self).__init__(False)
        self._mail = mail
        self._LOGIN_GMAIL = 'letemps.mailer@gmail.com'
        self._PASSWORD_GMAIL = '1Qa2Wd4Ef)'

    def _send_mail(self, msg):
        smtp = smtplib.SMTP("smtp.gmail.com", 587)
        smtp.ehlo() # for tls add this line
        smtp.starttls() # for tls add this line
        smtp.ehlo() # for tls add this line
        smtp.login(self._LOGIN_GMAIL, self._PASSWORD_GMAIL)
        smtp.sendmail(self._LOGIN_GMAIL, [self._mail], msg)
        smtp.quit()

    def upload_PDF(self, newspaperissue, stream):
        filename = newspaperissue.title()
        filename += ' ' + newspaperissue.date().strftime('%d-%m-%y')
        filename += '.pdf'

        emailmsg = email.MIMEMultipart.MIMEMultipart('alternative')
        emailmsg['Subject'] = filename
        emailmsg['From'] = self._LOGIN_GMAIL
        emailmsg['To'] = self._mail

        emailmsg.attach(email.mime.text.MIMEText('','plain'))

        filemsg = email.mime.base.MIMEBase('application','application/pdf')

        filemsg.set_payload(stream.read())
        email.encoders.encode_base64(filemsg)
        filemsg.add_header('Content-Disposition','attachment;filename=%s' % filename)
        emailmsg.attach(filemsg)

        self._send_mail(emailmsg.as_string())

        logger = logging.getLogger(__name__)
        logger.info('Email sent to %s (filename: %s)', self._mail, filename)

class DirManager(object):

    def __init__(self, dir):
        if os.path.isdir(dir):
            self._dir = dir
        else:
            raise ValueError('"%s" is not a directory' % dir)

    def create_file(self, base_name):
        ascii_base_name = base_name.encode('ascii', 'ignore').decode('ascii')
        handle, path = tempfile.mkstemp(suffix='.pdf', prefix=ascii_base_name, dir=self._dir)
        filename = os.path.basename(path)
        return os.fdopen(handle, "wb"), filename

    def create_thumbnail(self, base_name, pdf_name):
        ascii_base_name = base_name.encode('ascii', 'ignore').decode('ascii')
        thumbnail_path = tempfile.mktemp(dir=self._dir, prefix=ascii_base_name, suffix='.png')

        pdf_path = os.path.join(self._dir, pdf_name)
        params = [CONVERT_PATH, '%s[0]' % pdf_path, '-resize', '250x420', \
                  '-crop', '250x324+0+0', thumbnail_path]
        code = subprocess.call(params)
        if code != 0:
            raise OSError('Error code %d when executing %s', \
                          code, ' '.join(params))

        thumbnail_name = os.path.basename(thumbnail_path)
        return thumbnail_name

class DBSender(Sender):

    def __init__(self, dirmanager, db):
        super(DBSender, self).__init__(True)

        if dirmanager == None or db == None:
            raise ValueError('Invalid constructor value')

        self._dirmanager = dirmanager
        self._db = db

    def upload_PDF(self, newspaperissue, stream):
        try:
            logger = logging.getLogger(__name__)

            title = newspaperissue.title()
            # we cannot use ':' characters with imagemagick:
            #  http://www.imagemagick.org/discourse-server/viewtopic.php?f=1&t=21314
            title = title.replace(':', '')
            d, path = self._dirmanager.create_file(title)

            shutil.copyfileobj(stream, d)
            d.close()

            try:
                thumbnail_name = self._dirmanager.create_thumbnail(title, path)
                logger.info('Thumbnail created in %s', thumbnail_name)
            except (IOError, OSError) as e:
                logger.warning('Exception %s when creating a thumbnail', e)
                thumbnail_name = None

            self._db.add_issue(newspaperissue, path, thumbnail_name)

            logger.info('Newspaper %s saved in the database (path: %s)', \
                        newspaperissue.title(), path)
        except (OSError, IOError) as e:
            raise SenderException('Impossible to save locally the file for %s (%s)' % (newspaperissue, e))
        except nd.db.DBException as e:
            raise SenderException('Unable to save %s in database' % newspaperissue)


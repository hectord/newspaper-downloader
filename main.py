
import logging, logging.handlers
import nd.plugin_utils
import nd.scheduler
import nd.newspaper_loader
import nd.sender
import nd.config

import sqlite3

import sys, locale
locale.setlocale(locale.LC_ALL, 'fr_CH.utf-8')

from argparse import ArgumentParser

# the options available
parser = ArgumentParser(description='Newspaper downloader')
parser.add_argument("-l", "--logs", type=str, default="downloader.log", help="The log file to be used")
parser.add_argument("-d", "--db", type=str, default="newspapers", help="The database used to store metadata")

parser.add_argument("-e", "--email", nargs=1, dest="email", help="The mail to which the newspapers must be sent")

parser.add_argument("-c", "--config", nargs=1, default="config.cfg", dest="config", help="The configuration file")

parser.add_argument("-p", "--plugins", nargs='+', default=None, dest="plugins", type=str, help="Use a subset of the available plugins")

options = parser.parse_args()

# create the application's logger
logger = logging.getLogger('')
logger.setLevel(logging.INFO)
logHandler = logging.handlers.RotatingFileHandler(options.logs, maxBytes=1024*1024, backupCount=5)
formatter = logging.Formatter('%(levelname)s:%(asctime)s: %(message)s', datefmt='%d.%m.%Y %H:%M')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

try:
  config = nd.config.Configuration()
  config_file = open(options.config)
  config.load(config_file)
except (IOError, OSError, nd.config.ConfigurationException) as e:
  logger.critical(e)
  sys.exit(1)

GMAIL_EMAIL = config.get("nd.downloader.log.email")
GMAIL_PASSWORD = config.get("nd.downloader.log.password")

# add a email handler (only for critical errors)
if GMAIL_EMAIL and GMAIL_PASSWORD:
  mailhandler = logging.handlers.SMTPHandler(
                    mailhost='smtp.gmail.com',
                    fromaddr=GMAIL_EMAIL,
                    toaddrs=[GMAIL_EMAIL],
                    subject='NP: Critical error',
                    credentials=(GMAIL_EMAIL, GMAIL_PASSWORD),
                    secure=())
  mailhandler.setLevel(logging.CRITICAL)
  logger.addHandler(mailhandler)

# load the plugins
imported_plugins = nd.plugin_utils.load_plugins()
newspapers = []
for imported_plugin in imported_plugins:
  try:
    plugin = imported_plugin(config)
    logger.info("Found newspaper loader for '%s'", plugin.name())
    newspapers.append(plugin)
  except Exception as e:
    logger.info("Module '%s' disabled (Exception %s)", imported_plugin, e)

if options.plugins != None:
  newspapers = list(filter(lambda x : x.name() in options.plugins, newspapers))
  logger.info("Newspapers kept: %s", ', '.join(map(lambda x : x.name(), newspapers)))

  if len(newspapers) != len(options.plugins):
    logger.error("At least one newspaper among %s doesn't exist", ", ".join(options.plugins))
    sys.exit(1)

if not newspapers:
  logger.info("No module found")
  sys.exit(1)

db_name = '%s.db' % options.db
db_folder = options.db
try:
  ndb = sqlite3.connect(db_name)
  try:
    newspaperDir = nd.sender.DirManager(db_folder)
  except IOError as e:
    logger.error(str(e))
    sys.exit(1)

  db = nd.db.DB(ndb)
  dbSender = nd.sender.DBSender(newspaperDir, db)
  senders = [dbSender]
  if options.email != None:
    senders.append(nd.sender.GMailSender(options.email))

  downloaders = []
  for newspaper in newspapers:
    downloaders.append(nd.newspaper_loader.NewspaperDownloader(senders, newspaper))

  nd.scheduler.download(downloaders)

except nd.newspaper_api.LoaderException as e:
  logger.error(e)
except sqlite3.Error as e:
  logger.exception("Error when loading the database")
except Exception as e:
  logger.critical("Unknown exception " + str(e), exc_info=True)


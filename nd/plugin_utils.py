
from nd.newspaper_api import NewspaperLoader

import nd.plugins, pkgutil, inspect
import logging

def load_plugins():
  '''
  Load all the plugins to download newspapers
  '''
  imported_plugins = []
  logger = logging.getLogger(__name__)

  for importer, modname, ispkg in pkgutil.iter_modules(nd.plugins.__path__):
    try:
      plugin = __import__('nd.plugins.%s' % modname, fromlist=[modname])
      foundImporter = False
      for name, obj in inspect.getmembers(plugin):
        if inspect.isclass(obj) and issubclass(obj, NewspaperLoader) \
            and obj != NewspaperLoader:
          foundImporter = True
          imported_plugins.append(obj)
      if not foundImporter:
        logger.warning("No importer found in '%s'", modname)
    except Exception as e:
      logger.exception("Invalid plugin '%s'", modname)
  return imported_plugins

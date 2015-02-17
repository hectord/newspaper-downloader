'''
A tool to read simple configuration file
'''

class ConfigurationException(Exception):
  pass

class Configuration(object):

  def __init__(self):
    self._inputs = {}

  def load(self, fileio):
    try:
      while True:

        line = fileio.readline()

        if not line:
          break

        if '#' in line:
          line = line[:line.index('#')]

        line = line.strip()
        if not line:
          continue

        if '=' not in line:
          data = dict(line=line)
          raise ConfigurationException("Invalid line: %(line)s", data)

        separator = line.index('=')

        varname, value = line[:separator].strip(), line[separator+1:].strip()

        if not varname:
          data = dict(line=line)
          raise ConfigurationException("Invalid line: %(line)s", data)

        self._inputs[varname] = value

    except (IOError, OSError):
      raise ConfigurationException("Unable to access the configuration file")

  def get(self, variable):
    return self._inputs.get(variable, "")


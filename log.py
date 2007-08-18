import logging
import traceback
import sys

# Borrowed the LogStream from fogle  -- Thanks man!
class LogStream(object):
    def __init__(self, logger=None, level=logging.INFO):
        self.level = level
        if not logger:
            self.logger = logging.getLogger()
        else:
            self.logger = logger

    def write(self, text):
        self.logger.log(self.level, text.strip())    

class LogHandler(logging.Handler):
    def __init__(self, format=None):
        logging.Handler.__init__(self)
        format = format or "%(asctime)s %(levelname)s %(message)s"
        formatter = logging.Formatter(format)
        self.setFormatter(formatter)
        self.listeners = []
    def register(self, func):
        self.listeners.append(func)
    def unregister(self, func):
        self.listeners.remove(func)
    def emit(self, record):
        for listener in self.listeners:
            listener(self, record)

def redirect_stdout(logname=None):
    #sys.stdout = LogStream(logging.getLogger(logname), level=logging.INFO)
    pass

def redirect_stderr(logname=None):
    #sys.stderr = LogStream(logging.getLogger(logname), level=logging.INFO)
    pass

# Global stuff
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    filename="log.txt",
                    filemode='w')

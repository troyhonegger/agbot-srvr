# For logging API documentation see https://docs.python.org/3/library/logging.html

import logging
from logging import handlers
import os

def get_logger(file):
	logger = logging.getLogger('agbot')
	logger.setLevel(logging.DEBUG)
	if not logger.hasHandlers():
		handler = handlers.TimedRotatingFileHandler('/var/log/agbot.log', when = 'midnight', backupCount = 31)
		handler.setFormatter(logging.Formatter('%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s'))
		logger.addHandler(handler)
	if file is not None:
		name = os.path.splitext(os.path.relpath(file))[0]
		print(name)
		child = logging.getLogger('agbot.%s'%(name))
		child.setLevel(logging.DEBUG)
		return child
	return logger

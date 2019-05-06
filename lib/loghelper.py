# For logging API documentation see https://docs.python.org/3/library/logging.html

import logging
from logging import handlers
import os

def get_logger(file):
	logger = logging.getLogger('agbot')
	if not logger.hasHandlers():
		handler = handlers.TimedRotatingFileHandler('/var/data/logs/agbot.log', when = 'midnight', backupCount = 31)
		handler.setFormatter(logging.Formatter('%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s'))
		logger.addHandler(handler)
	if file is not None:
		child = logging.getLogger('agbot.%s'%(os.path.splitext(file)[0]))
		child.setEffectiveLevel(logging.DEBUG)
		return child

# For logging API documentation see https://docs.python.org/3/library/logging.html

import logging
import os

def get_logger(file):
	logger = logging.getLogger('agbot')
	if not logger.hasHandlers():
		logger.addHandler(logging.FileHandler('/var/data/logs/agbot.log'))
	if file is not None:
		child = logging.getLogger('agbot.%s'%(os.path.splitext(file)[0]))
		child.setEffectiveLevel(logging.DEBUG)
		return child
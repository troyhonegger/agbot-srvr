#!/usr/bin/python

import time
import argparse

from lib import loghelper
from lib import multivator
from lib import speed_ctrl

if __name__ == '__main__':
	parser = argparse.ArgumentParser(prog = 'keep_alive', description = 'Send KeepAlive messages to the multivator and/or the speed controller')
	parser.add_argument('-m', '--ignore-multivator', action = 'store_true', help = 'Suppress sending KeepAlive messages to the multivator')
	parser.add_argument('-s', '--ignore-speed-controller', action = 'store_true', help = 'Suppress sending KeepAlive messages to the speed controller')
	parser.add_argument('-d', '--delay', type = float, default = 1.0, help = 'Set the delay length in between sending messages')

	args = parser.parse_args()

	log = loghelper.get_logger(__file__)

	if not args.ignore_multivator:
		m = multivator.Multivator()
	else:
		# passing a dummy class around, with all the methods replaced with no-ops, is easier,
		# and arguably more elegant, than putting 'if not None' checks everywhere.
		# We do the same thing with DummySpeedController
		class DummyMultivator:
			def __init__(self):
				pass
			def isconnected(self):
				return True
			def connect(self):
				pass
			def disconnect(self):
				pass
			def estop(self):
				pass
			def keep_alive(self):
				pass
		m = DummyMultivator()
	if not args.ignore_speed_controller:
		s = speed_ctrl.SpeedController()
	else:
		class DummySpeedController:
			def __init__(self):
				pass
			def isconnected(self):
				return True
			def connect(self):
				pass
			def disconnect(self):
				pass
			def estop(self):
				pass
			def keep_alive(self):
				pass
		s = DummySpeedController()
	try:
		while True:
			try:
				if not m.isconnected():
					m.connect()
				m.keep_alive()
			except multivator.MultivatorException as ex:
				m.disconnect()
				log.error('Multivator KeepAlive FAILED.')
			try:
				if not s.isconnected():
					s.connect()
				s.keep_alive()
			except speed_ctrl.SpeedControlException as ex:
				s.disconnect()
				log.error('SpeedController KeepAlive FAILED.')
			time.sleep(args.delay)
	finally:
		m.disconnect()
		s.disconnect()

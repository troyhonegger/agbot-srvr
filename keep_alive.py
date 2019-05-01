#!/usr/bin/python

#TODO: update this to use standardized logging

import time
import sys
import argparse

if __name__ == '__main__':
	parser = argparse.ArgumentParser(prog = 'keep_alive', description = 'Send KeepAlive messages to the multivator and/or the speed controller')
	parser.add_argument('-m', '--multivator', action = 'store_true', help = 'Send KeepAlive messages to the multivator')
	parser.add_argument('-s', '--speed-controller', action = 'store_true', help = 'Send KeepAlive messages to the speed controller')
	parser.add_argument('-d', '--delay', type = float, default = 1.0, help = 'Set the delay length in between sending messages')

	args = parser.parse_args()

	if args.multivator:
		import multivator
		def inst_multivator():
			m = multivator.Multivator()
			m.connect()
			return m
	else:
		# passing a dummy class around, with all the methods replaced with no-ops, is easier,
		# and arguably more elegant, than putting 'if not None' checks everywhere.
		# We do the same thing with DummySpeedController
		class DummyMultivator:
			def __init__(self):
				pass
			def disconnect(self):
				pass
			def estop(self):
				pass
			def keep_alive(self):
				pass
		def inst_multivator():
			return DummyMultivator()
	m = inst_multivator()
	if args.speed_controller:
		import speed_ctrl
		def inst_speed_controller():
			s = speed_ctrl.SpeedController()
			s.connect()
			return s
	else:
		class DummySpeedController:
			def __init__(self):
				pass
			def disconect(self):
				pass
			def estop(self):
				pass
			def keep_alive(self):
				pass
		def inst_speed_controller(self):
			return DummySpeedController()
	s = inst_speed_controller()
	
	def handle_error(m, s, source, ex):
		sys.stderr.write('%s: %s'%(source, str(ex)))
		try:
			if m is not None:
				m.disconnect()
			m = inst_multivator()
			m.estop()
		except multivator.MultivatorException as ex:
			sys.stderr.write('Multivator Estop failed: %s\n'%str(ex))
		try:
			if s is not None:
				s.disconnect()
			s = inst_multivator()
			s.estop()
		except speed_ctrl.SpeedControlException as ex:
			sys.stderr.write('SpeedControl Estop failed: %s\n'%str(ex))

	try:
		while True:
			try:
				m.keep_alive()
			except multivator.MultivatorException as ex:
				handle_error(m, s, 'Multivator', ex)
			try:
				s.keep_alive()
			except speed_ctrl.SpeedControlException as ex:
				handle_error(m, s, 'SpeedController', ex)
			time.sleep(args.delay)
	finally:
		m.disconnect()
		s.disconnect()

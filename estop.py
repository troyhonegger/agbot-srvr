#!/usr/bin/python

if __name__ == '__main__':
	parser = argparse.ArgumentParser(prog = 'estop', description = 'Send an estop command to the multivator and/or the speed controller')
	parser.add_argument('-m', '--multivator', action = 'store_true', help = 'Send KeepAlive messages to the multivator')
	parser.add_argument('-s', '--speed-controller', action = 'store_true', help = 'Send KeepAlive messages to the speed controller')
	parser.add_argument('-d', '--delay', type = float, default = 1.0, action = 'Set the delay length in between sending messages')
	
	args = parser.parse_args()
	
	num_failed = 0
	if (args.multivator):
		import multivator
		with multivator.Multivator() as m:
			try:
				m.estop()
			except multivator.MultivatorException:
				num_failed++
	if (args.speed_controller):
		import speed_ctrl
		with speed_ctrl.SpeedController() as s:
			try:
				s.estop()
			except speed_ctrl.SpeedControlException():
				num_failed++
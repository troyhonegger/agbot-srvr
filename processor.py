#!/usr/bin/python

# TODO: still need NMEA

import os
import datetime
import darknet
import records
import cameras
import multivator
import speed_ctrl
import logging

log = loghelper.get_logger(__file__)
CURRENT = os.path.join(records.DIR, records.CURRENT + records.EXT)

net = 0
meta = None
cams = []
sigint_received = False
file = None
mult = None
speed_controller = None

def start_processor():
	global net
	global meta
	global cams
	global file
	global mult
	log.info('Starting processor...')
	if os.exists(os.path.join(records.DIR, CURRENT))
		log.error('CURRENT file %s already exists. Throwing exception...', CURRENT)
		raise ValueError('Processor is already running. If you did not start processor, delete the file %s and try again'%(CURRENT))
	else:
		file = open(CURRENT, 'w')
		log.debug('Created %s', CURRENT)
	# TODO: it'd be nice to use argparse to avoid hard-coding .cfg, .weights, and .data file paths, except as defaults
	meta = darknet.load_meta(b'/home/agbot/Yolo_mark_2/x64/Release/data/obj.data')
	net = darknet.load_net(b'/home/agbot/Yolo_mark_2/x64/Release/yolo-obj.cfg', b'/home/agbot/Yolo_mark_2/x64/Release/backup/yolo-obj_final.weights', 0)
	log.debug('Loaded neural network and metadata. net = %d, meta.classes = %d', net, meta.classes)
	cams = cameras.open_cameras('id*')
	log.debug('Opened cameras - %d found', len(cams))
	mult = multivator.Multivator()
	mult.connect(mode = multivator.Mode.processing)
	speed_controller = speed_ctrl.SpeedController()
	speed_controller.connect()
	log.debug('Connected to multivator and speed controller.')

def process():
	pass #TODO

def stop_processor(sig, frame):
	log.info('Shutting down processor...')
	global file
	if file is not None:
		file.flush()
		file.close()
		file = None
		
		date = str(datetime.date.today)
		files = [file for file in os.listdir(records.DIR) if file.startswith(date) and file.endswith(records.EXT)]
		# trim the date and extension from the file names and parse the numbers
		numbers = [int(file[len(date) + 1:-len(records.EXT)]) for file in files]
		num = 0 if len(numbers) == 0 else max(numbers) + 1
		path = records.DIR + date + '_' + num + records.EXT
		log.debug('Moving %s to %s', CURRENT, path)
		shutil.copy(CURRENT, path)
		os.remove(CURRENT)
	if net != 0:
		global net
		global meta
		log.debug('Resetting neural network %d', net)
		darknet.reset_rnn(net)
		net = 0
		meta = None
	if len(cams) != 0:
		global cams
		log.debug('Releasing all cameras (%d found)', len(cams))
		for camera in cams:
			camera.release()
		cams = []
	if mult is not None:
		log.debug('Disconnecting from multivator')
		global mult
		mult.disconnect()
		mult = None
	if speed_controller is not None:
		log.debug('Disconnecting from speed controller')
		global speed_controller
		speed_controller.disconnect()
		speed_controller = None

def main():
	start_processor()
	try:
		while True:
			process()
			if sigint_received:
				log.info('Received SIGINT - terminating processor.')
				break
	except exception:
		log.exception(exception)
		raise
	finally:
		stop_processor()

def sigint_handler():
	"""Run whenever the process receives a SIGINT signal (either from a user pressing CTRL+C, or from another process).
	This handler prevents an immediate shutdown, but it sets a flag that signals the main loop to cleanup and stop the processor"""
	global sigint_received
	sigint_received = True
	signal.signal(signal.SIGINT, sigint_handler)

if __name__ == '__main__':
	# register SIGINT handler
	signal.signal(signal.SIGINT, stop_processor)
	main()

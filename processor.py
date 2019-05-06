#!/usr/bin/python

import os
import datetime
import shutil
import signal
import setproctitle

from lib import records
from lib import cameras
from lib import multivator
from lib import speed_ctrl
from lib import loghelper
from lib import nmea
from lib import darknet_wrapper
from lib import plants

log = loghelper.get_logger(__file__)
CURRENT = os.path.join(records.DIR, records.CURRENT + records.EXT)

# Adjust this to taste
THRESHOLD = 0.5

net = 0
meta = None
cams = []
cams_history = []
sigint_received = False
file = None
mult = None
speed_controller = None

# TODO: update this as needed to more accurately match our camera layout.
def map_location(camera_id, x, y):
	if camera_id == 'id0':
		return 0
	elif camera_id == 'id1':
		return 1
	elif camera_id == 'id2':
		return 2
	elif camera_id == 'id3':
		return 2
	elif camera_id == 'id4':
		return 3
	elif camera_id == 'id5':
		return 4
	else:
		return None

plants_map = { # TODO: fill this in with the class names
	'giant_ragweed': plants.Plants.Ragweed
}

def start_processor():
	global net
	global meta
	global cams
	global cams_history
	global file
	global mult
	log.info('Starting processor...')
	if os.path.exists(os.path.join(records.DIR, CURRENT)):
		log.error('CURRENT file %s already exists. Throwing exception...', CURRENT)
		raise ValueError('Processor is already running. If you did not start processor, delete the file %s and try again'%(CURRENT))
	else:
		file = open(CURRENT, 'w')
		log.debug('Created %s', CURRENT)
	# TODO: it'd be nice to use argparse to avoid hard-coding .cfg, .weights, and .data file paths, except as defaults
	meta = darknet_wrapper.load_meta(b'/home/agbot/Yolo_mark_2/x64/Release/data/obj.data')
	net = darknet_wrapper.load_net(b'/home/agbot/Yolo_mark_2/x64/Release/yolo-obj.cfg', b'/home/agbot/Yolo_mark_2/x64/Release/backup/yolo-obj_final.weights', 0)
	log.debug('Loaded neural network and metadata. net = %d, meta.classes = %d', net, meta.classes)
	cams = cameras.open_cameras('id*')
	cams_history= [None for cam in cams]
	log.debug('Opened cameras - %d found', len(cams))
	mult = multivator.Multivator(initial_mode = multivator.Mode.processing)
	mult.connect()
	speed_controller = speed_ctrl.SpeedController()
	speed_controller.connect()
	log.debug('Connected to multivator and speed controller.')

def process_detector():
	global net
	global meta
	global cams
	global cams_history
	global file
	global mult
	global speed_controller
	i = -1
	results = [plants.Plants.NONE] * 5
	for camera in cams:
		i += 1 # increment i here just so we don't forget if we add a continue or something to the loop
		ret, image = camera.read()
		if not ret: #ERROR - skip this camera
			if cams_history[i]:
				log.error('Could not read image from camera %s', camera.id)
			cams_history[i] = False
			continue # skip this camera
		else:
			cams_history[i] = True
		for (cls, confidence, (x, y, w, h)) in darknet_wrapper.detect_cv2(net, meta, image, thresh = THRESHOLD):
			if cls in plants_map.keys():
				results[map_location(camera.id, x, y)] |= plants_map[cls]
	mult.send_process_message(plants)
	gga = nmea.read_data(nmea.GGA)
	record = records.RecordLine(datetime.datetime.now(), gga.longitude, gga.latitude, results)
	print(str(record), file)
	file.flush()

def process():
	# TODO: update this with end-of-row detection and handling
	process_detector()

# TODO: send stop commands to the multivator as well. Everything should be stopped,
# the clutch should be engaged, and the hitch should be raised.
def stop_processor():
	log.info('Shutting down processor...')
	global file
	global net
	global meta
	global cams
	global mult
	global speed_controller
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
		log.debug('Resetting neural network %d', net)
		darknet_wrapper.reset_rnn(net)
		net = 0
		meta = None
	if len(cams) != 0:
		log.debug('Releasing all cameras (%d found)', len(cams))
		for camera in cams:
			camera.release()
		cams = []
	if mult is not None:
		log.debug('Disconnecting from multivator')
		mult.disconnect()
		mult = None
	if speed_controller is not None:
		log.debug('Disconnecting from speed controller')
		speed_controller.disconnect()
		speed_controller = None
	# close the NMEA data files
	nmea.close()
	log.info('Processor successfully shut down - the program will now exit')

def sigint_handler(sig, frame):
	"""Run whenever the process receives a SIGINT signal (either from a user pressing CTRL+C, or from another process).
	This handler prevents an immediate shutdown, but it sets a flag that signals the main loop to cleanup and stop the processor"""
	global sigint_received
	sigint_received = True
	signal.signal(signal.SIGINT, sigint_handler)

def main():
	start_processor()
	try:
		while True:
			process()
			if sigint_received:
				log.info('Received SIGINT - terminating processor.')
				break
	except Exception as exception:
		log.exception(exception)
		raise
	finally:
		stop_processor()

if __name__ == '__main__':
	# Set the process title so we can be found (and signaled) more easily
	os.environ['SPT_NOENV'] = 'True'
	setproctitle.setproctitle('processor.py')
	# register SIGINT handler
	signal.signal(signal.SIGINT, sigint_handler)
	main()


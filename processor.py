#!/usr/bin/python

import os
import datetime
import shutil
import signal
import setproctitle
import cv2

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

def _draw_bbox(img, cls, x, y, z, w, h):
	if cls == 'foxtail':
		color = (0, 0, 255) #red
	elif cls == 'corn':
		color = (0, 255, 0) #green
	elif cls == 'nitro_def_corn':
		color = (0, 255, 246) #yellow
	elif cls == 'cocklebur':
		color = (255, 0, 250) #pink
	elif cls == 'giant_ragweed':
		color = (255, 0, 0) #blue
	else:
		color = (0, 0, 0) #black
	pt1 = ((x-w/2) * len(img[0]), (y-h/2) * len(img))
	pt2 = ((x+w/2) * len(img[0]), (y+h/2) * len(img))
	cv2.rectangle(img, pt1, pt2, color)

plants_map = {
    'foxtail': plants.Plants.Foxtail,
    'cocklebur': plants.Plants.Cocklebur,
	'giant_ragweed': plants.Plants.Ragweed,
    'nitro_def_corn': plants.Plants.Corn,
    'corn': plants.Plants.NONE # ignore non-nitrogen deficient corn
}

def start_processor(ignore_multivator = False, ignore_speed_controller = False):
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
		file = open(CURRENT, 'w+')
		log.debug('Created %s', CURRENT)
	# TODO: it'd be nice to use argparse to avoid hard-coding .cfg, .weights, and .data file paths, except as defaults
	meta = darknet_wrapper.load_meta(b'/home/agbot/Yolo_mark_2/x64/Release/data/obj.data')
	net = darknet_wrapper.load_net(b'/home/agbot/Yolo_mark_2/x64/Release/yolo-obj.cfg', b'/home/agbot/Yolo_mark_2/x64/Release/backup/yolo-obj_final.weights', 0)
	log.debug('Loaded neural network and metadata. net = %d, meta.classes = %d', net, meta.classes)
	cams = cameras.open_cameras('id*')
	cams_history= [True for cam in cams]
	log.debug('Opened cameras - %d found', len(cams))
	if not ignore_multivator:
		mult = multivator.Multivator(initial_mode = multivator.Mode.processing)
		mult.connect()
		log.debug('Connected to multivator')
	if not ignore_speed_controller:
		speed_controller = speed_ctrl.SpeedController()
		speed_controller.connect()
		speed_controller.start()
		log.debug('Connected to speed controller')

def process_detector(ignore_multivator = False, ignore_nmea = False, diagcam_id = None):
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
		draw_bbox = camera.id == diagcam_id
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
			if draw_bbox:
				_draw_bbox(image, cls, x, y, w, h)
				cv2.imshow(diagcam_id, image)
			if cls in plants_map.keys():
				results[map_location(camera.id, x, y)] |= plants_map[cls]
	if not ignore_multivator:
		mult.send_process_message(results)
	if not ignore_nmea:
		gga = nmea.read_data(nmea.GGA)
		record = records.RecordLine(datetime.datetime.now(), gga.longitude, gga.latitude, results)
		print(str(record), file)
		file.flush()

def process(ignore_multivator = False, ignore_speed_controller = False, ignore_nmea = False, diagcam_id = None):
	# TODO: update this with end-of-row detection and handling
	process_detector(ignore_multivator, ignore_nmea, diagcam_id)

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
		
		date = str(datetime.date.today())
		files = [file for file in os.listdir(records.DIR) if file.startswith(date) and file.endswith(records.EXT)]
		# trim the date and extension from the file names and parse the numbers
		numbers = [int(file[len(date) + 1:-len(records.EXT)]) for file in files]
		path = '%s/%s_%d%s'%(records.DIR, date, num, records.EXT)
		path = records.DIR + '/' + date + '_' + str(num) + records.EXT
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
		# switching to diag is probably very bad practice, but it's the quickest way to really stop everything
		mult.set_mode(multivator.Mode.diag)
		mult.diag_set_hitch(multivator.Hitch(mult.get_configuration(multivator.Config.hitch_raised_height)))
		mult.disconnect()
		mult = None
	if speed_controller is not None:
		log.debug('Disconnecting from speed controller')
		speed_controller.stop();
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

def main(ignore_multivator = False, ignore_speed_controller = False, ignore_nmea = False, diagcam_id = None):
	start_processor(ignore_multivator, ignore_speed_controller)
	try:
		while not sigint_received:
			process(ignore_multivator, ignore_speed_controller, ignore_nmea, diagcam_id)
		log.info('Received SIGINT - terminating processor.')
	except Exception as exception:
		log.exception(exception)
		raise
	finally:
		stop_processor()

if __name__ == '__main__':
	import argparse
	# Set the process title so we can be found (and signaled) more easily
	os.environ['SPT_NOENV'] = 'True'
	setproctitle.setproctitle('processor.py')
	
	parser = argparse.ArgumentParser()
	parser.add_argument('-c', '--diagcam-id', default = None)
	parser.add_argument('-n', '--ignore-nmea', action = 'store_true')
	parser.add_argument('-m', '--ignore-multivator', action = 'store_true')
	parser.add_argument('-s', '--ignore-speed-controller', action = 'store_true')
	args = parser.parse_args()
	# register SIGINT handler
	signal.signal(signal.SIGINT, sigint_handler)
	main(args.ignore_multivator, args.ignore_speed_controller, args.ignore_nmea, args.diagcam_id)


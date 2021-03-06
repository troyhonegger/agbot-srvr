#!/usr/bin/python

import cv2
import re
import subprocess
import fnmatch

from lib import loghelper

log = loghelper.get_logger(__file__)

class VideoCamera:
	def __init__(self, stream, id = None, serial = None, port = None):
		""" Initializes a new VideoCamera.
		stream is a cv2.VideoCapture corresponding to a source of video.
		id is the value referred to by the agBot software to identify the camera based on its position
		serial is a string with the serial number of the camera and will usually consist only of hexadecimal digits
		port is the /dev/videoX port number used by the OS to identify the camera
		"""
		self.stream = stream
		self.serial = serial
		self.port = port
		self.id = id
	def release(self):
		if self.stream is not None:
			self.stream.release()
			self.stream = None
	def read(self):
		return self.stream.read()
	def __str__(self):
		return "Camera " + str(self.id)
	def __repr__(self):
		return "Camera {} ({}) at /dev/video{} - stream={}".format(self.id, self.serial, self.port, repr(self.stream))

class CameraException(Exception):
	def __init__(self, message = None):
		self.message = message

def open_cameras(*patterns):
	""" Opens and returns all connected cameras whose ID matches one of the patterns.
	Examples:
		open_cameras() # equivalent to open_cameras('*')
		open_cameras('id0', 'id1')
		open_cameras('id*')
	"""
	if len(patterns) == 0:
		patterns = ('*',)
	
	# read the list of all available cameras from the OS
	ports = []
	proc = subprocess.Popen("ls -l /dev/video*", shell = True, stdout = subprocess.PIPE)
	proc.wait()
	if proc.stdout is not None:
		regex = re.compile(r'.*\/dev\/video(\d+).*')
		for line in proc.stdout.read().split(b'\n'):
			match = regex.match(line.decode('latin-1'))
			if match is not None:
				groups = match.groups()
				if groups is not None and len(groups) > 0:
					ports.append(int(groups[0]))
	ports = sorted(ports)
	log.debug('Loaded cameras from OS. Found %d', len(ports))
	
	cameras = []
	id_map = {
		#'A0C8727F' : 'id0',
        '0F57525F' : 'id0',
		'E517325F' : 'id1',
		'33D0525F' : 'id2',
		'FEB7325F' : 'id3',
		'C622525F' : 'id4',
		'54A8727F' : 'id5'
	}
	# Regular expression to parse the shell output, which should look something like "E: ID_SERIAL_SHORT=256DEC57\n"
	regex = re.compile(r"[^=]*=([A-Fa-f\d]+)[^A-Fa-f\d]*")
	for port in ports:
		# thanks to https://stackoverflow.com/questions/18605701/get-unique-serial-number-of-usb-device-mounted-to-dev-folder for this trick
		proc = subprocess.Popen("/bin/udevadm info --name=/dev/video{} | grep SERIAL_SHORT".format(port), shell = True, stdout = subprocess.PIPE)
		if proc.wait() != 0:
			# either the OS couldn't find camera info, or the info didn't contain SERIAL_SHORT. Either way, skip this camera
			log.warning('Could not read camera info for %s. Skipping this camera.', port)
			continue
		stdout = proc.stdout.read().decode('latin-1')
		match = regex.match(stdout)
		if match is None:
			log.warning('Could not parse serial number for /dev/video%s. Skipping this camera. The line read was \'%s\'', port, stdout)
			continue
		serial = match.groups()[0]
		if not serial in id_map.keys():
			log.warning('Unrecognized serial number %s at /dev/video%s. Skipping this camera.', serial, port)
			continue
		camera_id = id_map[serial]
		if len([1 for pattern in patterns if fnmatch.fnmatch(camera_id, pattern)]) == 0:
			continue # serial number doesn't match any of the patterns - skip it
		
		if len([1 for camera in cameras if camera.id == camera_id]) != 0:
			# TODO: hack here. The ID cameras that we are using each contain two virtual cameras (i.e. /dev/video* ports),
			# and I'm not sure what the second one is supposed to do; only that whatever it is, it doesn't appear to do it.
			# From my testing, I'm pretty sure that the disfunctional virtual camera is always the second to connect. So
			# for now we can get around it by checking the cameras by ID and not overwriting them if they have already
			# been found
			log.warning('Duplicate serial number at /dev/video%s: %s (%s) has already been mapped.', port, serial, camera_id)
			continue
		else:
			log.info('Successfully mapped /dev/video%s to camera %s', port, camera_id)
			cameras.append(VideoCamera(cv2.VideoCapture(port), camera_id, serial, port))
	return sorted(cameras, key=lambda camera: camera.id)

if __name__ == "__main__":
	import argparse
	import os
	import datetime
	import time
	parser = argparse.ArgumentParser(description = "View live feed from the weed camera(s)")
	parser.add_argument('-s', '--store', action = 'store_true', help='Select this option to store the images taken to /home/agbot/images')
	parser.add_argument('--filter', '-f', default='*', \
						help='Specify a filter for which cameras to open - the default is \'*\'', required=False)
	args = parser.parse_args()
	log.debug('Starting camera diagnostics program')
	cameras = open_cameras(args.filter)
	last_store_times = [datetime.datetime(1970,1,1)] * len(cameras)
	try:
		while True:
			for i in range(0, len(cameras)):
				ret, img = cameras[i].read()
				if not ret:
					cameras[i].release()
					cameras.remove(cameras[i])
				else:
					cv2.imshow(str(cameras[i]), img)
					now = datetime.datetime.now()
					if args.store and (now - last_store_times[i]).total_seconds() > 0.1: # min delay between frames is 0.1 sec
						cv2.imwrite('/home/agbot/images/%s-%s.jpg'%(datetime.datetime.now().isoformat(), str(cameras[i])), img)
						last_store_times[i] = now
			if len(cameras) == 0 or (cv2.waitKey(1) & 0xFF == ord('q')):
				break
	except KeyboardInterrupt:
		pass # just quit silently
	finally:
		for camera in cameras:
			camera.release()
		cv2.destroyAllWindows()

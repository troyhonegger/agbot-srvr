#!/usr/bin/python

import cv2
import re
import subprocess

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
		if self.video_capture is not None:
			self.video_capture.release()
			self.video_capture = None
	def read(self):
		return self.stream.read()
	def __str__(self):
		return "Camera " + str(id)
	def __repr__(self):
		return "Camera {} ({}) at /dev/video{} - stream={}".format(self.id, self.serial, self.port, repr(self.stream))

class CameraException(Exception):
	def __init__(self, message = None):
		self.message = message

def open_cameras(n = -1):
	""" Opens the first n connected cameras returned by the OS.
	If n is omitted, all connected cameras will be opened.
	If any camera is connected but cannot be opened, a CameraException is thrown.
	"""
	# read the list of all available cameras from the OS
	ports = []
	proc = subprocess.Popen("ls -l /dev/video*", shell = True, stdout = subprocess.PIPE)
	proc.wait()
	if proc.stdout is not None:
		regex = re.compile(r"/dev/video(\d+)")
		for line in proc.stdout.read().split('\n')[:-1]:
			match = regex.match(line)
			if match is not None:
				groups = match.groups()
				if groups is not None and len(groups) > 1:
					ports.append(int(groups[1]))
	# select the first n such ports (for example, if /dev/video0, /dev/video2, and /dev/video4 were connected and n = 2,
	# select ports 0 and 2)
	ports = sorted(ports)
	if n >= 0:
		ports = ports[:n]
	
	cameras = []
	map = { #TODO: insert serial numbers here
		"A0C8727F" : 0,
		"serial_1" : 1,
		"serial_2" : 2,
		"serial_3" : 3,
		"serial_4" : 4,
		"serial_5" : 5
	}
	# Regular expression to parse the shell output, which should look something like "E: ID_SERIAL_SHORT=256DEC57\n"
	regex = re.compile(r"=([A-Fa-f\d]+)")
	for port in ports:
		# thanks to https://stackoverflow.com/questions/18605701/get-unique-serial-number-of-usb-device-mounted-to-dev-folder for this trick
		proc = subprocess.Popen("/bin/udevadm info --name=/dev/video{} | grep SERIAL_SHORT".format(port), shell = True, stdout = subprocess.PIPE)
		if proc.wait() != 0:
			raise CameraException("Could not find video port /dev/video" + str(port))
		stdout = proc.stdout.read()
		match = regex.match(proc.stdout.read())
		if match is None:
			raise CameraException("Could not read serial number of /dev/video" + str(port))
		serial = match.groups()[1]
		id = map[serial];
		# TODO: hack here. The cameras that we are using each contain two logical cameras (/dev/video* ports),
		# and I'm not sure what the second one is supposed to do; only that it doesn't appear to do it. From my
		# testing, I'm pretty sure that the disfunctional virtual camera is always the second to connect. So
		# for now we can get around it by checking the cameras by ID and not overwriting them if they have already
		# been found
		if len(camera for camera in cameras if camera.id != id) == 0:
			cameras.append(VideoCamera(cv2.VideoCapture(port), id, serial, port))
	return sorted(cameras, key=lambda camera: camera.id)

if __name__ == "__main__":
	import argparse
	parser = argparse.ArgumentParser(description = "View live feed from the weed camera(s)")
	parser.add_argument("--num_cameras", "-n", default=-1, type=int, help="The number of cameras to display")
	args = parser.parse_args()
	cameras = open_cameras(args.num_cameras)
	while True:
		for i in range(0, len(cameras)):
			ret, img = cameras[i].read()
			if not ret:
				cameras[i].release()
				cameras.remove(cameras[i])
			else:
				cv2.imshow(str(cameras[i]), img)
		if len(cameras) == 0:
			break
		if cv2.waitKey(1) & 0xFF == ord('q'):
			for camera in cameras:
				camera.release()
			cv2.destroyAllWindows()
			break
#!/usr/bin/python

import pynmea2

DIR = '/home/agbot/nmea'

# The Trimble supports the following messages:
GGA = 'GGA' # position fix
GSA = 'GSA' # dilution of precision
GST = 'GST' # position error
VTG = 'VTG' # ground speed
ZDA = 'ZDA' # date and time

# We support all of them for completeness, though we will most likely only use GGA

_files = {
	GGA: None,
	GSA: None,
	GST: None,
	VTG: None,
	ZDA: None,
}
	
def read_data(type):
	global _files
	if type not in _files.keys:
		raise ValueError("Unsupported message type: '%s'"%(type))
	if _files[type] is None:
		path = os.path.join(DIR, type + '.txt')
		if not os.path.exists(path):
			raise ValueError('Cannot receive NMEA data because the NMEA listener is not set up. Run %s to start it'%(file))
		_files[type] = open(path, 'r')
	for line in _files[line]:
		if len(line) < 2:
			raise ValueError('No %s data received yet. Make sure the Trimble is working.'%(type))
		data = pynmea2.parse(line, check = True)
		break # only read the first line
	_files[type].seek(0)
	return data

def close():
	for type in _files:
		if _files[type] is not None:
			_files[type].close()
			_files[type] = None

if __name__ == '__main__':
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument('-p', '--port', default = '/dev/ttyS0', required = False, help = 'The serial port on which to listen. The default is /dev/ttyS0')
	args = parser.parse_args()
	from lib import loghelper
	import os
	log = loghelper.get_logger(__file__)
	log.info('Starting up NMEA listener on serial port %s...', args.port)
	try:
		for type in _files:
			_files[type] = open(os.path.join(DIR, type + '.txt'), 'w')
		with open(args.port, 'w') as nmea_port:
			for line in nmea_port:
				try:
					data = pynmea2.parse(line.strip())
					type = data.__class__.__name__
					if type in files.keys:
						# use os.write() to auto-synchronize things for us. This makes all writes (effectively) atomic
						os.write(_files[type].fileno(), (str(data) + '\n').encode('utf-8'))
						# NOTE: if a longer message is followed by a shorter one, this will leave garbage left over after the first line.
						# It shouldn't be a big deal as read_data() only reads the first line, but it's something to keep in mind.
						_files[type].seek(0)
					else:
						log.warning('Received unrecognized message type %s', type)
				except pynmea2.ChecksumError:
					log.error("Invalid NMEA checksum on the following message: '%s'. Skipping this message...", line.strip())
	finally:
		close()
		# delete all the files, so the next person to call read_data hits an error instead of reading stale data
		for type in _files:
			os.remove(os.path.join(DIR, type + '.txt'))

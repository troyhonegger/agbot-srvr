#!/usr/bin/python

import pynmea2
import subprocess
import datetime
import sys
import os
DIR = '/home/agbot/nmea'

# The Trimble supports the following messages:
GGA = 'GGA' # position fix
GSA = 'GSA' # dilution of precision
GST = 'GST' # position error
VTG = 'VTG' # ground speed
ZDA = 'ZDA' # date and time
RMC = 'RMC' # position, velocity, time

# We support all of them for completeness, though we will most likely only use GGA

_files = {
	GGA: None,
	GSA: None,
	GST: None,
	VTG: None,
	ZDA: None,
	RMC: None,
}

def _processor_pid():
	try:
		# runs 'pidof processor.py' in a shell and returns the output (a list
		# of PIDs), or raises a CalledProcessError upon a nonzero exit code.
		return int(subprocess.check_output(['pidof', 'processor.py']).split()[0])
	except subprocess.CalledProcessError:
		return None

# TODO: fine tune through testing
_MAX_EOR_INTERVAL = 2.0 # only remember velocity data from the last two seconds
_MIN_EOR_INTERVAL = 0.5 # if we only have data from the past 0.5 seconds, discard the result as too noisy
_MIN_SPD_KPH = 0.5 # discard any readings with speed less than 0.5 kph (approx 0.45 fps) (prevents noise when the BOT is not moving and the heading is unreliable) 
_TURN_SPEED_CUTOFF = 5.0 # if we average 5 degrees/sec for 2 seconds, assume we're turning
_TURN_DEBOUNCE_TIME = 2.0 # prevent turning/not turning signals from being generated twice inside 2 seconds
_vtg_history = []

def is_turning(vtg_msg):
	now = datetime.datetime.now()
	if vtg_msg.spd_over_grnd_kmph >= _MIN_SPD_KPH:  
		_vtg_history.append((now, vtg_msg))
	# remove queue elements older than _EOR_INTERVAL seconds old
	for date, msg in _vtg_history:
		if (now - date).total_seconds() >= _MAX_EOR_INTERVAL:
			_vtg_history.remove((date,msg))
	# add current element to history
	_vtg_history.append((now, vtg_msg))
	if len(_vtg_history) < 2: return None # insufficient data: we don't know if we're turning
	# compute change in heading (dh) / change in time (dt)
	time0, msg0 = _vtg_history[0]
	time1, msg1 = _vtg_history[-1]
	dt = (time1 - time0).total_seconds()
	if dt < _MIN_EOR_INTERVAL: return None # insufficient data: we don't know if we're turning
	dh = msg1.true_track - msg0.true_track
	abs_dh = min(abs(dh), abs(dh - 360.0))
	return abs_dh/dt > _TURN_SPEED_CUTOFF

def read_data(type):
	global _files
	if type not in _files.keys():
		raise ValueError("Unsupported message type: '%s'"%(type))
	if _files[type] is None:
		path = os.path.join(DIR, type + '.txt')
		if not os.path.exists(path):
			raise ValueError('Cannot receive NMEA data because the NMEA listener is not set up. Run %s to start it'%(__file__))
		_files[type] = open(path, 'r')
	for line in _files[type]:
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
	import os
	import signal
	parser = argparse.ArgumentParser()
	parser.add_argument('-p', '--port', default = '/dev/ttyS0', required = False, help = 'The serial port on which to listen. The default is /dev/ttyS0')
	parser.add_argument('-t', '--ignore-turn', action = 'store_true', help = 'Use this flag to suppress end-of-row detection')
	parser.add_argument('-b', '--baud-rate', default=38400, type=int, choices = [4800, 9600, 19200, 38400, 57600, 115200], help = 'The serial baud rate. The default is 38400.')
	args = parser.parse_args()
	from lib import loghelper
	log = loghelper.get_logger(__file__)
	log.info('Starting up NMEA listener on serial port %s. Baud rate = %d', args.port, args.baud_rate)
	try:
		subprocess.run(['stty', '-F', args.port, str(args.baud_rate)], check=True)
	except subprocess.CalledProcessError as ex:
		log.error('Could not set baud rate - %s', repr(ex))
		raise
	try:
		for type in _files:
			path = os.path.join(DIR, type + '.txt')
			_files[type] = open(path, 'w+')
			# This script will run as root, so this should make sure everyone else permission to read the files we create
			os.chmod(path, 0o644)
		with open(args.port, 'r') as nmea_port:
			if not args.ignore_turn:
				was_turning = None
				turning_last_edge = None
			for line in nmea_port:
				try:
					line = line.strip()
					if len(line) == 0: continue # skip blank lines
					data = pynmea2.parse(line)
					type = data.__class__.__name__
					if type in _files.keys():
						# use os.write() to auto-synchronize things for us. This makes all writes (effectively) atomic
						os.write(_files[type].fileno(), (str(data) + '\n').encode('utf-8'))
						# NOTE: if a longer message is followed by a shorter one, this will leave garbage left over after the first line.
						# It shouldn't be a big deal as read_data() only reads the first line, but it's something to keep in mind.
						_files[type].seek(0)
						if type == VTG and not args.ignore_turn:
							turning = is_turning(data)
							if turning is not None and turning != was_turning and \
									(was_turning is None or (datetime.datetime.now() - turning_last_edge).total_seconds() >= _TURN_DEBOUNCE_TIME):
								was_turning = turning
								turning_last_edge = datetime.datetime.now()
								pid = _processor_pid()
								if pid is not None:
									os.kill(pid, signal.SIGUSR2 if turning else signal.SIGUSR1)
					else:
						log.warning('Received unrecognized message type %s', type)
				except pynmea2.ChecksumError:
					log.error("Invalid NMEA checksum on the following message: '%s'. Skipping this message...", line.strip())
				except pynmea2.ParseError:
					log.error("Could not parse NMEA message: '%s'. Skipping this message...", line.strip())
				except UnicodeDecodeError:
					# this may happen if the baud rate is wrong, or if the Trimble stops unexpectedly, or if the serial
					# transmission begins in the middle of a byte, or possibly other issues. If the baud rate is wrong,
					# this will flood the logs at an alarming rate. Otherwise, the issue can probably be ignored
					log.warning('Received Unicode decode error - check your baud rate if this message appears repeatedly.')
	except KeyboardInterrupt:
		pass # suppress exception, but exit gracefully through finally
	finally:
		log.info('Shutting down NMEA service')
		close()
		# delete all the files, so the next person to call read_data hits an error instead of reading stale data
		for type in _files:
			try:
				os.remove(os.path.join(DIR, type + '.txt'))
			except OSError:
				pass # oh well - we tried. Probably this just means the file didn't exist

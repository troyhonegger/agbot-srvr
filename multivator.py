#!/usr/bin/python

import plants
import socket
import threading
import datetime
import json
import time

DEFAULT_IP = '10.0.0.2'
DEFAULT_PORT = 8010
DEFAULT_TIMEOUT = 0.2
MAX_MESSAGE_SIZE = 63
STOP = 'STOP'
MSG_TIMEOUT = 0.5

class Mode:
	processing = property(lambda self : 'Processing')
	diag = property(lambda self : 'Diagnostics')
	all_modes = property(lambda self: [processing, diag])

class Config:
	precision = property(lambda self : 'Precision')
	keep_alive_timeout = property(lambda self: 'KeepAliveTimeout')
	response_delay = property(lambda self: 'ResponseDelay')
	tiller_accuracy = property(lambda self : 'TillerAccuracy')
	tiller_raise_time = property(lambda self : 'TillerRaiseTime')
	tiller_lower_time = property(lambda self : 'TillerLowerTime')
	tiller_raised_height = property(lambda self: 'TillerRaisedHeight')
	tiller_lowered_height = property(lambda self: 'TillerLoweredHeight')
	hitch_raised_height = property(lambda self: 'HitchRaisedHeight')
	hitch_lowered_height = property(lambda self: 'HitchLoweredHeight')
	all_settings = property(lambda self: \
		[ precision, keep_alive_timeout, response_delay, tiller_accuracy, tiller_raise_time, tiller_lower_time, \
		tiller_raised_height, tiller_lowered_height, hitch_raised_height, hitch_lowered_height ])

class Tiller:
	def __init__(self, id, target_height, actual_height = None, dh = None, until = None):
		self.id = id
		self.actual_height = actual_height
		self.dh = dh
		self.target_height = target_height
		self.until = until

class Sprayer:
	def __init__(self, id, is_on, until = None):
		self.id = id
		self.is_on = is_on
		self.until = until

class Hitch:
	def __init__(self, target_height, actual_height = None, dh = None):
		self.actual_height = actual_height
		self.target_height = target_height
		self.dh = dh

class MultivatorException(Exception):
	def __init__(self, message = None, cause = None):
		self.message = message
		self.cause = cause

class KeepAliveBackgroundWorker(threading.Thread):
	def __init__(self, multivator, err_handler, ip = DEFAULT_IP, port = DEFAULT_PORT):
		Thread.__init__(self)
		self._multivator = multivator
		self._ip = ip
		self._port = port
		self._cancelled = False
		self._event = threading.Event()
		self._err_handler = err_handler
		self.last_error_time = datetime.datetime(1970, 1, 1)
	def _send_keepalive(self):
		"""Send a keep-alive message and return silently if successful, raise a MultivatorException otherwise.
		This should only be called from KeepAliveBackgroundWorker.run()"""
		try:
			msg = b'KeepAlive\n'
			total_sent = 0
			msg_len = len(msg)
			while total_sent < msg_len:
				sent = self.socket.send(msg[total_sent:])
				if sent == 0:
					raise MultivatorException('Could not send message: the server closed the connection.')
				total_sent += sent
			response = ''
			while not response.endswith(b'\n'):
				data = self.socket.recv(MAX_MESSAGE_SIZE)
				if len(data) == 0:
					raise MultivatorException('Could not read message: the server closed the connection')
				response += data
			if len(response.strip()) != 0:
				raise MultivatorException(response.strip())
			return response
		except socket.error as error:
			raise MultivatorException('Protocol error when sending message: see cause for details', error)
	def run(self):
		with socket.socket(socket.AddressFamily.AF_INET, socket.SocketKind.SOCK_STREAM) as s:
			s.settimeout(MSG_TIMEOUT)
			s.connect((self._ip, self._port))
			while True:
				us_diff = (datetime.datetime.now() - self.multivator.last_message_time).microseconds
				if self._cancelled:
					break
				elif us_diff >= 1000000:
					try:
						self._send_keepalive()
						self._multivator.last_message_time = datetime.datetime.now()
					except MultivatorException as error:
						# allow errors to be fired at most 10 times a second
						err_time = datetime.datetime.now()
						if (err_time - self.last_error_time).microseconds > 100000:
							self.last_error_time = err_time
							if self._err_handler is not None:
								self._err_handler(self, error)
						else:
							self._event.wait(0.000001 * (100000 - (err_time - self.last_error_time).microseconds))
							self._event.clear()
				else:
					self._event.wait(0.000001 * (1000000 - us_diff))
					self._event.clear()
	
	def close(self):
		self._cancelled = True
		self._event.set()
	
	def __str__(self):
		return 'KeepAlive Background Worker'

"""Represents a connection to the agBot multivator. Note that this class is NOT thread-safe: to talk to the multivator through
two separate threads, use two separate objects. Further note that currently the multivator will allow a maximum of eight sockets
to connect at the same time - this allows a max of 7 Multivator objects, one of which has a KeepAliveBackgroundWorker.

All API calls will block until the API responds to the message. If an error occurs, they will raise a MultivatorException.
One socket (generally the 'master' socket) should be instantiated with create_keepalive = True. It will periodically ping
the controller to verify it is still connected, and if it does not receive a response, it will call bw_error_handler. If no
keep-alive thread is created, the API may sporadically engage the e-stop if it goes long enough without receiving a message.
"""
class Multivator:
	def __init__(self, create_keepalive = True, bw_error_handler = None):
		"""Initializes a multivator instance that, once connected, will be able to talk to the multivator."""
		self.socket = None
		self.create_keepalive = create_keepalive
		self.bw_error_handler = bw_error_handler
	def __enter__(self):
		"""Equivalent to connect() - implemented to support the with operator"""
		self.connect(create_keepalive = self.create_keepalive, bw_error_handler = self.bw_error_handler)
	def __exit__(self, *args):
		"""Equivalent to disconnect() - implemented to support the with operator"""
		self.disconnect()
	
	def _send_msg(self, msg, assertEmpty = False):
		"""Send a message and read the response. Raise a MultivatorException if the message transmission fails"""
		try:
			if self.socket is None:
				raise MultivatorException('Not connected')
			msg = msg + b'\n'
			total_sent = 0
			msg_len = len(msg)
			while total_sent < msg_len:
				sent = self.socket.send(msg[total_sent:])
				if sent == 0:
					raise MultivatorException('Server closed connection unexpectedly - could not send message')
				total_sent += sent
			response = ''
			while not response.endswith(b'\n'):
				data = self.socket.recv(MAX_MESSAGE_SIZE)
				if len(data) == 0:
					raise MultivatorException('Server closed connection unexpectedly - the response could not be read completely.')
				response += data
			self.last_message_time = datetime.datetime.now()
			response = response.strip()
			if assertEmpty and len(response) != 0:
				raise MultivatorException(response)
			return response
		except socket.error as error:
			raise MultivatorException('Protocol error when sending message - see cause for details', error)
	
	def connect(self, ip = DEFAULT_IP, port = DEFAULT_PORT, mode = None, create_keepalive = True, bw_error_handler = None):
		"""Connects to the multivator listening at the specified IP address and port number.
		If a mode is specified (one of Mode.diag or Mode.processing), this also sets the multivator's mode"""
		self.disconnect()
		self.socket = socket.socket(socket.AddressFamily.AF_INET, socket.SocketKind.SOCK_STREAM)
		self.socket.settimeout(MSG_TIMEOUT)
		self.socket.connect((ip,port))
		self.last_message_time = datetime.datetime.now()
		if create_keepalive:
			self._keep_alive_worker = KeepAliveBackgroundWorker(self, bw_error_handler, ip, port)
			self._keep_alive_worker.start()
		if mode is not None:
			self.set_mode(mode)
	def disconnect(self):
		if self._keep_alive_worker is not Note:
			self._keep_alive_worker.close()
			self._keep_alive_worker = None
		if self.socket is not None:
			self.socket.close()
			self.socket = None
	
	def set_mode(self, mode):
		if mode != Mode.processing and mode != Mode.diag:
			raise MultivatorException('Invalid mode ' + repr(mode))
		self._send_msg(b'SetMode %s'%(mode), True)
	def get_mode(self):
		response = self._send_msg(b'GetState Mode')
		if response in Mode.all_modes:
			return response
		else:
			raise MultivatorException(response)
	
	def get_tiller(self, tiller_id):
		try:
			response = self._send_msg(b'GetState Tiller[%d]'%(tiller_id)).strip()
			json_data = json.loads(response)
			until = json_data['until'] if 'until' in json_data.keys() else None
			return Tiller(tiller_id, json_data['target'], json_data['height'], json_data['dh'], until)
		except JsonDecodeError:
			raise MultivatorException(response)
		except KeyError:
			raise MultivatorException('Could not parse response: %s'%(response))
	def get_sprayer(self, sprayer_id):
		response = _send_msg('GetState Sprayer[%d]'%(sprayer_id))
		# matches something like "ON 1200" or "OFF"
		match = re.match('(\w+)(?: (\d+))?', response)
		if match is not None:
			groups = match.groups()
			return Sprayer(sprayer_id, groups[0], groups[1])
		else:
			raise MultivatorException(response)
	def get_hitch(self):
		try:
			response = self._send_msg(b'GetState Hitch')
			json_data = json.loads(response)
			until = json_data['until'] if 'until' in json_data.keys() else None
			return Hitch(json_data['target'], json_data['height'], json_data['dh'], until)
		except JsonDecodeError:
			raise MultivatorException(response)
		except KeyError:
			raise MultivatorException('Could not parse response: %s'%(response))
	
	def get_configuration(self, setting):
		response = self._send_msg(b'GetState Configuration[%s]\n'%(setting))
		try:
			return int(response)
		except ValueError:
			raise MultivatorException(response)
	def set_configuration(self, setting, value):
		self._send_msg(b'SetConfig %s=%s\n'%(setting, str(value)), True)
	
	def diag_set_sprayer(self, sprayer):
		self._send_msg('DiagSet Sprayer[%d]=%s'%(sprayer.id, 'ON' if sprayer.is_on else 'OFF'), True)
	def diag_set_tiller(self, tiller):
		self._send_msg('DiagSet Tiller[%d]=%s'%(tiller.id, str(tiller.target_height)), True)
	def diag_set_hitch(self, hitch):
		self._send_msg('DiagSet Hitch=%s'%(str(hitch.target_height)), True)
	
	def estop(self):
		self._send_msg('Estop', True)
	
	def send_process_message(self, plants):
		"""Sends a list of PlantInfo objects to the multivator. These PlantInfo objects should be ordered by their
		physical position, left to right - the first entry corresponds to the left tiller, the next corresponds to
		the left row, then the middle row, and so on."""
		message = 'Process #'
		for plant in plants:
			message += hex(plant.plants)[2:]
		self._send_msg(message, True)

if __name__ == '__main__':
	import argparse
	import sys
	parser = ArgumentParser(description = 'Run diagnostics commands on the multivator')
	group = parser.add_mutually_exclusive_group()
	group.add_argument('--script', '-s', action='store_true', help='start the program in script mode')
	group.add_argument('--gui', '-g', action='store_false', help='start this program as a GUI')
	if parser.parse_args().script:
		def err_handler(src, error):
			sys.stderr.write('%s: %s\n'%(str(src), error.message))
		with multivator as Multivator(create_keepalive = True, bw_error_handler = err_handler):
			while True:
				try:
					response = multivator._send_msg(line.encode('utf-8'))
					print(response)
				except MultivatorException as error:
					err_handler('Multivator', error)
				except EOFError:
					break
	else: #GUI mode
		# TODO: implement GUI using tkinter. GUI should support the following functionality:
		#	1. visible log of all messages (except keep-alives, which happen automatically)
		# 	2. send raw message (at your own risk)
		# 	3. drag slider for tillers and hitch
		# 	4. toggle button for each sprayer
		# 	5. config settings drop down with numeric input box and get/set buttons
		# 	6. big red "Estop" button
		# In the interest of minimalism, the following calls are NOT supported except through the send raw message box:
		# 	-GetState [Tiller/Sprayer/Hitch] - use raw message if they are visibly not responding use raw message
		# 	-Process commands - shouldn't be necessary for diagnostics; if so use raw message box
		# 	-SetMode commands - useless without process commands. Just call SetMode Diagnostics on startup
		sys.stderr.write('Sorry - multivator diagnostics GUI is not yet implemented. You\'ll have to use script mode...\n')

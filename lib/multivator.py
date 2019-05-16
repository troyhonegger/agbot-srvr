#!/usr/bin/python

import socket
import json
import time
import re

DEFAULT_IP = '192.168.4.2'
DEFAULT_PORT = 8010
DEFAULT_TIMEOUT = 0.2
MAX_MESSAGE_SIZE = 63
MSG_TIMEOUT = 0.5

class Mode:
	processing = 'Processing'
	diag = 'Diagnostics'
	all_modes = (processing, diag)

class Config:
	precision = 'Precision'
	keep_alive_timeout = 'KeepAliveTimeout'
	response_delay = 'ResponseDelay'
	tiller_accuracy = 'TillerAccuracy'
	tiller_raise_time = 'TillerRaiseTime'
	tiller_lower_time = 'TillerLowerTime'
	tiller_raised_height = 'TillerRaisedHeight'
	tiller_lowered_height = 'TillerLoweredHeight'
	hitch_raised_height = 'HitchRaisedHeight'
	hitch_lowered_height = 'HitchLoweredHeight'
	hitch_accuracy = 'HitchAccuracy'
	all_settings = ( precision, keep_alive_timeout, response_delay, tiller_accuracy, tiller_raise_time, \
		tiller_lower_time, tiller_raised_height, tiller_lowered_height, hitch_raised_height, hitch_lowered_height, hitch_accuracy )

class Tiller:
	def __init__(self, id, target_height, actual_height = None, dh = None, until = None):
		self.id = id
		self.actual_height = actual_height
		self.dh = dh
		self.target_height = target_height
		self.until = until
	def __repr__(self):
		return 'Tiller(id=%d, target_height=%s, actual_height=%s, dh=%s, until=%s)'%(self.id, \
			str(self.target_height), str(self.actual_height), str(self.dh), str(self.until))

class Sprayer:
	def __init__(self, id, is_on, until = None):
		self.id = id
		self.is_on = is_on
		self.until = until
	def __repr__(self):
		return 'Sprayer(id=%d, is_on=%s, until=%s)'%(self.id, str(self.is_on), str(self.until))

class Hitch:
	def __init__(self, target_height, actual_height = None, dh = None, until = None):
		self.actual_height = actual_height
		self.target_height = target_height
		self.until = until
		self.dh = dh
	def __repr__(self):
		return 'Hitch(target_height=%s, actual_height=%s, dh=%s, until=%s)'%(str(self.target_height), \
			str(self.actual_height), str(self.dh), str(self.until))

class MultivatorException(Exception):
	def __init__(self, message = None, cause = None):
		self.message = message
		self.cause = cause
	def __str__(self):
		return str(self.message)
	def __repr__(self):
		return 'MultivatorException(message=%s, cause=%s)'%(repr(self.message), repr(self.cause))

"""
Represents a connection to the agBot multivator. Note that this class is NOT thread-safe: to talk to the multivator through
two separate threads, use two separate objects. Further note that currently the multivator will allow a maximum of eight sockets
to connect at the same time, so at most 8 instances of this class can be simultaneously connected across the entire system.
All API calls will block until the API responds to the message. If an error occurs, they will raise a MultivatorException.
"""
class Multivator:
	def __init__(self, ip = DEFAULT_IP, port = DEFAULT_PORT, create_socket = None, initial_mode = None):
		"""Initializes a multivator instance that, once connected, will be able to talk to the multivator.
		create_socket is a lambda for dependency injection. If not None, the instance will call it to
		obtain a TCP socket."""
		self.ip = ip
		self.port = port
		self.socket = None
		self.create_socket = create_socket if create_socket is not None else lambda self: socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.initial_mode = initial_mode
	def __enter__(self):
		"""Equivalent to connect() - implemented to support the with operator"""
		self.connect()
	def __exit__(self, *args):
		"""Equivalent to disconnect() - implemented to support the with operator"""
		self.disconnect()
	
	def _send_msg(self, msg, assert_empty = False):
		"""Send a message and read the response. Raise a MultivatorException if the message transmission fails"""
		try:
			if self.socket is None:
				raise MultivatorException('Not connected')
			if isinstance(msg, str): msg = msg.encode('utf-8')
			msg = msg + b'\n'
			total_sent = 0
			msg_len = len(msg)
			while total_sent < msg_len:
				sent = self.socket.send(msg[total_sent:])
				if sent == 0:
					raise MultivatorException('Server closed connection unexpectedly - could not send message')
				total_sent += sent
			response = b''
			while not response.endswith(b'\n'):
				data = self.socket.recv(MAX_MESSAGE_SIZE)
				if len(data) == 0:
					raise MultivatorException('Server closed connection unexpectedly - the response could not be read completely.')
				response += data
			response = response.strip()
			if assert_empty and len(response) != 0:
				raise MultivatorException(response)
			return response.decode('latin-1')
		except socket.error as error:
			raise MultivatorException('Protocol error when sending message - see cause for details', error)
	
	def isconnected(self):
		return self.socket is not None
	def connect(self):
		"""Connects to the multivator listening at the specified IP address and port number."""
		self.disconnect()
		try:
			self.socket = self.create_socket(self);
			self.socket.settimeout(MSG_TIMEOUT)
			self.socket.connect((self.ip,self.port))
		except OSError as ex:
			raise MultivatorException('Could not connect to multivator: %s'%(str(ex)), ex)
		if self.initial_mode is not None:
			self.set_mode(self.initial_mode)
	def disconnect(self):
		if self.isconnected():
			self.socket.close()
			self.socket = None
	
	def __str__(self):
		return 'Multivator(ip = %s, port = %d)'%(self.ip, self.port)
	
	def set_mode(self, mode):
		if mode != Mode.processing and mode != Mode.diag:
			raise MultivatorException('Invalid mode ' + repr(mode))
		self._send_msg('SetMode %s'%(mode), True)
	def get_mode(self):
		response = self._send_msg('GetState Mode')
		if response in Mode.all_modes or response == 'Unset':
			return response
		else:
			raise MultivatorException(response)
	
	def get_tiller(self, tiller_id):
		try:
			response = self._send_msg('GetState Tiller[%d]'%(tiller_id)).strip()
			json_data = json.loads(response)
			until = json_data['until'] if 'until' in json_data.keys() else None
			return Tiller(tiller_id, json_data['target'], json_data['height'], json_data['dh'], until)
		except ValueError:
			raise MultivatorException(response)
		#I think this was right on Python 3.7, but now it doesn't work on 2.7
		#except json.JsonDecodeError:
		#	raise MultivatorException(response)
		except KeyError:
			raise MultivatorException('Could not parse response: %s'%(response))
	def get_sprayer(self, sprayer_id):
		response = self._send_msg('GetState Sprayer[%d]'%(sprayer_id))
		match = re.match('(ON|OFF)(?: (\d+))?', response)
		if match is not None:
			groups = match.groups()
			time = int(groups[1]) if groups[1] is not None else None
			return Sprayer(sprayer_id, groups[0], time)
		else:
			raise MultivatorException(response)
	def get_hitch(self):
		try:
			response = self._send_msg('GetState Hitch')
			json_data = json.loads(response)
			until = json_data['until'] if 'until' in json_data.keys() else None
			return Hitch(json_data['target'], json_data['height'], json_data['dh'], until)
		except ValueError:
			raise MultivatorException(response)
		#I think this was right on Python 3.7, but now it doesn't work on 2.7
		#except json.JsonDecodeError:
		#	raise MultivatorException(response)
		except KeyError:
			raise MultivatorException('Could not parse response: %s'%(response))
	
	def get_configuration(self, setting):
		response = self._send_msg('GetState Configuration[%s]'%(setting))
		try:
			return int(response)
		except ValueError:
			raise MultivatorException(response)
	def set_configuration(self, setting, value):
		self._send_msg('SetConfig %s=%s'%(setting, str(value)), True)
	
	def diag_set_sprayer(self, sprayer):
		self._send_msg('DiagSet Sprayer[%x]=%s'%(1 << sprayer.id, 'ON' if sprayer.is_on else 'OFF'), True)
	def diag_set_tiller(self, tiller):
		self._send_msg('DiagSet Tiller[%x]=%s'%(1 << tiller.id, str(tiller.target_height)), True)
	def diag_set_hitch(self, hitch):
		self._send_msg('DiagSet Hitch=%s'%(str(hitch.target_height)), True)
	
	def estop(self):
		self._send_msg('Estop', True)
	
	def keep_alive(self):
		self._send_msg('KeepAlive', True)
	
	def send_process_message(self, plants):
		"""Sends a list of Plants objects to the multivator. These Plants objects should be ordered by their
		physical position, left to right - the first entry corresponds to the left tiller, the next corresponds to
		the left row, then the middle row, and so on."""
		message = 'Process #'
		for entry in plants:
			message += hex(entry)[2:]
		self._send_msg(message, True)
	def process_raise_hitch(self):
		self._send_msg('ProcessRaiseHitch', True)
	def process_lower_hitch(self):
		self._send_msg('ProcessLowerHitch', True)

if __name__ == '__main__':
	import sys
	with Multivator() as multivator:
		while True:
			try:
				line = input()
				response = multivator._send_msg(line.encode('utf-8'))
				print(response)
			except MultivatorException as error:
				sys.stderr.write(error.message)
			except EOFError:
				break

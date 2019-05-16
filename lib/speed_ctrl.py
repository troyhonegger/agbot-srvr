import socket

DEFAULT_IP = '192.168.4.3'
DEFAULT_PORT = 8010
DEFAULT_TIMEOUT = 0.2
MAX_MESSAGE_SIZE = 63
MSG_TIMEOUT = 0.5

class SpeedControlException(Exception):
	def __init__(self, message = None, cause = None):
		self.message = message
		self.cause = cause
	def __str__(self):
		return str(self.message)
	def __repr__(self):
		return 'SpeedControlException(message=%s, cause=%s)'%(repr(self.message), repr(self.cause))

class SpeedController:
	def __init__(self, ip = DEFAULT_IP, port = DEFAULT_PORT):
		"""Initializes a SpeedController instance that, once connected, will be able to connect to the speed controller."""
		self.socket = None
		self.ip = ip
		self.port = port
	def __enter__(self):
		"""Equivalent to connect() - implemented to support the with operator"""
		self.connect()
	def __exit__(self, *args):
		"""Equivalent to disconnect() - implemented to support the with operator"""
		self.disconnect()
	
	def _send_msg(self, msg, assert_empty = False):
		"""Send a message and read the response. Raise a SpeedControlException if the message transmission fails"""
		try:
			if self.socket is None:
				raise SpeedControlException('Not connected')
			if isinstance(msg, str): msg = msg.encode('utf-8')
			msg = msg + b'\n'
			total_sent = 0
			msg_len = len(msg)
			while total_sent < msg_len:
				sent = self.socket.send(msg[total_sent:])
				if sent == 0:
					raise SpeedControlException('Server closed connection unexpectedly - could not send message')
				total_sent += sent
			response = b''
			while not response.endswith(b'\n'):
				data = self.socket.recv(MAX_MESSAGE_SIZE)
				if len(data) == 0:
					raise SpeedControlException('Server closed connection unexpectedly - the response could not be read completely.')
				response += data
			response = response.strip()
			if assert_empty and len(response) != 0:
				raise SpeedControlException(response)
			return response.decode('latin-1')
		except socket.error as error:
			raise SpeedControlException('Protocol error when sending message - see cause for details', error)
	
	def isconnected(self):
		return self.socket is not None
	def connect(self):
		"""Connects to the speed controller listening at the specified IP address and port number."""
		self.disconnect()
		try:
			self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.socket.settimeout(MSG_TIMEOUT)
			self.socket.connect((self.ip, self.port))
		except OSError as ex:
			raise SpeedControlException('Could not connect to speed controller: %s'%(str(ex)), ex)
	def disconnect(self):
		if self.isconnected():
			self.socket.close()
			self.socket = None
	
	def __str__(self):
		return 'SpeedController(ip = %s, port = %d'%(self.ip, self.port)
	
	def keep_alive(self):
		self._send_msg('KeepAlive', True)
	def estop(self):
		self._send_msg('Estop', True)
	def start(self):
		self._send_msg('Start', True)
	def stop(self):
		self._send_msg('Stop', True)
	def enter_row(self):
		self._send_msg('EnterRow', True)
	def exit_row(self):
		self._send_msg('ExitRow', True)

if __name__ == '__main__':
	import sys
	with SpeedController() as controller:
		while True:
			try:
				line = input()
				response = controller._send_msg(line)
				print(response)
			except SpeedControlException as error:
				sys.stderr.write(error.message)
			except EOFError:
				break
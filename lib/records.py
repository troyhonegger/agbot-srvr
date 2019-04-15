import os
import sys
import cv2
import plants

def _parse_record_line(self, line):
	pass #TODO

class RecordLine:
	def __init__(timestamp, longitude, latitude, plants):
		self.timestamp = timestamp
		self.longitude = longitude
		self.latitude = latitude
		self.plants = plants

class Record:
	def __init__(self):
		self.lines = []
	def __len__(self):
		return len(self.lines)
	def write_to(self, file):
		for line in self.lines:
			file.write(line)
			file.write('\n')
		file.flush()
	def read_from(self, file):
		while True:
			line = file.readline()
			self.lines.append(_parse_record_line(line.trim()))
			if not line.endswith('\n'):
				break
		return self
	def render_image(self):
		pass #TODO
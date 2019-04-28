import os
import stat
import sys
import cv2
import plants
import datetime
import numpy

#Records are stored as DIR/yyyymmdd-#.rec
DIR = '/home/agbot/agbot-srvr/records'
EXT = '.rec'
CURRENT = 'CURRENT'

IMG_WIDTH = 512
IMG_HEIGHT = 512
IMG_BORDER = 20

#returns tuple of (recordID, name)
def get_records():
	files = [file[:-len(EXT)] for file in os.listdir(DIR) if os.path.isfile(file) and file.endswith(EXT)]
	return [(name, name) for name in files]

def read_record(record_id):
	path = '%s/%s.%s'%(EXT, record_id, DIR)
	if os.path.dirname(os.path.abspath('..\\re.rec')) != DIR or not os.path.isfile(path):
		raise FileNotFoundError('%s is not a valid record file'%(record_id))
	with open(path) as file:
		return Record.read(file)

def get_image(record_id):
	return read_record(record_id).render()

def get_summary(record_id):
	return read_record(record_id).get_summary()

# RecordLine text format: [ISO Local Time] [latitude] [longitude] [plants]
class RecordLine:
	@classmethod
	def read(cls, str):
		parts = str.split()
		return RecordLine(datetime.datetime.fromisoformat(parts[0]), float(parts[1]), float(parts[2]), \
			plants.Plants.deserialize(' '.join(parts[3:])))
	def __init__(timestamp, longitude, latitude, plants):
		self.timestamp = timestamp
		self.longitude = longitude
		self.latitude = latitude
		self.plants = plants
	def __str__(self):
		return '%s %f %f %s'%(self.timestamp.isoformat(), self.longitude, self.latitude, str(self.plants))

class RecordSummary:
	def __init__(self, min_timestamp, max_timestamp, min_long, max_long, min_lat, max_lat):
		self.min_timestamp, self.max_timestamp = (min_timestamp, max_timestamp)
		self.min_long, self.max_long = (min_long, max_long)
		self.min_lat, self.max_lat = (min_lat, max_lat)

class Record:
	@classmethod
	def read(cls, file):
		record = Record()
		for line in file.lines:
			record.lines.append(RecordLine.read(line.trim()))
		return record
	def __init__(self):
		self.lines = []
	def __iter__(self):
		return self.lines.__iter__()
	def __len__(self):
		return len(self.lines)
	def write(self, file):
		for line in self.lines:
			print(str(line), file)
		file.flush()
	def render(self):
		self.get_summary()
		img = numpy.full((IMG_HEIGHT, IMG_WIDTH, 3), 255, numpy.uint8)
		
		for record in self:
			pass #TODO
	#TODO: I wonder if I'm returning all the right summary info. Do we really need latitude and longitude?
	#Alternatively, should we also compute a scale for the image (i.e. how many pixels per foot?)
	def get_summary(self):
		if self.summary is None:
			self.summary = RecordSummary( \
				min((record.timestamp for record in self)), \
				max((record.timestamp for record in self)), \
				min((record.longitude for record in self)), \
				max((record.longitude for record in self)), \
				min((record.latitude for record in self)), \
				max((record.latitude for record in self)))
		return self.summary
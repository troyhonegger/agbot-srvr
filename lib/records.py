import os
import stat
import sys
import cv2
import plants
import datetime
import numpy
import math

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

EARTH_RADIUS = 20_902_464 # feet
def _to_cartesian(longitude, latitude):
	theta = math.radians(latitude)
	phi = math.radians(90 - longitude)
	xy_radius = math.sin(phi) * EARTH_RADIUS
	return (xy_radius * math.cos(theta), xy_radius * math.sin(theta), EARTH_RADIUS * math.cos(phi))

def _vec(*components):
	return numpy.array(components, numpy.float64)
def _mag(vector):
	return math.sqrt(sum([x*x for x in vector]))
def _hat(vector):
	return vector / _mag(vector)
def _crossprod(v1, v2):
	return _vec(v1[1]*v2[2] - v1[2]*v2[1], v1[2]*v2[0] - v1[0]*v2[2], v1[0]*v2[1] - v1[1]*v2[0])
def _dotprod(v1, v2):
	return sum([x*y for x,y in zip(v1, v2)])
def _coordinate_vectors(x0, y0, z0):
	"""Returns two vectors - one pointing North in three dimensions (relative to the current position)
	and one pointing East in three dimensions (relative to the current position)"""
	# The equation of the tangent plane is x0*x + y0*y + z0*z = x0^2 + y0^2 + z0^2
	#	this can be derived from the fact that every vector on the plane is perpendicular to (x0, y0, z0)
	# Therefore, the gradient of the plane is (-x0/z0, -y0/z0).
	# If we traverse in the x- and y-directions along the gradient and compute the change in z, the vector
	# (dx, dy, dz) will point north.
	
	# As we get very close to the equator, the magnitude of the gradient will become infinite. So I'll stick this
	# in here just in case. But unless we're literally within ~1/4 mile of the equator, it should never run.
	if abs(z0 - 0) < 1000:
		north = _vec(0, 0, 1.0)
	# Otherwise, we can compute the gradient normally
	else:
		dx, dy = -x0/z0, -y0/z0
		# distortions will also start to occur very close to the north pole, where the gradient approaches zero and
		# "north" becomes less meaningful. Not that it matters, of course, for our purposes
		north = _hat(_vec(dx * dx + dy * dy, dx, dy))
	# This is perpendicular to both north and the normal vector, so it must point either east or west. Right-hand
	# rule experimentation shows this is the way that points east.
	east = _hat(_crossprod(north, _vec(x0, y0, z0)))
	return north, east

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

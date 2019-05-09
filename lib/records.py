import os
import stat
import sys
import cv2
import datetime
import numpy
import math

from lib import plants

#Records are stored as DIR/yyyymmdd-#.rec
DIR = '/home/agbot/agbot-srvr/records'
EXT = '.rec'
CURRENT = 'CURRENT'

MAX_IMG_WIDTH = 1500
MAX_IMG_HEIGHT = 700

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
EARTH_RADIUS = 20_902_464 # feet
def _to_cartesian(longitude, latitude):
	theta = math.radians(latitude)
	phi = math.radians(90 - longitude)
	xy_radius = math.sin(phi) * EARTH_RADIUS
	return _vec([xy_radius * math.cos(theta), xy_radius * math.sin(theta), EARTH_RADIUS * math.cos(phi)])
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
# [plants] is a comma-delimited list of Plants objects (which are themselves pipe-delimited).
# Each entry in the list corresponds to a row, and the rows are listed left to right.
class RecordLine:
	@classmethod
	def read(cls, string):
		parts = string.split()
		rows = ' '.join(parts[3:]).split(',')
		return RecordLine(datetime.datetime.fromisoformat(parts[0]), float(parts[1]), float(parts[2]), \
			[plants.Plants.deserialize(row.strip()) for row in rows])
	def __init__(self, timestamp, longitude, latitude, rows):
		self.timestamp = timestamp
		self.longitude = longitude
		self.latitude = latitude
		self.rowdata = rows
	def __str__(self):
		return '%s %f %f %s'%(self.timestamp.isoformat(), self.longitude, self.latitude, ', '.join([str(row) for row in self.rows]))

class RecordSummary:
	def __init__(self, start_time, end_time, latitude, longitude):
		self.start_time = start_time
		self.end_time = end_time
		self.longitude = longitude
		self.latitude = latitude

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
		center = _to_cartesian(self.summary.longitude, self.summary.latitude)
		north_vec, east_vec = _coordinate_vectors(center[0], center[1], center[2])
		rel_posns = numpy.array(_to_cartesian(record.longitude, record.latitude) - center for record in self)
		rel_north = numpy.array(_dotprod(north_vec, rel_posn) for rel_posn in rel_posns)
		rel_east = numpy.array(_dotprod(east_vec, rel_posn) for rel_posn in rel_posns)
		furthest_east = numpy.max(rel_east)
		furthest_north = numpy.max(rel_north)
		furthest_west = numpy.min(rel_east)
		furthest_south = numpy.min(rel_north)
		width_ft, height_ft = furthest_east - furthest_west, furthest_north - furthest_south
		# compute scale (in pixels per foot)
		if width_ft == 0 and height_ft == 0:
			scale = 0 # TODO
			raise NotImplementedError()
		elif width_ft == 0:
			scale = MAX_IMG_HEIGHT / height_ft
		elif height_ft == 0:
			scale = MAX_IMG_WIDTH / width_ft
		else:
			scale = min(MAX_IMG_WIDTH / width_ft, MAX_IMG_HEIGHT / height_ft)
		width_px, height_px = math.floor(width_ft * scale), math.floor(height_ft * scale)
		img = numpy.full((height_px, width_px, 3), 255, numpy.uint8)
		for record in self:
			pass # TODO
	def get_summary(self):
		if self.summary is None:
			if len(self) == 0:
				raise ValueError('Cannot compute summary of an empty record')
			avg_latitude = sum(record.latitude for record in self) / len(self) if len(self) != 0 else 0.0
			longitudes1 = numpy.array((record.longitude for record in self), numpy.float64)
			longitudes2 = numpy.array((record.longitude if record.longitude < 180.0 else record.longitude - 360.0 \
									for record in self), numpy.float64)
			avg_longitude = numpy.average(longitudes2) \
							if numpy.std(longitudes2) < numpy.std(longitudes1) \
							else numpy.average(longitudes1)
			self.summary = RecordSummary( \
				min(record.timestamp for record in self), \
				max(record.timestamp for record in self), \
				avg_latitude, avg_longitude)
		return self.summary

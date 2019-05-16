import os
import cv2
import datetime
import numpy
import math

from lib import plants

#Records are stored as DIR/yyyymmdd-#.rec
DIR = '/home/agbot/agbot-srvr/records'
EXT = '.rec'
CURRENT = 'CURRENT'

MAX_IMG_WIDTH = 700
MAX_IMG_HEIGHT = 500
PLANT_RADIUS_FT = 2 / 12 # TODO: adjust as needed. This is 4 inches diameter for one plant
# distances from each row to the center of the BOT.
ROW_DIST = [-26/12, -16/12, 0.0, 16/12, 26/12]

def get_name(record_id):
	# for now, names and record IDs are synonymous
	return record_id

def get_records():
	files = [file[:-len(EXT)] for file in os.listdir(DIR) if os.path.isfile(os.path.join(DIR, file)) and file.endswith(EXT)]
	return [(record_id, get_name(record_id)) for record_id in files]

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
	theta = math.radians(longitude)
	phi = math.radians(90 - latitude)
	xy_radius = math.sin(phi) * EARTH_RADIUS
	return _vec(xy_radius * math.cos(theta), xy_radius * math.sin(theta), EARTH_RADIUS * math.cos(phi))
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
		north = _hat(_vec(dx, dy, dx * dx + dy * dy))
	# This is perpendicular to both north and the normal vector, so it must point either east or west. Right-hand
	# rule experimentation shows this is the way that points east.
	east = _hat(_crossprod(north, _vec(x0, y0, z0)))
	return north, east

# RecordLine text format: [ISO Local Time] [latitude] [longitude] [plants]
# [plants] is a comma-delimited list of Plants objects (which are themselves pipe-delimited).
# Each entry in the list corresponds to a row, and the rows are listed left to right.
def _img_compute_scale(width_ft, height_ft):
	if width_ft == 0 and height_ft == 0:
		raise ValueError('Cannot compute scale: area given is infinitesimal')
	elif width_ft == 0:
		return MAX_IMG_HEIGHT / height_ft
	elif height_ft == 0:
		return MAX_IMG_WIDTH / width_ft
	else:
		return min(MAX_IMG_WIDTH / width_ft, MAX_IMG_HEIGHT / height_ft)
def get_color(plant):
	if plants.Plants.Foxtail in plant:
		return (0, 0, 255) #red
	elif plants.Plants.Corn in plant:
		return (0, 255, 0) #green
	elif plants.Plants.Cocklebur in plant:
		return (0, 255, 246) #yellow
	elif plants.Plants.Ragweed in plant:
		return (255, 0, 0) #blue
def _draw_record_line(img, record_line, posn_px, normal_ft, scale, plant_radius_px):
	for row_offs, row in zip(ROW_DIST, record_line.rowdata):
		center = posn_px + scale * row_offs * normal_ft # find the center of any weeds found in that row
		for plant in row:
			# debug only
			#print('drawing circle at (%d,%d), radius %d, color (%d %d %d)'\
			#	%(int(center[0]), int(center[1]), plant_radius_px, get_color(plant)[0], get_color(plant)[1], get_color(plant)[2]))
			cv2.circle(img, (int(center[0]), int(center[1])), plant_radius_px, get_color(plant), -1)

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
	def __repr__(self):
		return 'RecordLine(timestamp=%s; longitude=%f; latitude=%f; rows=%s)'% \
			(repr(self.timestamp), self.longitude, self.latitude, ', '.join([str(row) for row in self.rowdata]))
	def __str__(self):
		return '%s %f %f %s'%(self.timestamp.isoformat(), self.longitude, self.latitude, ', '.join([str(row) for row in self.rowdata]))

class RecordSummary:
	def __init__(self, record_id, record_name, start_time, end_time, latitude, longitude):
		self.record_id = record_id
		self.record_name = record_name
		self.start_time = start_time
		self.end_time = end_time
		self.longitude = longitude
		self.latitude = latitude
	def __repr__(self):
		return 'RecordSummary(record_id=%s, record_name=%s, start_time=%s, end_time=%s, longitude=%f, latitude=%f)'%\
			(self.record_id, self.record_name, str(self.start_time), str(self.end_time), self.longitude, self.latitude)
	def __str__(self):
		return "Record '%s': started %s, long/lat = (%f, %f)"%(self.record_name, str(self.start_time), self.longitude, self.latitude)

class Record:
	@classmethod
	def read(cls, record_id):
		path = record_id + EXT
		if not path in os.listdir(DIR):
			raise FileNotFoundError('%s is not a valid record file'%(record_id))
		record = Record(record_id, get_name(record_id))
		with open(os.path.join(DIR, path)) as file:
			for line in file:
				record.lines.append(RecordLine.read(line.strip()))
		return record
	def __init__(self, record_id, name):
		self.record_id = record_id
		self.name = name
		self.summary = None
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
		if len(self) == 0:
			img = numpy.full((MAX_IMG_HEIGHT, MAX_IMG_WIDTH, 3), 200, numpy.uint8)
			# TODO: if we want to draw a little AgBot picture in the middle, do that here
			return img
		else:
			self.get_summary()
			center = _to_cartesian(self.summary.longitude, self.summary.latitude)
			north_vec, east_vec = _coordinate_vectors(center[0], center[1], center[2])
			rel_posns = [_to_cartesian(record.longitude, record.latitude) - center for record in self]
			rel_north = [_dotprod(north_vec, rel_posn) for rel_posn in rel_posns]
			rel_east = [_dotprod(east_vec, rel_posn) for rel_posn in rel_posns]
			# add a margin to account for width of the BOT
			margin = ROW_DIST[-1] + PLANT_RADIUS_FT + 3
			furthest_east = numpy.max(rel_east) + margin
			furthest_north = numpy.max(rel_north) + margin
			furthest_west = numpy.min(rel_east) - margin
			furthest_south = numpy.min(rel_north) - margin
			width_ft, height_ft = furthest_east - furthest_west, furthest_north - furthest_south
			scale = _img_compute_scale(width_ft, height_ft)
			width_px, height_px = math.floor(width_ft * scale), math.floor(height_ft * scale)
			img = numpy.full((height_px, width_px, 3), 200, numpy.uint8)
			plant_radius_px = math.ceil(scale * PLANT_RADIUS_FT) # radius >= 1 - always draw at least 1px
			def _posn_ft(i):
				return _vec(rel_east[i], rel_north[i])
			def _posn_px(i):
				posn_ft = _posn_ft(i)
				return _vec(int(scale * (posn_ft[0] - furthest_west)), int(scale * (furthest_north - posn_ft[1])))
			if len(self) == 1:
				_draw_record_line(img, self.lines[0], _posn_ft(0), _vec(0,0), scale, plant_radius_px)
			else:
				for i in range(len(self)):
					posn_ft = _posn_ft(i)
					print('posn_ft(%d)=%s'%(i, repr(posn_ft)))
					print('posn_px(%d)=%s'%(i, repr(_posn_px(i))))
					velocity_ft = posn_ft - _posn_ft(i - 1) if i != 0 else _posn_ft(i + 1) - posn_ft
					# compute a vector normal to the direction of travel, pointing right
					normal_ft = _hat(_vec(velocity_ft[1], velocity_ft[0])) if (velocity_ft[0] != 0 or velocity_ft[1] != 0) else _vec(0, 0)
					_draw_record_line(img, self.lines[i], _posn_px(i), normal_ft, scale, plant_radius_px)
			# TODO: if we want to draw a little AgBot picture in the last position, do that here
			return img
	def get_summary(self):
		if self.summary is None:
			if len(self) == 0:
				raise ValueError('Cannot compute summary of an empty record')
			avg_latitude = sum(record.latitude for record in self) / len(self)
			longitudes1 = numpy.array([record.longitude for record in self], numpy.float64)
			longitudes2 = numpy.array([record.longitude if record.longitude < 180.0 else record.longitude - 360.0 \
									for record in self], numpy.float64)
			avg_longitude = numpy.average(longitudes2) \
							if numpy.std(longitudes2) < numpy.std(longitudes1) \
							else numpy.average(longitudes1)
			self.summary = RecordSummary(
				self.record_id, self.name, \
				min(record.timestamp for record in self), \
				max(record.timestamp for record in self), \
				avg_latitude, avg_longitude)
		return self.summary
	def __str__(self):
		return "Record '%s' (%d lines)"%(self.name, len(self))
	def __repr__(self):
		return 'Record(record_id=%s, name=%s, len=%d)'%(self.record_id, self.name, len(self))

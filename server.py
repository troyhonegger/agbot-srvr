#!/usr/bin/python

import cherrypy
import os
import cv2
import subprocess
import signal
import datetime

import estop
from lib import records

def _processor_pid():
	try:
		# runs 'pidof processor.py' in a shell and returns the output (a list
		# of PIDs), or raises a CalledProcessError upon a nonzero exit code.
		return int(subprocess.check_output(['pidof', 'processor.py']).split()[0])
	except subprocess.CalledProcessError:
		return None

class UI:
	pass

class MachineState:
	exposed = True
	def __init__(self):
		pass
	
	@cherrypy.expose
	@cherrypy.tools.json_out()
	def GET(self):
		return { 'processing': _processor_pid() is not None }
	
	@cherrypy.expose
	@cherrypy.tools.accept(media = 'application/json')
	@cherrypy.tools.json_in()
	def PUT(self):
		json_properties = cherrypy.request.json.keys()
		if 'estopped' in json_properties:
			# try and estop. If it fails, return error code
			try:
				estop.estop(kill_processor = True, new_process = False)
				cherrypy.response.status = '200 OK'
			except estop.EstopError as ex:
				cherrypy.response.status = '500 Internal Server Error'
				return repr(ex)
		elif 'processing' in json_properties and cherrypy.request.json['processing'] == True:
			if _processor_pid() is None:
				subprocess.Popen(['/home/agbot/agbot-srvr/processor.py'])
			cherrypy.response.status = '200 OK'
		elif 'processing' in json_properties and cherrypy.request.json['processing'] == False:
			pid = _processor_pid()
			if pid is not None:
				# send a SIGINT to processor.py. This more or less politely asks
				# processor.py to shut down at its earliest convenience.
				os.kill(pid, signal.SIGINT)
			cherrypy.response.status = '200 OK'


@cherrypy.popargs('recordID')
class Records:
	exposed = True
	def __init__(self):
		self.image = RecordImage()
	@cherrypy.expose
	@cherrypy.tools.response_headers(headers = [('Content-Type','application/json')])
	@cherrypy.tools.json_out()
	def GET(self, recordID = None, **params):
		if recordID is None:
			return [{'recordID':recordID, 'name':name} for (recordID, name) in records.get_records()]
		else:
			try:
				record = records.Record.read(recordID)
				if len(record) != 0:
					summary = record.get_summary()
					return {
						'recordID': summary.record_id,
						'name': summary.record_name,
						'startTime': summary.start_time.isoformat(),
						'endTime': summary.end_time.isoformat(),
						'longitude': summary.longitude,
						'latitude': summary.latitude
					}
				else:
					return {
						'recordID': record.record_id,
						'name': record.name,
						'startTime': datetime.datetime.now(),
						'endTime': datetime.datetime.now(),
						'longitude': 0,
						'latitude': 0
					}
			except FileNotFoundError:
				raise cherrypy.HTTPError(404, 'Not Found - record %s does not exist'%(recordID))
class RecordImage:
	exposed = True
	@cherrypy.expose
	@cherrypy.tools.response_headers(headers = [('Content-Type','image/jpeg')])
	def GET(self, recordID, **params):
		try:
			image = records.Record.read(recordID).render()
			retval, stream = cv2.imencode('.jpeg', image)
			if not retval:
				raise cherrypy.HTTPError(500, 'Internal Server Error - could not encode record %s as a JPEG image'%(recordID))
			return stream
		except FileNotFoundError:
			raise cherrypy.HTTPError(404, 'Not Found - record %s does not exist'%(recordID))

class API:
	def __init__(self):
		self.machineState = MachineState()
		self.records = Records()

if __name__ == '__main__':
	path = os.path.dirname(os.path.abspath(__file__))
	cherrypy.config.update(path + '/server.conf')
	cherrypy.tree.mount(UI(), '/', path + '/server.conf')
	cherrypy.tree.mount(API(), '/api', path + '/api.conf')
	cherrypy.engine.start()
	cherrypy.engine.block()

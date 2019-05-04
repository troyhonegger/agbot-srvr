import cherrypy
import os
import json
import cv2

from lib import records

class UI:
	pass

class MachineState:
	exposed = True
	def __init__(self):
		pass
	@cherrypy.expose
	@cherrypy.tools.json_out()
	def GET(self):
		#TODO
		raise cherrypy.HTTPError(501, 'Not Implemented')
		return {'processing':False}
	@cherrypy.expose
	@cherrypy.tools.accept(media = 'application/json')
	@cherrypy.tools.json_in()
	def PUT(self, estopped = None, mode = None):
		#TODO: implement code inside these three 'if' statements
		if cherrypy.request.json['estopped']:
			pass
		if cherrypy.request.json['processing'] == True:
			pass
		elif cherrypy.request.json['processing'] == False:
			pass
		raise cherrypy.HTTPError(501, 'Not Implemented')

@cherrypy.popargs('recordID')
class Records:
	exposed = True
	def __init__(self):
		self.image = RecordImage()
	@cherrypy.expose
	@cherrypy.tools.response_headers(headers = [('Content-Type','application/json')])
	@cherrypy.tools.json_out()
	def GET(self, recordID = None):
		if recordID is None:
			return [{'recordID':recordID, 'name':name} for (recordID, name) in records.get_records()]
		else:
			try:
				record = records.get_summary(recordID)
				return {
					'startTime': record.start_time.isoformat(),
					'endTime': record.end_time.isoformat(),
					'longitude': record.longitude,
					'latitude': record.latitude,
				}
			except FileNotFoundError:
				raise cherrypy.HTTPError(404, 'Not Found - record %s does not exist'%(recordID))
class RecordImage:
	exposed = True
	@cherrypy.tools.response_headers(headers = [('Content-Type','image/jpeg')])
	def GET(self, recordID):
		try:
			retval, bytes = cv2.imencode('.jpeg', records.get_image(recordID))
			if not retval:
				raise cherrypy.HTTPError(500, 'Internal Server Error - could not encode record %s as image'%(recordID))
			return bytes
		except FileNotFoundError:
			raise cherrypy.HTTPError(404, 'Not Found - record %s does not exist'%(recordID))

class API:
	def __init__(self):
		self.machineState = MachineState()
		self.records = Records()

#TODO: implement camera endpoints

if __name__ == '__main__':
	path = os.path.dirname(os.path.abspath(__file__))
	cherrypy.config.update(path + '/server.conf')
	cherrypy.tree.mount(UI(), '/', path + '/server.conf')
	cherrypy.tree.mount(API(), '/api', path + '/api.conf')
	cherrypy.engine.start()
	cherrypy.engine.block()

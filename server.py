import cherrypy
import os

class UI(object):
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

class Records:
	exposed = True
	def __init__(self):
		pass
	@cherrypy.expose
	def GET(self, id = None):
		pass #TODO
		#https://github.com/cherrypy/tools/blob/master/RestfulDispatch might be helpful?

class API(object):
	def __init__(self):
		self.machineState = MachineState()
		self.records = Records()
	
	#TODO: the records and camera endpoints still need implemented

if __name__ == '__main__':
	cherrypy.config.update('server.conf')
	cherrypy.tree.mount(UI(), '/', 'server.conf')
	cherrypy.tree.mount(API(), '/api', 'api.conf')
	cherrypy.engine.start()
	cherrypy.engine.block()
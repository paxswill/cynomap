import logging
from flask import Flask, Response
from map import CynoMap

app = Flask(__name__)

keyid = 0
vcode = ""

@app.route('/cynos.svg')
@app.route('/cynos-<range>.svg')
def cynos(range=13):
	logging.info('Range %s' % range)
	map = CynoMap(jumprange=float(range), keyid=keyid, vcode=vcode).svg.standalone_xml()
	return Response(mimetype='image/svg+xml', response=map)

@app.route('/')
def index():
	return """<iframe src="/cynos.svg" width="600px" height="600px" scrolling="yes"></iframe>"""	
	
if __name__ == '__main__':
	logging.basicConfig(level=logging.DEBUG)
	app.run(host='0.0.0.0')

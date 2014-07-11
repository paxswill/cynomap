import os
import logging
from flask import Flask, Response, render_template
from cynomap import CynoMap

app = Flask(__name__)

@app.route('/cynos.svg')
@app.route('/cynos-<range>.svg')
def cynos(range=13):
    logging.info('Range %s' % range)
    map = CynoMap(jumprange=float(range), keyid=os.environ['CYNOMAP_KEYID'], vcode=os.environ['CYNOMAP_VCODE']).svg.standalone_xml()
    return Response(mimetype='image/svg+xml', response=map)

@app.route('/')
@app.route('/<float:jump_range>/')
def index(jump_range=13.0):
    svg = CynoMap(jumprange=jump_range,
            keyid=os.environ['CYNOMAP_KEYID'],
            vcode=os.environ['CYNOMAP_VCODE']).svg.xml()
    return render_template('index.html', mapsvg=svg)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    app.run(host='0.0.0.0')

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


base_range = {
    'carrier': 6.5,
    'dread': 5.0,
    'dreadnought': 5.0,
    'rorq': 5.0,
    'rorqual': 5.0,
    'jumpfreighter': 5.0,
    'jf': 5.0,
    'mothership': 4.0,
    'mom': 4.0,
    'super': 4.0,
    'supercarrier': 4.0,
    'titan': 3.5,
    'blops': 3.5,
    'blackops': 3.5,
}


@app.route('/')
@app.route('/<float:jump_range>/')
@app.route('/<ship_class>/')
@app.route('/<ship_class>/<int:jdc_level>/')
def index(jump_range=None, ship_class='carrier', jdc_level=4):
    if jump_range is None:
        jump_range = base_range.get(ship_class, 6.5)
        if jdc_level > 5:
            jdc_level = 5
        elif jdc_level < 0:
            jdc_level = 0
        jump_range *= 1 + (0.25 * jdc_level)
    svg = CynoMap(jumprange=jump_range,
            keyid=os.environ['CYNOMAP_KEYID'],
            vcode=os.environ['CYNOMAP_VCODE']).svg.xml()
    return render_template('index.html', mapsvg=svg)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    app.run(host='0.0.0.0')

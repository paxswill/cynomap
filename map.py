#!/usr/bin/env python

import sys
import time
import logging
from math import sqrt
from sqlite3 import connect

from svgfig import *
from eveapi import EVEAPIConnection

from cache import DbCacheHandler

__version__ = (0,0,1)

class CynoMap(object):

	def __init__(self, dbtype='sqlite3', conn={'database': 'cru11-sqlite3-v1.db'}, keyid=None, vcode=None, jumprange=13):
	
		if dbtype == 'sqlite3':
			from sqlite3 import connect
		elif dbtype == 'mysql':
			from MySQLdb import connect
		elif dbtype == 'postgres':
			from psycopg2 import connect
		else:
			self.log.debug('Unknown DB Type %s, attempting to import %s' % (dbtype, dbtype))
			try:
				connect = __import__(dbtype, fromlist=['connect']).connect
			except ImportError:
				self.log.critical('Error importing %s library, check your dbtype is correct' % dbtype)
				raise Exception('Invalid dbtype passed')
				
		self.factor = 20
		self.sddconn = connect(**conn)
		self.keyid = keyid
		self.vcode = vcode
		self.jumprange = jumprange

	@property
	def log(self):
		if not hasattr(self, '_log'):
			self._log = logging.getLogger(self.__class__.__name__)
		return self._log
		
	@property
	def svg(self):
		if not hasattr(self, '_svg'):
			t1 = time.time()
			self._svg = self.render_map()
			t2 = time.time()
			self.log.debug('SVG generated (took %0.3f sec)' % ((t2-t1),))
		return self._svg

	@staticmethod
	def calc_distance(sys1, sys2):
		"""Calculate the distance between two sets of 3d coordinates"""
		return sqrt((sys1['x']-sys2['x'])**2+(sys1['y']-sys2['y'])**2+(sys1['z']-sys2['z'])**2) / 9460000000000000.0

	@property
	def systems(self):
		if not hasattr(self, '_systems'):
			t1 = time.time()
			self._systems = self.get_systems_data()
			t2 = time.time()
			self.log.debug('%s systems data generated (took %0.3f ms)' % (len(self._systems), (t2-t1)*1000.0))
		return self._systems
	
	def get_systems_data(self):
		"""Takes the system data out of the SDD and mangles the coords"""
		
		sql = """SELECT solarSystemID as id,
						solarSystemName as name,
						security,
						x,
						y,
						z
				FROM mapSolarSystems WHERE regionID < 11000001"""
				
		data = {}
		csr = self.sddconn.cursor()
		csr.execute(sql)
		
		for id, name, security, x, y, z in csr:
			reduction = 10000000000000000
			
			cx = ((x / reduction) * self.factor) + 100
			cy = ((y / reduction) * self.factor) + 100
			cz = ((z / reduction) * self.factor) + 100
			
			data[int(id)] = {'id': id, 'name': name, 'security': security, 'x': x, 'y': y, 'z': z, 'cx': cx, 'cy': cy, 'cz': cz }
			
		return data
	
	@property
	def jumps(self):
		if not hasattr(self, '_jumps'):
			t1 = time.time()
			self._jumps = self.get_gate_data()
			t2 = time.time()
			self.log.debug('%s jump data generated (took %0.3f ms)' % (len(self._jumps), (t2-t1)*1000.0))
		return self._jumps
	
	def get_gate_data(self):
		"""Extracts the list of gate jumps out of the SDD"""
	
		sql = """SELECT fromSolarSystemID,
						toSolarSystemID 
				FROM mapSolarSystemJumps"""
		data = []
		csr = self.sddconn.cursor()
		csr.execute(sql)
		
		return [{'from': int(frm), 'to': int(to)} for frm, to in csr]
	
	def get_system_location(self, id):
		"""Attempts to derrive a system ID based on a location ID provided"""
		
		stationsql = "SELECT solarSystemID from StaStations WHERE stationID = ?"
		systemsql = "SELECT solarSystemID from mapSolarSystems where solarSystemID = ?"
		
		apistation = {}
		if not hasattr(self, '_stations'):
			stations = EVEAPIConnection(cacheHandler=DbCacheHandler()).eve.ConquerableStationList().outposts
			for x in stations:
				apistation[x.stationID] = x.solarSystemID
			self._stations = apistation

		csr = self.sddconn.cursor()
		
		if csr.execute(systemsql, (id,)).fetchone():
			return id
		elif id in self._stations:
			return self._stations[id]
		else:
			stid = csr.execute(stationsql, (id,)).fetchone()
			if stid: return stid[0]
		return None
	
	def get_cyno_locations(self):
		"""Aquires the list of corporation members to check for character locations"""
		if not self.keyid or not self.vcode: return {}
		if not hasattr(self, '_cynochars'):
			auth = EVEAPIConnection(cacheHandler=DbCacheHandler()).auth(keyID=self.keyid, vCode=self.vcode)
			#chars = auth.account.APIKeyInfo()
			members = auth.corp.MemberTracking(extended=1)
			
			self._cynochars = {}
			for member in members.members:
				loc = self.get_system_location(member.locationID)
				if not loc: continue
				
				info = member.name
				if not int(loc) in self._cynochars:
					self._cynochars[loc] = [info]
				else:
					self._cynochars[loc].append(info)
			
		return self._cynochars
		
	@property
	def cynos(self):
		if not hasattr(self, '_cynos'):
			self._cynos = self.get_cyno_routes()
		return self._cynos
		
	def get_cyno_routes(self):
		"""Calculates usable cyno routes between cyno alts"""
		routes = []
		for cyno in self.get_cyno_locations().keys():
			sys1 = self.systems[cyno]
			if not sys1['security'] < 0.5: continue
			for cyno2 in self.get_cyno_locations().keys():
				sys2 = self.systems[cyno2]
				if not sys2['security'] < 0.5: continue
				dist = self.calc_distance(self.systems[cyno], self.systems[cyno2])
				#self.log.debug('Checking %s to %s (%sly)' % (sys1['name'], sys2['name'], dist))
				if not cyno == cyno2 and dist <= self.jumprange:
					self.log.info('Cyno route found: %s to %s (%sly)' % (sys1['name'], sys2['name'], dist))
					routes.append((cyno, cyno2))
					
		return routes
		
	def render_map(self, compressed=False):
		"""Renders the map data into a SVG, with gate jumps and cynos where possible"""

		# Generate systems
		lowx = 0
		highx = 0
		lowz = 0
		highz = 0
		sysgroup = SVG('g', id='systems')
		for sys in self.systems.values():
			if sys['id'] in self.get_cyno_locations():
                                if sys['security'] < 0.5:
					fill = 'red'
				else:
					fill = 'green'
				radius = 5
				title = "%s - %s (%s)" % (sys['name'], round(sys['security'], 2), ', '.join(self.get_cyno_locations()[sys['id']]))
			else:
				fill = 'gray'
				for loc in self.get_cyno_locations():
					if self.calc_distance(sys, self.systems[loc]) < self.jumprange:
						fill = 'blue'
				radius = 2
				title = sys['name']
			

			
			if lowx > sys['cx']: lowx = sys['cx']
			if lowz > sys['cz']: lowz = sys['cz']
			if highx < sys['cx']: highx = sys['cx']
			if highz < sys['cz']: highz = sys['cz']
			attrs = {'cx': sys['cx'], 'cy': -sys['cz'], 'r': radius, 'id': 'system-%s' % sys['id'], 'class': 'system', 'fill': fill, 'stroke-width': 0, 'title': title}
			svg = SVG('circle', **attrs)
			sysgroup.append(svg)
			
		# Generate jumps
		jumpgroup = SVG('g', id='jumps')
		for jump in self.jumps:
			sys1 = self.systems[jump['from']]
			sys2 = self.systems[jump['to']]
			attrs = {'x1': sys1['cx'], 'y1': -sys1['cz'], 'x2': sys2['cx'], 'y2': -sys2['cz'], 'id': 'jump-%s-%s' % (jump['from'], jump['to']), 'class': 'jump', 'stroke': 'lightgray'}
			jmp = Line(**attrs).SVG()
			jumpgroup.append(jmp)
			
		# Generate cynos
		cynos = SVG('g', id='cynos')
		for frm, to in self.cynos:
			sys1 = self.systems[frm]
			sys2 = self.systems[to]
			attrs = {'x1': sys1['cx'], 'y1': -sys1['cz'], 'x2': sys2['cx'], 'y2': -sys2['cz'], 'id': 'cyno-%s-%s' % (frm, to), 'class': 'cyno', 'stroke': 'red', 'width': '2px'}
			cyn = Line(**attrs).SVG()
			cynos.append(cyn)
			
		c = canvas()
		c.attr.update({'viewBox': '-1000 -1100 2000 2000', 'height': '2000', 'width': '2000'})
		c.extend([jumpgroup, sysgroup, cynos])
		return c

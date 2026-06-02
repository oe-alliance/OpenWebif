##########################################################################
# OpenWebif: MultiBootController
##########################################################################
# Copyright (C) 2026 jbleyel
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston MA 02110-1301, USA.
##########################################################################

from twisted.web import resource, http, server
import json
from .utilities import getUrlArg
from .models.control import getMultiBootSlots, setMultiBoot


class MultiBootGetResource(resource.Resource):

	def getCallback(self, result):
		req = self.req
		req.setResponseCode(http.OK)
		req.setHeader('Content-type', 'application/json')
		req.setHeader('charset', 'UTF-8')
		try:
			json_data = json.dumps(result, indent=1).encode("UTF-8")
			req.write(json_data)
		except Exception as exc:
			req.setResponseCode(http.INTERNAL_SERVER_ERROR)
			json_data = json.dumps({
				"result": False,
				"error": str(exc)
			}).encode()
			req.write(json_data)
		finally:
			req.finish()

	def render_GET(self, request):
		self.req = request
		d = getMultiBootSlots()
		d.addCallback(self.getCallback)
		d.addErrback(self.getErrorback)
		return server.NOT_DONE_YET

	def getErrorback(self, failure):
		req = self.req
		req.setResponseCode(http.INTERNAL_SERVER_ERROR)
		req.setHeader('Content-type', 'application/json')
		req.setHeader('charset', 'UTF-8')
		try:
			json_data = json.dumps({
				"result": False,
				"error": str(failure.value)
			}).encode("UTF-8")
			req.write(json_data)
		except Exception as exc:
			print(f"Error in getErrorback: {exc}")
		finally:
			req.finish()


class MultiBootSetResource(resource.Resource):

	def __init__(self, session):
		resource.Resource.__init__(self)
		self.session = session

	def render_GET(self, request):

		slot = getUrlArg(request, "slot")
		bootcode = getUrlArg(request, "bootcode")

		if not slot:
			request.setResponseCode(http.OK)
			request.setHeader('Content-type', 'application/json')
			request.setHeader('charset', 'UTF-8')
			return json.dumps({
				"result": False,
				"statetext": "Missing slot parameter",
				"id": ""
			}).encode()

		try:
			slot = int(slot)
		except (ValueError, TypeError):
			request.setResponseCode(http.OK)
			request.setHeader('Content-type', 'application/json')
			request.setHeader('charset', 'UTF-8')
			return json.dumps({
				"result": False,
				"statetext": "Invalid slot parameter",
				"id": ""
			}).encode()

		result = setMultiBoot(self.session, slot, bootcode)
		request.setResponseCode(http.OK)
		request.setHeader('Content-type', 'application/json')
		request.setHeader('charset', 'UTF-8')
		return json.dumps({
			"result": result,
			"statetext": "Rebooting to slot %d" % slot if result else "Failed to set MultiBoot",
			"id": ""
		}).encode()


class MultiBootController(resource.Resource):

	def __init__(self, session=None):
		resource.Resource.__init__(self)
		self.session = session
		self.putChild(b'get', MultiBootGetResource())
		self.putChild(b'set', MultiBootSetResource(self.session))

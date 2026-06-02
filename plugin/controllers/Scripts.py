##########################################################################
# OpenWebif: ScriptsController
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
from enigma import eConsoleAppContainer
import json
import os
from .utilities import getUrlArg


class ScriptExecuteResource(resource.Resource):

	def __init__(self):
		resource.Resource.__init__(self)
		self.container = None
		self.script_output = ''
		self.is_alive = True

	def connectionError(self, err):
		self.is_alive = False

	def onScriptClosed(self, data):
		"""Called when script execution is complete"""
		if self.is_alive:
			try:
				# Write final JSON object with completion marker
				json_data = json.dumps({
					"result": True,
					"output": "",
					"exit_code": 0,
					"complete": True
				}).encode("UTF-8")
				self.request.write(b"data: " + json_data + b"\n\n")
			except Exception as exc:
				print(f"Error in onScriptClosed: {exc}")
			finally:
				self.request.finish()

	def onScriptData(self, data):
		"""Called when script outputs data - stream immediately"""
		if data and self.is_alive:
			try:
				output_text = data.decode('utf-8', errors='ignore')
				# Stream each chunk as SSE (Server-Sent Events)
				json_data = json.dumps({
					"result": True,
					"output": output_text,
					"complete": False
				}).encode("UTF-8")
				self.request.write(b"data: " + json_data + b"\n\n")
			except Exception as exc:
				print(f"Error in onScriptData: {exc}")

	def render_GET(self, request):
		script = getUrlArg(request, "script")

		if not script:
			request.setResponseCode(http.OK)
			request.setHeader('Content-type', 'application/json; charset=utf-8')
			return json.dumps({
				"result": False,
				"output": "Missing script parameter",
				"exit_code": 1
			}).encode("UTF-8")

		# Validate script name to prevent path traversal
		if '/' in script or script.startswith('.'):
			request.setResponseCode(http.OK)
			request.setHeader('Content-type', 'application/json; charset=utf-8')
			return json.dumps({
				"result": False,
				"output": "Invalid script name",
				"exit_code": 1
			}).encode("UTF-8")

		script_path = os.path.join('/usr/script', script)

		# Check if script exists
		if not os.path.exists(script_path):
			request.setResponseCode(http.OK)
			request.setHeader('Content-type', 'application/json; charset=utf-8')
			return json.dumps({
				"result": False,
				"output": f"Script not found: {script}",
				"exit_code": 1
			}).encode("UTF-8")

		self.request = request
		self.script_output = ''
		self.is_alive = True

		# Setup for Server-Sent Events streaming
		request.setResponseCode(http.OK)
		request.setHeader('Content-type', 'text/event-stream; charset=utf-8')
		request.setHeader('Cache-Control', 'no-cache')
		request.setHeader('Connection', 'keep-alive')

		# Setup connection error handler
		if hasattr(request, 'notifyFinish'):
			request.notifyFinish().addErrback(self.connectionError)

		# Create console container
		self.container = eConsoleAppContainer()
		self.container.dataAvail.append(self.onScriptData)
		self.container.appClosed.append(self.onScriptClosed)

		# Execute script
		self.container.execute(f"/bin/sh {script_path}")

		return server.NOT_DONE_YET


class ScriptsController(resource.Resource):

	def __init__(self):
		resource.Resource.__init__(self)
		self.putChild(b'execute', ScriptExecuteResource())

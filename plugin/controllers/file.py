##########################################################################
# OpenWebif: FileController
##########################################################################
# Copyright (C) 2011 - 2022 E2OpenPlugins
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

from glob import glob
from json import dumps
from os.path import exists, isdir, realpath, basename
from re import match
from urllib.parse import quote

from twisted.web import static, resource, http

from Screens.LocationBox import DEFAULT_INHIBIT_DIRECTORIES
from Components.config import config
from .utilities import lenient_force_utf_8, sanitise_filename_slashes, getUrlArg, toBinary


def new_getRequestHostname(self):
	host = self.getHeader(b'host')
	if host:
		if host[0] == '[':
			return host.split(']', 1)[0] + "]"
		return host.split(':', 1)[0].encode('ascii')
	return self.getHost().host.encode('ascii')

# Do wee need this?
#http.Request.getRequestHostname = new_getRequestHostname


class FileController(resource.Resource):
	def render(self, request):
		action = getUrlArg(request, "action", "download")
		file = getUrlArg(request, "file")

		if file is not None:
			filename = lenient_force_utf_8(file)
			filename = sanitise_filename_slashes(realpath(filename))

			if not exists(filename):
				return f"File '{filename}' not found"

			if action == "stream":
				name = getUrlArg(request, "name", "stream")
				port = config.OpenWebif.port.value
				proto = 'http'
				if request.isSecure():
					port = config.OpenWebif.https_port.value
					proto = 'https'
				ourhost = request.getHeader('host')
				m = match(r'.+\:(\d+)$', ourhost)
				if m is not None:
					port = m.group(1)

				response = f"#EXTM3U\n#EXTVLCOPT:http-reconnect=true\n#EXTINF:-1,{name}\n{proto}://{request.getRequestHostname()}:{port}/file?action=download&file={quote(filename)}"
				request.setHeader("Content-Disposition", f'attachment;filename="{name}.m3u"')
				request.setHeader("Content-Type", "application/x-mpegurl")
				return response
			elif action == "delete":
				request.setResponseCode(http.OK)
				return f"TODO: DELETE FILE: {filename}"
			elif action == "download":
				request.setHeader("Content-Disposition", f"attachment;filename=\"{filename.split('/')[-1]}\"")
				rfile = static.File(toBinary(filename), defaultType="application/octet-stream")
				return rfile.render(request)
			else:
				return "wrong action parameter"

		path = getUrlArg(request, "dir")
		if path is not None:
			pattern = '*'
			nofiles = False
			pattern = getUrlArg(request, "pattern", "*")
			nofiles = getUrlArg(request, "nofiles") is not None
			directories = []
			files = []
			request.setHeader("content-type", "application/json; charset=utf-8")
			if exists(path):
				if path == '/':
					path = ''
				try:
					files = glob(f"{path}/{pattern}")
				except OSError:
					files = []
				files.sort()
				tmpfiles = files[:]
				for x in tmpfiles:
					if isdir(x):
						directories.append(f"{x}/")
						files.remove(x)
				if nofiles:
					files = []
				return toBinary(dumps({"result": True, "dirs": directories, "files": files}, indent=2))
			else:
				return toBinary(dumps({"result": False, "message": f"path {path} not exits"}, indent=2))

		tree = "tree" in request.args
		path = getUrlArg(request, "id")
		if tree is not None:
			request.setHeader("content-type", "application/json; charset=utf-8")
			directories = []
			if path is None or path == "#":
				path = "/"
			if exists(path):
				if path == "/":
					path = ""
				try:
					files = glob(f"{path}/*")
				except OSError:
					files = []
				files.sort()
				tmpfiles = files[:]
				for x in tmpfiles:
					if isdir(x) and x not in DEFAULT_INHIBIT_DIRECTORIES:
						directories.append({"id": x, "text": basename(x), "children": True})
			if path == "":
				return toBinary(dumps([{"id": "/", "text": "Root", "children": directories}]))
			else:
				return toBinary(dumps([{"id": path, "text": basename(path), "children": directories}]))

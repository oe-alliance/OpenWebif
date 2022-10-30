##########################################################################
# OpenWebif: IpkgController
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
from os import remove, stat as osstat
from enigma import eConsoleAppContainer
from twisted.web import server, resource, http


from Components.config import config
from .base import BaseController
from .i18n import _
from .utilities import getUrlArg


class IpkgController(BaseController):
	def __init__(self, session, path=""):
		BaseController.__init__(self, path=path, session=session)
		self.putChild(b'upload', IPKGUpload(self.session))

	def render(self, request):
		self.request = request
		self.json = False
		self.container = None
		self.action = getUrlArg(request, "command", "")
		package = getUrlArg(request, "package")
		self.json = getUrlArg(request, "format") == "json"
		fa = getUrlArg(request, "filter")
		if fa is None:
			self.filter = []
		elif fa == 'all':
			self.filter = ['dev', 'staticdev', 'dbg', 'doc', 'src', 'po']
		else:
			self.filter = fa.split(',')
		if self.action != '':
			if self.action in ("update", "upgrade"):
				return self.CallOPKG(request)
			elif self.action in ("info", "status", "install", "forceinstall", "remove", "forceremove"):
				if package is not None:
					return self.CallOPKG(request, package)
				else:
					return self.ShowError(request, "parameter: package is missing")
			elif self.action in ("full", "listall", "list", "list_installed", "list_upgradable"):
				return self.CallOPKList(request)
			elif self.action in ("tmp"):
				tmpfiles = glob('/tmp/*.ipk')  # nosec
				ipks = []
				for tmpfile in tmpfiles:
					ipks.append({
						'path': tmpfile,
						'name': (tmpfile.split('/')[-1]),
						'size': osstat(tmpfile).st_size,
						'date': osstat(tmpfile).st_mtime,
					})
				request.setHeader("content-type", "text/plain")
				request.write(dumps({'ipkfiles': ipks}).encode("ISO-8859-1"))
				request.finish()
				return server.NOT_DONE_YET
			else:
				return self.ShowError(request, "Unknown command: " + self.action)
		else:
			return self.ShowHint(request)

	def parseAll(self):
		map = {}
		try:
			for line in open("/tmp/opkg.tmp", 'r'):
				if line.startswith('Package:'):
					package = line.split(":", 1)[1].strip()
					description = ''
					status = ''
					section = ''
					installed = "0"
					continue
				if package is None:
					continue
				if line.startswith('Status:'):
					status = line.split(":", 1)[1].strip()
					if ' installed' in status.lower():
						installed = "1"
				elif line.startswith('Section:'):
					section = line.split(":", 1)[1].strip()
				elif line.startswith('Version:'):
					version = line.split(":", 1)[1].strip()
				# TDOD : check description
				elif line.startswith('Description:'):
					description = line.split(":", 1)[1].strip()
				elif description and line.startswith(' '):
					description += line[:-1]
				elif len(line) <= 1:
					d = description.split(' ', 3)
					if len(d) > 3:
						if d[1] == 'version':
							description = d[3]
						# TDOD : check this
						if description.startswith('gitAUTOINC'):
							description = description.split(' ', 1)[1]
					if package in map:
						v = map[package][0]
						map[package][3] = v
						map[package][2] = "1"
						map[package][0] = version
					else:
						map.update({package: [version, description.strip(), installed, "0", section]})
					package = None
		except OSError:
			pass

		keys = sorted(map.keys())
		self.ResultString = ""

		ret = []
		for name in keys:
			ignore = False
			if self.filter is not None:
				for f in self.filter:
					if name.endswith('-' + f):
						ignore = True
						continue
			if not ignore:
				ret.append({
					"name": name,
					"v": map[name][0],
					"d": map[name][1],
					"i": map[name][2],
					"u": map[name][3],
					"s": map[name][4]
				})
		return ret

	def Runcmd(self, cmd):
		print("Call /usr/bin/opkg " + cmd)
		self.container.execute("/usr/bin/opkg " + cmd)

# TDOD: check encoding
	def CallOPKList(self, request):
		request.setResponseCode(http.OK)
		self.ResultString = ''
		if hasattr(self.request, 'notifyFinish'):
			self.request.notifyFinish().addErrback(self.connectionError)
		self.container = eConsoleAppContainer()
		self.container.appClosed.append(self.NoMoredata)
		self.IsAlive = True
		self.olddata = None
		if self.action in ("full", "listall"):
			self.Runcmd("info > /tmp/opkg.tmp")
		else:
			self.container.dataAvail.append(self.Moredata)
			self.Runcmd(self.action)
		return server.NOT_DONE_YET

	def CallOPKG(self, request, package=None):
		cmd = ''
		if package is not None:
			if self.action == 'forceremove':
				cmd = 'remove ' + package + ' --force-remove --force-depends'
			elif self.action == 'forceinstall':
				cmd = '--force-overwrite install ' + package
			else:
				cmd = self.action + ' ' + package
		else:
			cmd = self.action
		request.setResponseCode(http.OK)
		self.ResultString = ''
		if hasattr(self.request, 'notifyFinish'):
			self.request.notifyFinish().addErrback(self.connectionError)
		self.container = eConsoleAppContainer()
		self.container.dataAvail.append(self.Moredata)
		self.container.appClosed.append(self.NoMoredata)
		self.IsAlive = True
		self.olddata = None
		self.action
		self.Runcmd(cmd)
		return server.NOT_DONE_YET

	def connectionError(self, err):
		self.IsAlive = False

	def NoMoredata(self, data):
		if self.IsAlive:
			if self.action == "listall":
				self.request.setHeader("content-type", "application/json; charset=utf-8")
				try:
					data = self.parseAll()
					self.request.write(dumps(data).encode("UTF-8"))
				except Exception as exc:
					self.request.setResponseCode(http.INTERNAL_SERVER_ERROR)
					self.request.write(dumps({"result": False, "request": self.request.path, "exception": repr(exc)}).encode("UTF-8"))
			elif self.action == "full":
				try:
					data = open("/tmp/opkg.tmp", 'r').read()
					self.request.write(data.encode("UTF-8"))
				except Exception as exc:
					self.request.setResponseCode(http.INTERNAL_SERVER_ERROR)
					self.request.write(repr(exc).encode("UTF-8"))
			else:
				nresult = ""
				if self.action == "list":
					for a in self.ResultString.split("\n"):
						if a.count(" - ") > 0:
							nresult += a + "\n"
				else:
					for a in self.ResultString.split("\n"):
						if a.count(" - ") > 0:
							if nresult[:-1] == "\n":
								nresult += a
							else:
								nresult += "\n" + a
						else:
							nresult += a + "\n"
				nresult = nresult.replace("\n\n", "\n")
				nresult = nresult.replace("\n ", " ")
				if self.filter is not None:
					pl = nresult.split("\n")
					add = True
					rpl = []
					for p in pl:
						if p.count(" - ") > 0:
							add = True
							name = p.split(' - ')[0]
							for f in self.filter:
								if name.endswith('-' + f):
									add = False
						if add:
							rpl.append(p)

				if self.json:
					data = []
					data.append({"result": True, "packages": rpl})
					self.request.setHeader("content-type", "application/json; charset=utf-8")
					self.request.write(dumps(data).encode("UTF-8"))
				else:
					nresult = '\n'.join(rpl)
					nresult.replace('\n', '<br>\n')
					self.request.write(b"<html><body>\n")
					self.request.write(nresult.encode("UTF-8"))
					self.request.write(b"</body></html>\n")
			self.request.finish()
		return server.NOT_DONE_YET

	def Moredata(self, data):
		if data != self.olddata or self.olddata is None and self.IsAlive:
			data = data.encode("UTF-8")
			self.ResultString += data

	def ShowError(self, request, text):
		request.setResponseCode(http.OK)
		request.write(text.encode("UTF-8"))
		request.finish()
		return server.NOT_DONE_YET

	def ShowHint(self, request):
		html = "<html><body><h1>OpenWebif Interface for OPKG</h1>"
		html += "Usage : ?command=<cmd>&package=packagename<&format=format><&filter=FILTER><br>"
		html += "Valid Commands:<br>list,listall,list_installed,list_upgradable,full<br>"
		html += "Valid Package Commands:<br>info,status,install,remove,forceremove,forceinstall<br>"
		html += "Valid Formats:<br>json,html(default)<br>"
		html += "FILTER :<br>all -> dev,staticdev,dbg,doc,src,po<br>"
		html += "FILTER :<br>dev,staticdev,...<br>"
		html += "</body></html>"
		request.setResponseCode(http.OK)
		request.write(html.encode("UTF-8"))
		request.finish()
		return server.NOT_DONE_YET


class IPKGUpload(resource.Resource):
	def __init__(self, session):
		resource.Resource.__init__(self)
		self.session = session

	def mbasename(self, fname):
		_fname = fname.split('/')
		_fname = _fname[len(_fname) - 1]
		_fname = _fname.split('\\')
		return _fname[len(_fname) - 1]

	def render_POST(self, request):
		request.setResponseCode(http.OK)
		request.setHeader('content-type', 'text/plain')
		request.setHeader('charset', 'UTF-8')
		content = request.args[b'rfile'][0]
		filename = self.mbasename(getUrlArg(request, "filename"))
		if not content or not config.OpenWebif.allow_upload_ipk.value:
			result = [False, _('Error upload File')]
		else:
			if not filename.endswith(".ipk"):
				result = [False, _('wrong filetype')]
			else:
				FN = "/tmp/" + filename  # nosec
				bytecount = 0
				with open(FN, "wb") as fd:
					bytecount = fd.write(content)
				if bytecount <= 0:
					try:
						remove(FN)
					except OSError:
						pass
					result = [False, _('Error writing File')]
				else:
					result = [True, FN]
		return dumps({"Result": result}).encode("UTF-8")

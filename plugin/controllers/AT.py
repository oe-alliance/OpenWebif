##########################################################################
# OpenWebif: ATController
##########################################################################
# Copyright (C) 2013 - 2022 jbleyel and E2OpenPlugins
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

from twisted.web import static, resource, http

from os.path import exists
from os import remove
import tarfile
import json
from .utilities import e2simplexmlresult
from .i18n import _

ATFN = "/tmp/autotimer_backup.tar"  # nosec


class ATBaseController(resource.Resource):
	def __init__(self, session=None):
		resource.Resource.__init__(self)
		self.session = session

	def setHeader(self, request, xml):
		request.setResponseCode(http.OK)
		if xml:
			request.setHeader('Content-type', 'application/xhtml+xml')
		else:
			request.setHeader('content-type', 'text/plain')
		request.setHeader('charset', 'UTF-8')


class ATUploadFile(resource.Resource):

	def __init__(self, session):
		self.session = session
		resource.Resource.__init__(self)

	def render_POST(self, request):
		request.setResponseCode(http.OK)
		request.setHeader('content-type', 'text/plain')
		request.setHeader('charset', 'UTF-8')
		content = request.args[b'rfile'][0]
		if not content:
			result = [False, 'Error upload File']
		else:
			bytecount = 0
			with open(ATFN, "wb") as fd:
				bytecount = fd.write(content)
			if bytecount <= 0:
				try:
					remove(ATFN)
				except OSError:
					pass
				result = [False, _("Error writing File")]
			else:
				result = [True, ATFN]
		return json.dumps({"Result": result}).encode("UTF-8")


class AutoTimerDoBackupResource(ATBaseController):
	def render(self, request):
		self.setHeader(request, True)
		state, statetext = self.backupFiles()
		return e2simplexmlresult(state, statetext)

	def backupFiles(self):
		if exists(ATFN):
			remove(ATFN)
		checkfile = '/tmp/.autotimeredit'
		try:
			with open(checkfile, "w") as fd:
				fd.write("created with AutoTimerWebEditor")

			with tarfile.open(ATFN, "w:gz") as tar:
				tar.add(checkfile)
				tar.add("/etc/enigma2/autotimer.xml")

			remove(checkfile)
			return (True, ATFN)

		except Exception as err:
			print(f"[OpenWebif] Error: create autotimer backup '{err}'")
			return (False, "Error while preparing backup file.")


class AutoTimerDoRestoreResource(ATBaseController):
	def render(self, request):
		self.setHeader(request, True)
		state, statetext = self.restoreFiles()
		return e2simplexmlresult(state, statetext)

	def restoreFiles(self):
		if exists(ATFN):
			check_tar = False
			try:
				with tarfile.open(ATFN) as tar:
					check_tar = tar.getmember("tmp/.autotimeredit")
					if check_tar:
						tar.extract("etc/enigma2/autotimer.xml", "/")
			except Exception as err:
				print(f"[OpenWebif] Error: extract autotimer.xml from backup '{err}'")
				return (False, f"Error, {ATFN} was not created with AutoTimerWebEditor...")

			if check_tar:
				from Plugins.Extensions.AutoTimer.plugin import autotimer
				if autotimer is not None:
					try:
						# Force config reload
						autotimer.configMtime = -1
						autotimer.readXml()
					except Exception as err:
						print(f"[OpenWebif] Error: read autotimer.xml from backup '{err}'")
						remove(ATFN)
						return (False, "Error in autotimer.xml ...")
					remove(ATFN)
				return (True, "AutoTimer-settings were restored successfully")
			else:
				return (False, f"Error, {ATFN} was not created with AutoTimerWebEditor...")
		else:
			return (False, f"Error, {ATFN} does not exists, restore is not possible...")


class ATController(ATBaseController):
	def __init__(self, session):
		ATBaseController.__init__(self, session)
		try:
			from Plugins.Extensions.AutoTimer.AutoTimerResource import AutoTimerDoParseResource, \
				AutoTimerAddOrEditAutoTimerResource, AutoTimerChangeSettingsResource, \
				AutoTimerRemoveAutoTimerResource, AutoTimerSettingsResource, \
				AutoTimerSimulateResource
		except ImportError:
			print("[OpenWebif] AT plugin not found")
			return
		self.putChild(b'parse', AutoTimerDoParseResource())
		self.putChild(b'remove', AutoTimerRemoveAutoTimerResource())
		self.putChild(b'edit', AutoTimerAddOrEditAutoTimerResource())
		self.putChild(b'get', AutoTimerSettingsResource())
		self.putChild(b'set', AutoTimerChangeSettingsResource())
		self.putChild(b'simulate', AutoTimerSimulateResource())
		try:
			from Plugins.Extensions.AutoTimer.AutoTimerResource import AutoTimerTestResource
			self.putChild(b'test', AutoTimerTestResource())
		except ImportError:
			pass
		try:
			from Plugins.Extensions.AutoTimer.AutoTimerResource import AutoTimerChangeResource
			self.putChild(b'change', AutoTimerChangeResource())
		except ImportError:
			pass
		self.putChild(b'uploadfile', ATUploadFile(session))
		self.putChild(b'restore', AutoTimerDoRestoreResource())
		self.putChild(b'backup', AutoTimerDoBackupResource())
		self.putChild(b'tmp', static.File(b'/tmp'))  # nosec
		try:
			from Plugins.Extensions.AutoTimer.AutoTimerResource import AutoTimerUploadXMLConfigurationAutoTimerResource, AutoTimerAddXMLAutoTimerResource
			self.putChild(b'upload_xmlconfiguration', AutoTimerUploadXMLConfigurationAutoTimerResource())
			self.putChild(b'add_xmltimer', AutoTimerAddXMLAutoTimerResource())
		except ImportError:
			pass

	def render(self, request):
		self.setHeader(request, True)
		try:
			from Plugins.Extensions.AutoTimer.plugin import autotimer
			try:
				if autotimer is not None:
					autotimer.readXml()
					return ''.join(autotimer.getXml()).encode("UTF-8")
			except Exception:
				return e2simplexmlresult(False, b"AutoTimer Config not found")
		except ImportError:
			return e2simplexmlresult(False, b"AutoTimer Plugin not found")

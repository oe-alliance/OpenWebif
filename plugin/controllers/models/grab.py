##########################################################################
# OpenWebif: grab
##########################################################################
# Copyright (C) 2011 - 2023 E2OpenPlugins, jbleyel
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

from time import localtime, strftime, time
from twisted.web import resource, server
from enigma import eConsoleAppContainer, eDBoxLCD
from Components.config import config
from Screens.InfoBar import InfoBar
from ServiceReference import ServiceReference
from ..utilities import getUrlArg

GRAB_PATH = "/usr/bin/grab"


class GrabRequest:
	def __init__(self, request, session):
		self.request = request

		mode = None
		graboptions = [GRAB_PATH, "-q", "-s"]

		fileformat = getUrlArg(request, "format", "jpg")
		if fileformat == "jpg":
			graboptions.append("-j")
			graboptions.append("95")
		elif fileformat == "png":
			graboptions.append("-p")
		elif fileformat != "bmp":
			fileformat = "bmp"

		size = getUrlArg(request, "r")
		if size is not None:
			graboptions.append("-r")
			graboptions.append(f"{int(size)}")

		mode = getUrlArg(request, "mode")
		if mode is not None:
			if mode == "osd":
				graboptions.append("-o")
			elif mode == "video":
				graboptions.append("-v")
			elif mode == "pip":
				graboptions.append("-v")
				if InfoBar.instance.session.pipshown:
					graboptions.append("-i 1")
			elif mode == "lcd":
				eDBoxLCD.getInstance().setDump(True)
				fileformat = "png"
				command = "cat /tmp/lcd.png"

		self.filepath = f"/tmp/screenshot.{fileformat}"
		self.container = eConsoleAppContainer()
		self.container.appClosed.append(self.grabFinished)
		self.container.stdoutAvail.append(request.write)
		self.container.setBufferSize(32768)
		if mode == "lcd":
			if self.container.execute(command):
				raise Exception("failed to execute: ", command)
			sref = "lcdshot"
		else:
			self.container.execute(GRAB_PATH, *graboptions)
			try:
				if mode == "pip" and InfoBar.instance.session.pipshown:
					ref = InfoBar.instance.session.pip.getCurrentService().toString()
				else:
					ref = session.nav.getCurrentlyPlayingServiceReference().toString()
				sref = "_".join(ref.split(":", 10)[:10])
				if config.OpenWebif.webcache.screenshotchannelname.value:
					sref = ServiceReference(ref).getServiceName()
			except Exception:  # nosec # noqa: E722
				sref = "screenshot"
		sref = f"{sref}_{strftime('%Y%m%d%H%M%S', localtime(time()))}"
		request.notifyFinish().addErrback(self.requestAborted)
		request.setHeader('Content-Disposition', f'inline; filename={sref}.{fileformat};')
		request.setHeader('Content-Type', f"image/{fileformat.replace('jpg', 'jpeg')}")
		# request.setHeader('Expires', 'Sat, 26 Jul 1997 05:00:00 GMT')
		# request.setHeader('Cache-Control', 'no-store, must-revalidate, post-check=0, pre-check=0')
		# request.setHeader('Pragma', 'no-cache')

	def requestAborted(self, err):
		# Called when client disconnected early, abort the process and
		# don't call request.finish()
		del self.container.appClosed[:]
		self.container.kill()
		del self.request
		del self.container

	def grabFinished(self, retval=None):
		try:
			self.request.finish()
		except RuntimeError as error:
			print(f"[OpenWebif] grabFinished error: {error}")
		# Break the chain of ownership
		del self.request


class GrabScreenshot(resource.Resource):
	def __init__(self, session, path=None):
		resource.Resource.__init__(self)
		self.session = session

	def render(self, request):
		# Add a reference to the grabber to the Request object. This keeps
		# the object alive at least until the request finishes
		request.grab_in_progress = GrabRequest(request, self.session)
		return server.NOT_DONE_YET

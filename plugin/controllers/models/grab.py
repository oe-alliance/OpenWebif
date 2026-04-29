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

import mmap
import struct
import fcntl
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
		command = None
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
		self.graboptions = graboptions
		self.container = eConsoleAppContainer()
		self.container.setBufferSize(32768)
		if mode == "lcd":
			self.container.appClosed.append(self.grabFinished)
			self.container.stdoutAvail.append(request.write)
			if command is None or self.container.execute(command):
				raise RuntimeError(f"failed to execute: {command}")
			sref = "lcdshot"
		else:
			# The DM9xx has a triple-buffered framebuffer (3 pages at Y=0, Y=1080, Y=2160).
			# The grab binary reads from Y=0 of /dev/fb0 regardless of the hardware pan
			# position, so it captures a stale page whenever E2 has panned to Y=1080 or
			# Y=2160.  Fix: copy the currently-displayed page to Y=0 before running grab.
			# This is a synchronous 8 MB copy (~5 ms) which is safe in the event loop.
			self._copyCurrentPageToY0()
			self.container.stdoutAvail.append(request.write)
			self.container.appClosed.append(self.grabFinished)
			self.container.execute(GRAB_PATH, *self.graboptions)
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

	def _copyCurrentPageToY0(self):
		# On devices with a multi-buffered OSD framebuffer (e.g. DM9xx with 3 pages at
		# Y=0/1080/2160), the grab binary calls FBIOGET_VSCREENINFO to read yoffset and
		# then mmap-reads from that offset.  When E2 pans to a back buffer that it is
		# actively rendering into, grab captures a stale or partially-drawn frame.
		# Fix (only applied when yvirt > yres, i.e. multiple pages exist):
		#   1. Copy the currently-displayed page (yoffset) to Y=0 using mmap.move() (~2ms)
		#   2. Call FBIOPAN_DISPLAY(yoffset=0) so grab reads VSCREENINFO yoffset=0 and
		#      reads from Y=0 (our copy). E2 won't render into Y=0 while it is the
		#      hardware front buffer.
		# On single-buffered devices yoff is always 0 and yvirt == yres, so this is a no-op.
		# All errors are caught so grab always runs even if the ioctl is unsupported.
		FBIOGET_VSCREENINFO = 0x4600
		FBIOPAN_DISPLAY = 0x4606
		try:
			with open('/dev/fb0', 'r+b') as fb:
				info = bytearray(fcntl.ioctl(fb, FBIOGET_VSCREENINFO, b'\x00' * 160))
				xres = struct.unpack_from('I', info, 0)[0]
				yres = struct.unpack_from('I', info, 4)[0]
				yvirt = struct.unpack_from('I', info, 12)[0]
				yoff = struct.unpack_from('I', info, 20)[0]
				bpp = struct.unpack_from('I', info, 24)[0]
				if yvirt <= yres:
					return  # single-buffered device, nothing to do
				stride = xres * (bpp // 8)
				page_size = yres * stride
				fb_size = yvirt * stride  # actual total framebuffer size
				if yoff != 0:
					# Copy the front buffer page to Y=0 using native memmove (~2ms for 8MB)
					mm = mmap.mmap(fb.fileno(), fb_size)
					try:
						mm.move(0, yoff * stride, page_size)
					finally:
						mm.close()
				# Pan hardware display to Y=0. Grab will now read VSCREENINFO yoffset=0
				# and read from Y=0 (our copy). E2 won't write to Y=0 while it is the
				# hardware front buffer.
				struct.pack_into('I', info, 16, 0)  # xoffset = 0
				struct.pack_into('I', info, 20, 0)  # yoffset = 0
				fcntl.ioctl(fb, FBIOPAN_DISPLAY, info)
		except Exception as e:
			print(f"[OpenWebif] _copyCurrentPageToY0 error: {e}")

	def requestAborted(self, _err):
		# Called when client disconnected early, abort the process and
		# don't call request.finish()
		if hasattr(self, 'container'):
			del self.container.appClosed[:]
			self.container.kill()
			del self.container
		del self.request

	def grabFinished(self, _retval=None):
		try:
			self.request.finish()
		except RuntimeError as error:
			print(f"[OpenWebif] grabFinished error: {error}")
		# Break the chain of ownership
		del self.request


class GrabScreenshot(resource.Resource):
	def __init__(self, session, _path=None):
		resource.Resource.__init__(self)
		self.session = session

	def render(self, request):
		# Add a reference to the grabber to the Request object. This keeps
		# the object alive at least until the request finishes
		request.grab_in_progress = GrabRequest(request, self.session)
		return server.NOT_DONE_YET

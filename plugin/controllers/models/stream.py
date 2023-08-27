##############################################################################
#                        2011-2022 E2OpenPlugins                                  #
#                                                                            #
#  This file is open source software; you can redistribute it and/or modify  #
#     it under the terms of the GNU General Public License version 2 as      #
#               published by the Free Software Foundation.                   #
#                                                                            #
##############################################################################
from os.path import exists
from re import match
from urllib.parse import unquote, quote
from enigma import eServiceReference, getBestPlayableServiceReference
from ServiceReference import ServiceReference
from Components.config import config
from twisted.web.resource import Resource
from .info import getInfo
from ..utilities import getUrlArg

BMC0 = "/dev/bcm_enc0"
ENC0 = "/dev/encoder0"
ENC0APPLY = "/proc/stb/encoder/0/apply"


class GetSession(Resource):
	def GetSID(self, request):
		sid = request.getSession().uid
		return sid

	def GetAuth(self, request):
		session = request.getSession().sessionNamespaces
		if "pwd" in list(session.keys()) and session["pwd"] is not None:
			return (session["user"], session["pwd"])
		else:
			return None


def getStream(session, request, m3ufile):
	sref = getUrlArg(request, "ref")
	if sref is not None:
		sref = unquote(unquote(sref))
	else:
		sref = ""

	currentserviceref = None
	if m3ufile == "streamcurrent.m3u":
		currentserviceref = session.nav.getCurrentlyPlayingServiceReference()
		sref = currentserviceref.toString()

	if sref.startswith("1:134:"):
		if currentserviceref is None:
			currentserviceref = session.nav.getCurrentlyPlayingServiceReference()
		if currentserviceref is None:
			currentserviceref = eServiceReference()
		ref = getBestPlayableServiceReference(eServiceReference(sref), currentserviceref)
		if ref is None:
			sref = ""
		else:
			sref = ref.toString()

	# #EXTINF:-1,%s\n adding back to show service name in programs like VLC
	progopt = ''
	name = getUrlArg(request, "name")
	if name is not None and config.OpenWebif.service_name_for_stream.value:
		progopt = "#EXTINF:-1,%s\n" % name

	name = "stream"
	portnumber = config.OpenWebif.streamport.value
	info = getInfo()
	# model = info["model"]
	# machinebuild = info["machinebuild"]
	urlparam = '?'
	if info["imagedistro"] in ('openpli', 'satdreamgr', 'openvision'):
		urlparam = '&'
	transcoder_port = None
	args = ""

	device = getUrlArg(request, "device")

	if exists(BMC0):
		try:
			transcoder_port = int(config.plugins.transcodingsetup.port.value)
		except Exception:
			# Transcoding Plugin is not installed or your STB does not support transcoding
			transcoder_port = None
		if device == "phone":
			portnumber = transcoder_port
		_port = getUrlArg(request, "port")
		if _port is not None:
			portnumber = _port
	elif exists(ENC0) or exists(ENC0APPLY):
		transcoder_port = portnumber

	if device == "phone" and (exists(BMC0) or exists(ENC0) or exists(ENC0APPLY)):
		try:
			bitrate = config.plugins.transcodingsetup.bitrate.value
			resolution = config.plugins.transcodingsetup.resolution.value
			(width, height) = tuple(resolution.split('x'))
			# framerate = config.plugins.transcodingsetup.framerate.value
			aspectratio = config.plugins.transcodingsetup.aspectratio.value
			interlaced = config.plugins.transcodingsetup.interlaced.value
			if exists("/proc/stb/encoder/0/vcodec"):
				vcodec = config.plugins.transcodingsetup.vcodec.value
				args = "?bitrate=%s__width=%s__height=%s__vcodec=%s__aspectratio=%s__interlaced=%s" % (bitrate, width, height, vcodec, aspectratio, interlaced)
			else:
				args = "?bitrate=%s__width=%s__height=%s__aspectratio=%s__interlaced=%s" % (bitrate, width, height, aspectratio, interlaced)
			args = args.replace('__', urlparam)
		except Exception:
			pass

	# When you use EXTVLCOPT:program in a transcoded stream, VLC does not play stream
	if config.OpenWebif.service_name_for_stream.value and sref != '' and portnumber != transcoder_port:
		progopt = "%s#EXTVLCOPT:program=%d\n" % (progopt, int(sref.split(':')[3], 16))

	if config.OpenWebif.auth_for_streaming.value:
		asession = GetSession()
		if asession.GetAuth(request) is not None:
			auth = ':'.join(asession.GetAuth(request)) + "@"
		else:
			auth = '-sid:' + str(asession.GetSID(request)) + "@"
	else:
		auth = ''

	icamport = 17999
	icam = "http://127.0.0.1:%s/" % icamport

	if icam in sref:
		portnumber = icamport
		sref = sref.split(icam)[1]
		sref = sref.split("::")[0] + ":"
		auth = ""
		args = ""

	response = "#EXTM3U \n#EXTVLCOPT:http-reconnect=true \n%shttp://%s%s:%s/%s%s\n" % (progopt, auth, request.getRequestHostname(), portnumber, sref, args)
	if config.OpenWebif.playiptvdirect.value:
		if "http://" in sref or "https://" in sref:
			link = sref.split(":http")[1]
			response = "#EXTM3U \n#EXTVLCOPT:http-reconnect=true\n%shttp%s\n" % (progopt, link)
	request.setHeader('Content-Type', 'application/x-mpegurl')
	# Note: do not rename the m3u file all the time
	fname = getUrlArg(request, "fname")
	if fname is not None:
		request.setHeader('Content-Disposition', 'inline; filename=%s.%s;' % (fname, 'm3u8'))
	return response


def getTS(self, request):
	_file = getUrlArg(request, "file")
	if _file is not None:
		filename = unquote(_file)
		if not exists(filename):
			return "File '%s' not found" % (filename)

# ServiceReference is not part of filename so look in the '.ts.meta' file
		sref = ""
		progopt = ''

		if exists(filename + '.meta'):
			metafile = open(filename + '.meta', "r")
			name = ''
			seconds = -1  # unknown duration default
			line = metafile.readline()  # service ref
			if line:
				sref = eServiceReference(line.strip()).toString()
			line2 = metafile.readline()  # name
			if line2:
				name = line2.strip()
			line6 = metafile.readline()  # description
			line6 = metafile.readline()  # recording time
			line6 = metafile.readline()  # tags
			line6 = metafile.readline()  # length

			if line6:
				seconds = float(line6.strip()) / 90000  # In seconds

			if config.OpenWebif.service_name_for_stream.value:
				progopt = "%s#EXTINF:%d,%s\n" % (progopt, seconds, name)

			metafile.close()

		portnumber = None
		proto = 'http'
		info = getInfo()
		# model = info["model"]
		# machinebuild = info["machinebuild"]
		transcoder_port = None
		args = ""
		urlparam = '?'
		if info["imagedistro"] in ('openpli', 'satdreamgr', 'openvision'):
			urlparam = '&'

		device = getUrlArg(request, "device")

		if exists(BMC0) or exists(ENC0) or exists(ENC0APPLY):
			try:
				transcoder_port = int(config.plugins.transcodingsetup.port.value)
			except Exception:
				# Transcoding Plugin is not installed or your STB does not support transcoding
				transcoder_port = None
			if device == "phone":
				portnumber = transcoder_port
			_port = getUrlArg(request, "port")
			if _port is not None:
				portnumber = _port

		if exists(BMC0) or exists(ENC0) or exists(ENC0APPLY):
			if device == "phone":
				try:
					bitrate = config.plugins.transcodingsetup.bitrate.value
					resolution = config.plugins.transcodingsetup.resolution.value
					(width, height) = tuple(resolution.split('x'))
					# framerate = config.plugins.transcodingsetup.framerate.value
					aspectratio = config.plugins.transcodingsetup.aspectratio.value
					interlaced = config.plugins.transcodingsetup.interlaced.value
					if exists("/proc/stb/encoder/0/vcodec"):
						vcodec = config.plugins.transcodingsetup.vcodec.value
						args = "?bitrate=%s__width=%s__height=%s__vcodec=%s__aspectratio=%s__interlaced=%s" % (bitrate, width, height, vcodec, aspectratio, interlaced)
					else:
						args = "?bitrate=%s__width=%s__height=%s__aspectratio=%s__interlaced=%s" % (bitrate, width, height, aspectratio, interlaced)
					args = args.replace('__', urlparam)
				except Exception:
					pass
			# Add position parameter to m3u link
			position = getUrlArg(request, "position")
			if position is not None:
				args = args + "&position=" + position

		# When you use EXTVLCOPT:program in a transcoded stream, VLC does not play stream
		if config.OpenWebif.service_name_for_stream.value and sref != '' and portnumber != transcoder_port:
			progopt = "%s#EXTVLCOPT:program=%d\n" % (progopt, int(sref.split(':')[3], 16))

		if portnumber is None:
			portnumber = config.OpenWebif.port.value
			if request.isSecure():
				portnumber = config.OpenWebif.https_port.value
				proto = 'https'
			ourhost = request.getHeader('host')
			m = match('.+\:(\d+)$', ourhost)
			if m is not None:
				portnumber = m.group(1)

		if config.OpenWebif.auth_for_streaming.value:
			asession = GetSession()
			if asession.GetAuth(request) is not None:
				auth = ':'.join(asession.GetAuth(request)) + "@"
			else:
				auth = '-sid:' + str(asession.GetSID(request)) + "@"
		else:
			auth = ''

		response = "#EXTM3U \n#EXTVLCOPT:http-reconnect=true \n%s%s://%s%s:%s/file?file=%s%s\n" % (progopt, proto, auth, request.getRequestHostname(), portnumber, quote(filename), args)
		request.setHeader('Content-Type', 'application/x-mpegurl')
		return response
	else:
		return "Missing file parameter"


def getStreamSubservices(session, request):
	services = []
	currentserviceref = session.nav.getCurrentlyPlayingServiceReference()

	# TODO : this will only work if sref = current channel
	# the DMM webif can also show subservices for other channels like the current
	# ideas are welcome

	sref = getUrlArg(request, "sRef")
	if sref is not None:
		currentserviceref = eServiceReference(sref)

	if currentserviceref is not None:
		currentservice = session.nav.getCurrentService()
		subservices = currentservice.subServices()

		services.append({
			"servicereference": currentserviceref.toString(),
			"servicename": ServiceReference(currentserviceref).getServiceName()
		})
		if subservices and subservices.getNumberOfSubservices() != 0:
			n = subservices and subservices.getNumberOfSubservices()
			z = 0
			while z < n:
				sub = subservices.getSubservice(z)
				services.append({
					"servicereference": sub.toString(),
					"servicename": sub.getName()
				})
				z += 1
	else:
		services.append({
			"servicereference": "N/A",
			"servicename": "N/A"
		})

	return {"services": services}

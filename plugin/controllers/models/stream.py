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
from ..defaults import STREAMRELAY

BMC0 = "/dev/bcm_enc0"
ENC0 = "/dev/encoder0"
ENC0APPLY = "/proc/stb/encoder/0/apply"


class GetSession(Resource):
	def GetSID(self, request):
		sid = request.getSession().uid.decode()
		return sid

	def GetAuth(self, request):
		session = request.getSession().sessionNamespaces
		if "pwd" in list(session.keys()) and session["pwd"] is not None:
			return (session["user"], session["pwd"])
		else:
			return None


def getStream(session, request, m3ufile):
	sref = getUrlArg(request, "ref")
	sref = unquote(unquote(sref)) if sref is not None else ""

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
	progopt = ""
	name = getUrlArg(request, "name")
	if name is not None and config.OpenWebif.service_name_for_stream.value:
		progopt = f"#EXTINF:-1,{name}\n"

	name = "stream"
	portnumber = config.OpenWebif.streamport.value
	info = getInfo()
	# model = info["model"]
	# machinebuild = info["machinebuild"]
	urlparam = "?"
	if info["imagedistro"] in ("openpli", "satdreamgr", "openvision"):
		urlparam = "&"
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
			(width, height) = tuple(resolution.split("x"))
			# framerate = config.plugins.transcodingsetup.framerate.value
			aspectratio = config.plugins.transcodingsetup.aspectratio.value
			interlaced = config.plugins.transcodingsetup.interlaced.value
			if exists("/proc/stb/encoder/0/vcodec"):
				vcodec = config.plugins.transcodingsetup.vcodec.value
				args = f"?bitrate={bitrate}__width={width}__height={height}__vcodec={vcodec}__aspectratio={aspectratio}__interlaced={interlaced}"
			else:
				args = f"?bitrate={bitrate}__width={width}__height={height}__aspectratio={aspectratio}__interlaced={interlaced}"
			args = args.replace("__", urlparam)
		except Exception:
			pass

	# When you use EXTVLCOPT:program in a transcoded stream, VLC does not play stream
	if config.OpenWebif.service_name_for_stream.value and sref != "" and portnumber != transcoder_port:
		progopt = "%s#EXTVLCOPT:program=%d\n" % (progopt, int(sref.split(":")[3], 16))

	if config.OpenWebif.auth_for_streaming.value:
		asession = GetSession()
		if asession.GetAuth(request) is not None:
			auth = ":".join(asession.GetAuth(request)) + "@"
		else:
			auth = f"-sid:{asession.GetSID(request)}@"
	else:
		auth = ""

	streamrelayport = config.misc.softcam_streamrelay_port.value if STREAMRELAY else 17999
	streamrelayip = ".".join("%d" % d for d in config.misc.softcam_streamrelay_url.value) if STREAMRELAY else "127.0.0.1"
	streamrelayurl = f"http://{streamrelayip}:{streamrelayport}/"

	if streamrelayurl in sref:
		portnumber = streamrelayport
		sref = sref.split(streamrelayurl)[1]
		sref = f'{sref.split("::")[0]}:'
		auth = ""
		args = ""
	elif STREAMRELAY:
		streamRelay = []
		try:
			with open("/etc/enigma2/whitelist_streamrelay") as fd:
				streamRelay = [line.strip() for line in fd.readlines()]
		except OSError:
			pass
		if streamRelay and sref in streamRelay:
			portnumber = streamrelayport
			auth = ""
			args = ""

	response = f"#EXTM3U \n#EXTVLCOPT:http-reconnect=true \n{progopt}http://{auth}{request.getRequestHostname()}:{portnumber}/{sref}{args}\n"
	if config.OpenWebif.playiptvdirect.value:
		if "http://" in sref or "https://" in sref:
			link = sref.split(":http")[1]
			response = f"#EXTM3U \n#EXTVLCOPT:http-reconnect=true\n{progopt}http{link}\n"
	request.setHeader("Content-Type", "application/x-mpegurl")
	# Note: do not rename the m3u file all the time
	fname = getUrlArg(request, "fname")
	if fname is not None:
		request.setHeader("Content-Disposition", f"inline; filename={fname}.m3u8;")
	return response


def getTS(self, request):
	_file = getUrlArg(request, "file")
	if _file is not None:
		filename = unquote(_file)
		if not exists(filename):
			return f"File '{filename}' not found"

# ServiceReference is not part of filename so look in the '.ts.meta' file
		sref = ""
		progopt = ""

		if exists(filename + ".meta"):
			metafile = open(filename + ".meta")
			name = ""
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
				progopt = f"{progopt}#EXTINF:{int(seconds)},{name}\n"

			metafile.close()

		portnumber = None
		proto = "http"
		info = getInfo()
		# model = info["model"]
		# machinebuild = info["machinebuild"]
		transcoder_port = None
		args = ""
		urlparam = "?"
		if info["imagedistro"] in ("openpli", "satdreamgr", "openvision"):
			urlparam = "&"

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
					(width, height) = tuple(resolution.split("x"))
					# framerate = config.plugins.transcodingsetup.framerate.value
					aspectratio = config.plugins.transcodingsetup.aspectratio.value
					interlaced = config.plugins.transcodingsetup.interlaced.value
					if exists("/proc/stb/encoder/0/vcodec"):
						vcodec = config.plugins.transcodingsetup.vcodec.value
						args = f"?bitrate={bitrate}__width={width}__height={height}__vcodec={vcodec}__aspectratio={aspectratio}__interlaced={interlaced}"
					else:
						args = f"?bitrate={bitrate}__width={width}__height={height}__aspectratio={aspectratio}__interlaced={interlaced}"
					args = args.replace("__", urlparam)
				except Exception:
					pass
			# Add position parameter to m3u link
			position = getUrlArg(request, "position")
			if position is not None:
				args = args + "&position=" + position

		# When you use EXTVLCOPT:program in a transcoded stream, VLC does not play stream
		if config.OpenWebif.service_name_for_stream.value and sref != "" and portnumber != transcoder_port:
			progopt = f"{progopt}#EXTVLCOPT:program={int(sref.split(':')[3], 16)}\n"

		if portnumber is None:
			portnumber = config.OpenWebif.port.value
			if request.isSecure():
				portnumber = config.OpenWebif.https_port.value
				proto = "https"
			ourhost = request.getHeader("host")
			m = match(r'.+\:(\d+)$', ourhost)
			if m is not None:
				portnumber = m.group(1)

		if config.OpenWebif.auth_for_streaming.value:
			asession = GetSession()
			if asession.GetAuth(request) is not None:
				auth = ":".join(asession.GetAuth(request)) + "@"
			else:
				auth = f"-sid:{asession.GetSID(request)}@"
		else:
			auth = ""

		response = f"#EXTM3U \n#EXTVLCOPT:http-reconnect=true \n{progopt}{proto}://{auth}{request.getRequestHostname()}:{portnumber}/file?file={quote(filename)}{args}\n"
		request.setHeader("Content-Type", "application/x-mpegurl")
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

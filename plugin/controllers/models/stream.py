##############################################################################
#                        2011-2026 jbleyel, E2OpenPlugins                    #
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
from Components.SystemInfo import BoxInfo
from twisted.web.resource import Resource
from .info import getInfo
from ..utilities import getUrlArg
from ..defaults import STREAMRELAY, globalVars

BMC0 = "/dev/bcm_enc0"
ENC0 = "/dev/encoder0"
DENC0 = "/dev/venc0"
ENC0APPLY = "/proc/stb/encoder/0/apply"
LIVE555_HLS_DEFAULT_PORT = 8090
LIVE555_HLS_DEFAULT_PATH = "stream"


def _requestValue(request, *keys):
	for key in keys:
		value = getUrlArg(request, key)
		if value not in (None, ""):
			return value
	return None


def _selectionValues(element):
	try:
		return [str(value) for value in element.choices]
	except Exception:
		return []


def _newEncoderIndices():
	return list(range(2 if BoxInfo.getItem("TranscodingSettingsMultiEncoder") else 1))


def _normaliseEncoderSelection(value, indices, fallback="auto"):
	value = str("auto" if value in (None, "") else value).strip().lower()
	if value in ("auto", "-1"):
		return "auto"
	try:
		index = int(value)
	except (TypeError, ValueError):
		return fallback
	return str(index) if index in indices else fallback


def _newEncoderSelection(request=None):
	indices = _newEncoderIndices()
	default = _normaliseEncoderSelection(config.plugins.transcodingsettings.encoder.value, indices)
	requested = _requestValue(request, "encoder") if request is not None else None
	return _normaliseEncoderSelection(requested, indices, fallback=default) if requested not in (None, "") else default


def _newEncoderIndex(request=None):
	selection = _newEncoderSelection(request)
	return -1 if selection == "auto" else int(selection)


def _newEncoderUrlValue(request=None):
	selection = _newEncoderSelection(request)
	return "auto" if selection == "auto" else selection


def _newEncoderProfileIndex(request=None):
	indices = _newEncoderIndices()
	index = _newEncoderIndex(request)
	return index if index in indices else (indices[0] if indices else 0)


def _newEncoderConfig(request=None):
	if _newEncoderProfileIndex(request) == 1:
		return config.plugins.transcodingsettings.encoder1
	return config.plugins.transcodingsettings.encoder0


def _newElementValue(request, requestKeys, name, default, transform=None):
	entry = _newEncoderConfig(request)
	element = getattr(entry, name, None)
	configured = getattr(element, "value", default)
	requested = _requestValue(request, *requestKeys)
	if requested in (None, ""):
		return configured
	if transform:
		requested = transform(requested)
	allowed = _selectionValues(element)
	return requested if str(requested) in allowed else configured


def _normaliseBitrate(value):
	try:
		value = int(value)
	except (TypeError, ValueError):
		return str(value)
	return str(value * 1000 if 0 < value <= 20000 else value)


def _normaliseFramerate(value):
	value = str(value).strip()
	decimalRates = {
		"23.976": "23976",
		"24": "24000",
		"25": "25000",
		"29.97": "29970",
		"30": "30000",
		"50": "50000",
		"59.94": "59940",
		"60": "60000",
	}
	if value in decimalRates:
		return decimalRates[value]
	try:
		number = int(value)
	except (TypeError, ValueError):
		return value
	return str(number * 1000 if 0 < number < 1000 else number)


def _newBitrateValue(request):
	return _newElementValue(request, ("bitrate", "video_bitrate"), "bitrate", "2000000", _normaliseBitrate)


def _newFramerateValue(request):
	return _newElementValue(request, ("framerate",), "framerate", "25000", _normaliseFramerate)


def _newChoiceValue(request, requestKeys, name, default):
	return _newElementValue(request, requestKeys, name, default)


def _splitResolution(value, default=("1280", "720")):
	try:
		width, height = str(value).lower().split("x", 1)
		width = str(int(width))
		height = str(int(height))
		if int(width) <= 0 or int(height) <= 0:
			raise ValueError
		return width, height
	except (TypeError, ValueError):
		return default


def _newTranscodingResolution(request):
	entry = _newEncoderConfig(request)
	element = getattr(entry, "resolution", None)
	configured = str(getattr(element, "value", "1280x720"))
	width = _requestValue(request, "width")
	height = _requestValue(request, "height")
	resolution = _requestValue(request, "resolution")
	requested = ""
	if width and height:
		requested = "%sx%s" % _splitResolution("%sx%s" % (width, height), ("", ""))
	elif resolution:
		requested = "%sx%s" % _splitResolution(resolution, ("", ""))
	if requested and requested in _selectionValues(element):
		configured = requested
	return _splitResolution(configured)


def _newLiveVideoCodec(request):
	element = config.plugins.transcodingsettings.live.videoCodec
	configured = str(element.value)
	requested = _requestValue(request, "vcodec", "video_codec")
	if requested:
		requested = str(requested).lower()
		requested = "h265" if requested == "hevc" else requested
		if requested in _selectionValues(element):
			return requested
	return configured


def _newLiveAudioBitrate(request):
	configured = int(config.plugins.transcodingsettings.live.audioBitrate.value)
	value = _requestValue(request, "audio_bitrate", "abitrate")
	try:
		value = int(value) if value not in (None, "") else configured
	except (TypeError, ValueError):
		value = configured
	if value > 1000:
		value //= 1000
	return max(32, min(448, value))


def _live555HlsArgs(request, sref):
	width, height = _newTranscodingResolution(request)
	values = [
		("ref", sref),
		("encoder", _newEncoderUrlValue(request)),
		("bitrate", _newBitrateValue(request)),
		("width", width),
		("height", height),
		("framerate", _newFramerateValue(request)),
		("vcodec", _newLiveVideoCodec(request)),
		("acodec", "aac"),
		("audio_bitrate", _newLiveAudioBitrate(request)),
		("aspectratio", _newChoiceValue(request, ("aspectratio",), "aspectratio", "0")),
		("interlaced", _newChoiceValue(request, ("interlaced",), "interlaced", "0")),
	]
	return "?" + "&".join(f"{key}={quote(str(value), safe='')}" for key, value in values if value not in (None, ""))


def _newTranscodingArgs(request, urlparam, port):
	width, height = _newTranscodingResolution(request)
	bitrate = _newBitrateValue(request)
	aspectratio = _newChoiceValue(request, ("aspectratio",), "aspectratio", "0")
	interlaced = _newChoiceValue(request, ("interlaced",), "interlaced", "0")
	vcodec = _newChoiceValue(request, ("vcodec", "video_codec"), "videocodec", "h264")
	parts = [f"bitrate={bitrate}", f"width={width}", f"height={height}"]
	if int(port) == 8001:
		parts.append(f"encoder={_newEncoderUrlValue(request)}")
		framerate = _newFramerateValue(request)
		acodec = _newChoiceValue(request, ("acodec", "audio_codec"), "audiocodec", "aac")
		parts.extend((f"framerate={framerate}", f"vcodec={vcodec}", f"acodec={acodec}", f"aspectratio={aspectratio}", f"interlaced={interlaced}"))
	else:
		parts.extend((f"vcodec={vcodec}", f"aspectratio={aspectratio}", f"interlaced={interlaced}"))
	return "?" + urlparam.join(parts)


def _getLive555HlsStream(request, sref, progopt, linkOnly=False):
	def _live555HlsAuth():
		user = config.plugins.transcodingsettings.hls.user.value
		password = config.plugins.transcodingsettings.hls.password.value
		if user:
			return f"{quote(str(user), safe='')}:{quote(str(password or ''), safe='')}@"
		return ""

	def _live555HlsPath():
		path = config.plugins.transcodingsettings.hls.path.value
		path = str(path or LIVE555_HLS_DEFAULT_PATH).strip("/")
		return path or LIVE555_HLS_DEFAULT_PATH

	live555HlsPort = config.plugins.transcodingsettings.hls.port.value

	hlsUrl = f"http://{_live555HlsAuth()}{request.getRequestHostname()}:{live555HlsPort}/{_live555HlsPath()}.m3u8{_live555HlsArgs(request, sref)}"
	print(f"[OpenWebif] HLSUrl='{hlsUrl}'")
	if linkOnly:
		return hlsUrl
	response = f"#EXTM3U \n#EXTVLCOPT:http-reconnect=true \n{progopt}{hlsUrl}\n"
	request.setHeader("Content-Type", "application/vnd.apple.mpegurl")
	fname = getUrlArg(request, "fname")
	if fname is not None:
		request.setHeader("Content-Disposition", f"attachment; filename={fname}.m3u8;")
	return response


def getLive555HlsWebTVBase(hostname):
	user = config.plugins.transcodingsettings.hls.user.value
	password = config.plugins.transcodingsettings.hls.password.value
	auth = f"{quote(str(user), safe='')}:{quote(str(password or ''), safe='')}@" if user else ""
	port = config.plugins.transcodingsettings.hls.port.value
	path = str(config.plugins.transcodingsettings.hls.path.value or LIVE555_HLS_DEFAULT_PATH).strip("/") or LIVE555_HLS_DEFAULT_PATH
	return f"http://{auth}{hostname}:{port}/{path}.m3u8"


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

	enc = False

	if globalVars.transcodingNew:
		if m3ufile == "streamnew.m3u":
			if globalVars.live555Hls and config.OpenWebif.webcache.transcoding_mode.value == 2 and device == "phone":
				return _getLive555HlsStream(request, sref, progopt)
			if device == "phone":
				enc = True
				portnumber = 8002 if config.OpenWebif.webcache.transcoding_mode.value == 1 else 8001
				args = _newTranscodingArgs(request, urlparam, portnumber)

		elif m3ufile == "streamhls.m3u" and globalVars.live555Hls:
			return _getLive555HlsStream(request, sref, progopt, linkOnly=True)
		else:
			if config.plugins.transcodingsettings.enabled.value:
				transcoder_port = config.plugins.transcodingsettings.port.value
				enc = True
				if device == "phone":
					portnumber = transcoder_port
					args = _newTranscodingArgs(request, urlparam, transcoder_port)
	else:
		if m3ufile == "streamhls.m3u":
			return ""
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
			enc = True
		elif exists(ENC0) or exists(ENC0APPLY) or exists(DENC0):
			transcoder_port = portnumber
			enc = True

		if device == "phone" and enc:
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
	# A transcoder creates a new MPEG-TS program, so the source service ID must
	# not be forced in VLC for phone/transcoding requests.
	if config.OpenWebif.service_name_for_stream.value and sref != "" and not (device == "phone" and enc) and portnumber != transcoder_port:
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

	request.setHeader("Content-Type", "application/vnd.apple.mpegurl")
	# Note: do not rename the m3u file all the time
	fname = getUrlArg(request, "fname")
	if fname is not None:
		request.setHeader("Content-Disposition", f"attachment; filename={fname}.m3u8;")
	return response


def getTS(session, request):
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

		if globalVars.transcodingNew:
			if config.plugins.transcodingsettings.enabled.value:
				transcoder_port = config.plugins.transcodingsettings.port.value
				if device == "phone":
					portnumber = transcoder_port
					args = _newTranscodingArgs(request, urlparam, transcoder_port)
				position = getUrlArg(request, "position")
				if position is not None:
					args = args + "&position=" + position
		else:
			if exists(BMC0) or exists(ENC0) or exists(ENC0APPLY) or exists(DENC0):
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
		request.setHeader("Content-Type", "application/vnd.apple.mpegurl")
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

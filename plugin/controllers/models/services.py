##########################################################################
# OpenWebif: services
##########################################################################
# Copyright (C) 2011 - 2024 E2OpenPlugins, jbleyel
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

from datetime import datetime
from collections import OrderedDict
from re import search, sub, IGNORECASE
from os.path import isfile, join as pathjoin
from urllib.parse import quote, unquote
from time import time, localtime, strftime, mktime
from unicodedata import normalize
from enigma import eServiceCenter, eServiceReference, iServiceInformation

from Components.ParentalControl import parentalControl
from Components.config import config
from Components.NimManager import nimmanager
import NavigationInstance
from ServiceReference import ServiceReference
from Screens.ChannelSelection import service_types_tv, service_types_radio, FLAG_SERVICE_NEW_FOUND
from Screens.InfoBar import InfoBar

from .info import getOrbitalText, getOrb
from ..utilities import parse_servicereference, SERVICE_TYPE_LOOKUP, NS_LOOKUP
from ..i18n import _, tstrings
from ..defaults import PICON_PATH, STREAMRELAY, LCNDB
from .epg import EPG, convertGenre, getIPTVLink, filterName, convertDesc, GetWithAlternative


def getServiceInfoString(info, what):
	v = info.getInfo(what)
	if v == -1:
		return "N/A"
	if v == -2:
		return info.getInfoString(what)
	return v


def getCurrentService(session):
	try:
		info = session.nav.getCurrentService().info()
		ref = str(getServiceInfoString(info, iServiceInformation.sServiceref))
		if len(ref) < 10:
			serviceref = session.nav.getCurrentlyPlayingServiceReference()
			if serviceref is not None:
				ref = serviceref.toString()

		ns = getServiceInfoString(info, iServiceInformation.sNamespace)
		try:
			ns = int(ns)
		except ValueError:
			ns = 0

		bqname = ""
		bqref = ""

		try:
			servicelist = InfoBar.instance.servicelist
			epg_bouquet = servicelist and servicelist.getRoot()
			if epg_bouquet:
				bqname = ServiceReference(epg_bouquet).getServiceName()
				bqref = ServiceReference(epg_bouquet).ref.toString()
		except:  # nosec # noqa: E722
			pass

		return {
			"result": True,
			"name": filterName(info.getName()),
			"namespace": 0xffffffff & ns,
			"aspect": getServiceInfoString(info, iServiceInformation.sAspect),
			"provider": getServiceInfoString(info, iServiceInformation.sProvider),
			"width": getServiceInfoString(info, iServiceInformation.sVideoWidth),
			"height": getServiceInfoString(info, iServiceInformation.sVideoHeight),
			"apid": getServiceInfoString(info, iServiceInformation.sAudioPID),
			"vpid": getServiceInfoString(info, iServiceInformation.sVideoPID),
			"pcrpid": getServiceInfoString(info, iServiceInformation.sPCRPID),
			"pmtpid": getServiceInfoString(info, iServiceInformation.sPMTPID),
			"txtpid": getServiceInfoString(info, iServiceInformation.sTXTPID),
			"tsid": getServiceInfoString(info, iServiceInformation.sTSID),
			"onid": getServiceInfoString(info, iServiceInformation.sONID),
			"sid": getServiceInfoString(info, iServiceInformation.sSID),
			"ref": quote(ref, safe=' ~@#$&()*!+=:;,.?/\''),
			"iswidescreen": info.getInfo(iServiceInformation.sAspect) in (3, 4, 7, 8, 0xB, 0xC, 0xF, 0x10),
			"bqref": quote(bqref, safe=' ~@#$&()*!+=:;,.?/\''),
			"bqname": bqname
		}
	except Exception as e:
		print(str(e))
		return {
			"result": False,
			"name": "",
			"namespace": "",
			"aspect": 0,
			"provider": "",
			"width": 0,
			"height": 0,
			"apid": 0,
			"vpid": 0,
			"pcrpid": 0,
			"pmtpid": 0,
			"txtpid": "N/A",
			"tsid": 0,
			"onid": 0,
			"sid": 0,
			"ref": "",
			"iswidescreen": False,
			"bqref": "",
			"bqname": ""
		}


def getCurrentFullInfo(session):
	_now = _next = {}
	inf = getCurrentService(session)
	inf['tuners'] = list(map(chr, list(range(65, 65 + nimmanager.getSlotCount()))))

	try:
		info = session.nav.getCurrentService().info()
	except:  # nosec # noqa: E722
		info = None

	try:
		subservices = session.nav.getCurrentService().subServices()
	except:  # nosec # noqa: E722
		subservices = None

	try:
		audio = session.nav.getCurrentService().audioTracks()
	except:  # nosec # noqa: E722
		audio = None

	try:
		ref = session.nav.getCurrentlyPlayingServiceReference().toString()
	except:  # nosec # noqa: E722
		ref = None

	if ref is not None:
		inf['sref'] = '_'.join(ref.split(':', 10)[:10])
		inf['srefv2'] = ref
		inf['picon'] = getPicon(ref)
		inf['wide'] = inf['aspect'] in (3, 4, 7, 8, 0xB, 0xC, 0xF, 0x10)
		inf['ttext'] = getServiceInfoString(info, iServiceInformation.sTXTPID)
		inf['crypt'] = getServiceInfoString(info, iServiceInformation.sIsCrypted)
		inf['subs'] = str(subservices and subservices.getNumberOfSubservices() > 0)
	else:
		inf['sref'] = None
		inf['picon'] = None
		inf['wide'] = None
		inf['ttext'] = None
		inf['crypt'] = None
		inf['subs'] = None

	inf['date'] = strftime(_("%d.%m.%Y"), (localtime()))
	inf['dolby'] = False
	inf['audio_desc'] = ""
	inf['audio_lang'] = ""

	if audio:
		# n = audio.getNumberOfTracks()
		# idx = 0
		# while idx < n:
		# 	i = audio.getTrackInfo(idx)
		# 	description = i.getDescription()
		# 	inf['audio'] = inf['audio'] + description + i.getLanguage() + "["+audio.getTrackInfo(audio.getCurrentTrack()).getLanguage()+"]"
		# 	if "AC3" in description or "DTS" in description or "Dolby Digital" in description:
		# 		inf['dolby'] = True
		# 	idx += 1
		audio_info = audio.getTrackInfo(audio.getCurrentTrack())
		description = audio_info.getDescription()
		if description in ["AC3", "DTS", "Dolby Digital"]:
			inf['dolby'] = True
		inf['audio_desc'] = audio_info.getDescription()
		inf['audio_lang'] = audio_info.getLanguage()

	try:
		feinfo = session.nav.getCurrentService().frontendInfo()
	except:  # nosec # noqa: E722
		feinfo = None

	frontenddata = feinfo and feinfo.getAll(True)

	if frontenddata is not None:
		cur_info = feinfo.getTransponderData(True)
		inf['tunertype'] = frontenddata.get("tuner_type", "UNKNOWN")
		if frontenddata.get("system", -1) == 1:
			inf['tunertype'] += "2"
		inf['tunernumber'] = frontenddata.get("tuner_number")
		orb = getOrbitalText(cur_info)
		inf['orbital_position'] = orb
		# if cur_info:
		# 	if cur_info.get('tuner_type') == "DVB-S":
		# 		inf['orbital_position'] = _("Orbital Position") + ': ' + orb
	else:
		inf['tunernumber'] = "N/A"
		inf['tunertype'] = "N/A"

	try:
		frontendstatus = feinfo and feinfo.getFrontendStatus()
	except:  # nosec # noqa: E722
		frontendstatus = None

	if frontendstatus is not None:
		percent = frontendstatus.get("tuner_signal_quality")
		if percent is not None:
			inf['snr'] = int(percent * 100 / 65535)
			inf['snr_db'] = inf['snr']
		percent = frontendstatus.get("tuner_signal_quality_db")
		if percent is not None:
			inf['snr_db'] = f"{percent / 100.0:3.02f} dB"
		percent = frontendstatus.get("tuner_signal_power")
		if percent is not None:
			inf['agc'] = int(percent * 100 / 65535)
		percent = frontendstatus.get("tuner_bit_error_rate")
		if percent is not None:
			inf['ber'] = int(percent * 100 / 65535)
	else:
		inf['snr'] = 0
		inf['snr_db'] = inf['snr']
		inf['agc'] = 0
		inf['ber'] = 0

	try:
		recordings = session.nav.getRecordings()
	except:  # nosec # noqa: E722
		recordings = None

	inf['rec_state'] = False
	if recordings:
		inf['rec_state'] = True

	ev = getChannelEpg(ref, nownext=True)
	if ev and len(ev['events']) > 1:
		_now = ev['events'][0] or {}
		_next = ev['events'][1] or {}
		if _now and len(_now['title']) > 50:
			_now['title'] = _now['title'][0:48] + "..."
		if _next and len(_next['title']) > 50:
			_next['title'] = _next['title'][0:48] + "..."

	return {"info": inf, "now": _now, "next": _next}


def getBouquets(stype):
	s_type = service_types_tv
	s_type2 = "bouquets.tv"
	if stype == "radio":
		s_type = service_types_radio
		s_type2 = "bouquets.radio"
	servicehandler = eServiceCenter.getInstance()
	services = servicehandler.list(eServiceReference(f'{s_type} FROM BOUQUET "{s_type2}" ORDER BY bouquet'))
	bouquets = services and services.getContent("SN", True)
	bouquets = removeHiddenBouquets(bouquets)
	return {"bouquets": bouquets}


def removeHiddenBouquets(bouquetlist):
	bouquets = bouquetlist
	if hasattr(eServiceReference, 'isInvisible'):
		for bouquet in bouquetlist:
			flags = int(bouquet[0].split(':')[1])
			if flags & eServiceReference.isInvisible and bouquet in bouquets:
				bouquets.remove(bouquet)
	return bouquets


def getProviders(stype):
	s_type = service_types_tv
	if stype == "radio":
		s_type = service_types_radio
	servicehandler = eServiceCenter.getInstance()
	services = servicehandler.list(eServiceReference(f'{s_type} FROM PROVIDERS ORDER BY name'))
	providers = services and services.getContent("SN", True)
	return {"providers": providers}


def getSatellites(stype):
	ret = []
	s_type = service_types_tv
	if stype == "radio":
		s_type = service_types_radio
	refstr = f'{s_type} FROM SATELLITES ORDER BY satellitePosition'
	ref = eServiceReference(refstr)
	servicehandler = eServiceCenter.getInstance()
	servicelist = servicehandler.list(ref)
	if servicelist is not None:
		while True:
			service = servicelist.getNext()
			if not service.valid():
				break
			unsigned_orbpos = service.getUnsignedData(4) >> 16
			orbpos = service.getData(4) >> 16
			if orbpos < 0:
				orbpos += 3600
			if service.getPath().find("FROM PROVIDER") != -1:
				# service_type = _("Providers")
				continue
			elif service.getPath().find("flags == %d" % (FLAG_SERVICE_NEW_FOUND)) != -1:
				service_type = _("New")
			else:
				service_type = _("Services")
			try:
				service_name = str(nimmanager.getSatDescription(orbpos))
			except:  # nosec # noqa: E722
				if unsigned_orbpos == 0xFFFF:  # Cable
					service_name = _("Cable")
				elif unsigned_orbpos == 0xEEEE:  # Terrestrial
					service_name = _("Terrestrial")
				else:
					service_name = getOrb(orbpos)
			service.setName(f"{service_name} - {service_type}")
			ret.append({
				"service": service.toString(),
				"name": service.getName()
			})
	ret = sortSatellites(ret)
	return {"satellites": ret}


def sortSatellites(satlist):
	sortdict = {}
	i = 0
	for k in satlist:
		result = search(r"\s*\(satellitePosition\s*==\s*(\d+)\)\s*", k["service"], IGNORECASE)
		if result is None:
			return satlist
		orb = int(result.group(1))
		if orb > 3600:
			orb *= -1
		elif orb > 1800:
			orb -= 3600
		if orb not in sortdict:
			sortdict[orb] = []
		sortdict[orb].append(i)
		i += 1
	outlist = []
	for key in sorted(sortdict.keys()):
		for v in sortdict[key]:
			outlist.append(satlist[v])
	return outlist


def getProtection(sref):
	isprotected = "0"
	if config.ParentalControl.configured.value and config.ParentalControl.servicepinactive.value:
		protection = parentalControl.getProtectionLevel(sref)
		if protection != -1:
			if config.ParentalControl.type.value == "blacklist":
				if sref in parentalControl.blacklist:
					if "SERVICE" in parentalControl.blacklist[sref]:
						isprotected = '1'
					elif "BOUQUET" in parentalControl.blacklist[sref]:
						isprotected = '2'
					else:
						isprotected = '3'
			elif config.ParentalControl.type.value == "whitelist":
				if sref not in parentalControl.whitelist:
					service = eServiceReference(sref)
					if service.flags & eServiceReference.isGroup:
						isprotected = '5'
					else:
						isprotected = '4'
	return isprotected


def getChannels(idbouquet, stype):

	picons = {}

	def _getPicon(sref):
		if sref in picons:
			return picons[sref]
		else:
			picons[sref] = getPicon(sref)
			return picons[sref]

	ret = []
	idp = 0
	s_type = service_types_tv
	if stype == "radio":
		s_type = service_types_radio
	if idbouquet == "ALL":
		idbouquet = f'{s_type} ORDER BY name'

	epg = EPG()
	servicehandler = eServiceCenter.getInstance()
	services = servicehandler.list(eServiceReference(idbouquet))
	channels = services and services.getContent("SN", True)
	epgnownextevents = epg.getMultiChannelNowNextEvents([item[0] for item in channels])
	index = -2

	streamRelay = []
	streamrelayport = 17999
	if STREAMRELAY:
		streamrelayport = config.misc.softcam_streamrelay_port.value

		try:
			with open("/etc/enigma2/whitelist_streamrelay") as fd:
				streamRelay = [line.strip() for line in fd.readlines()]
		except OSError:
			pass

	for channel in channels:
		index = index + 2  # each channel has a `now` and a `next` event entry
		chan = {
			'ref': quote(channel[0], safe=' ~@%#$&()*!+=:;,.?/\'')
		}

		if chan['ref'].split(":")[1] == '320':  # Hide hidden number markers
			continue
		chan['name'] = filterName(channel[1])
		if chan['ref'].split(":")[0] == '5002':  # BAD fix !!! this needs to fix in enigma2 !!!
			chan['name'] = chan['ref'].split(":")[-1]
		# IPTV
		ref = chan['ref']
		isStreamRelay = f"%3a{streamrelayport}/" in ref
		chan['link'] = "" if isStreamRelay else getIPTVLink(chan['ref'])
		if isStreamRelay or (streamRelay and ref in streamRelay):
			chan['sr'] = "1"

		if not int(channel[0].split(":")[1]) & 64:
			psref = parse_servicereference(channel[0])
			chan['service_type'] = SERVICE_TYPE_LOOKUP.get(psref.get('service_type'), "UNKNOWN")
			nsi = psref.get('ns')
			ns = NS_LOOKUP.get(nsi, "DVB-S")
			if ns == "DVB-S":
				chan['ns'] = getOrb(nsi >> 16 & 0xFFF)
			else:
				chan['ns'] = ns
			chan['picon'] = _getPicon(chan['ref'])
			if config.OpenWebif.parentalenabled.value and config.ParentalControl.configured.value and config.ParentalControl.servicepinactive.value:
				chan['protection'] = getProtection(channel[0])
			else:
				chan['protection'] = "0"

			nowevent = [epgnownextevents[index]][0]

			if nowevent[4]:
				chan['now_title'] = filterName(nowevent[0])
				chan['now_begin'] = strftime("%H:%M", (localtime(nowevent[1])))
				chan['now_end'] = strftime("%H:%M", (localtime(nowevent[1] + nowevent[2])))
				chan['now_left'] = int(((nowevent[1] + nowevent[2]) - nowevent[3]) / 60)
				chan['progress'] = int((nowevent[3] - nowevent[1]) * 100 / nowevent[2])
				chan['now_ev_id'] = nowevent[4]
				chan['now_idp'] = "nowd" + str(idp)
				chan['now_shortdesc'] = nowevent[5].strip()
				chan['now_extdesc'] = nowevent[6].strip()  # [E] Event Extended Description
				nextevent = [epgnownextevents[index + 1]][0]

# Some fields have been seen to be missing from the next event...
				if nextevent[4]:
					if nextevent[1] is None:
						nextevent[1] = time()
					if nextevent[2] is None:
						nextevent[2] = 0

					chan['next_title'] = filterName(nextevent[0])
					chan['next_begin'] = strftime("%H:%M", (localtime(nextevent[1])))
					chan['next_end'] = strftime("%H:%M", (localtime(nextevent[1] + nextevent[2])))
					chan['next_duration'] = int(nextevent[2] / 60)
					chan['next_ev_id'] = nextevent[4]
					chan['next_idp'] = "nextd" + str(idp)
					chan['next_shortdesc'] = nextevent[5].strip()
					chan['next_extdesc'] = nextevent[6]
				else:   # Have to fudge one in, as rest of OWI code expects it...
					# TODO: investigate use of X to stuff an empty entry
					chan['next_title'] = "<<absent>>"
					chan['next_begin'] = chan['now_end']
					chan['next_end'] = chan['now_end']
					chan['next_duration'] = 0
					chan['next_ev_id'] = chan['now_ev_id']
					chan['next_idp'] = chan['now_idp']
					chan['next_shortdesc'] = ""
				idp += 1

		if int(channel[0].split(":")[1]) != 832:
			ret.append(chan)
	return {"channels": ret}


def getServices(sref, showall=True, showhidden=False, pos=0, showproviders=False, picon=False, noiptv=False, removenamefromsref=False, excludeprogram=False, excludevod=False, showstreamrelay=False):
	starttime = datetime.now()
	services = []
	allproviders = {}
	calcpos = False
	servicehandler = eServiceCenter.getInstance()

	if not sref:
		sref = f'{service_types_tv} FROM BOUQUET "bouquets.tv" ORDER BY bouquet'
		calcpos = True
	elif ' "bouquets.radio" ' in sref or ' "bouquets.tv" ' in sref:
		calcpos = True

	if showproviders:
		s_type = service_types_tv
		if "radio" in sref:
			s_type = service_types_radio
		pservices = servicehandler.list(eServiceReference(f'{s_type} FROM PROVIDERS ORDER BY name'))
		providers = pservices and pservices.getContent("SN", True)

		for provider in providers:
			pservices = servicehandler.list(eServiceReference(provider[0]))
			slist = pservices and pservices.getContent("CN" if removenamefromsref else "SN", True)
			for sitem in slist:
				allproviders[sitem[0]] = provider[1]

	streamRelay = []
	if showstreamrelay:
		try:
			with open("/etc/enigma2/whitelist_streamrelay") as fd:
				streamRelay = [line.strip() for line in fd.readlines()]
		except OSError:
			pass

	bqservices = servicehandler.list(eServiceReference(sref))
	slist = bqservices and bqservices.getContent("CN" if removenamefromsref else "SN", True)

	opos = 0
	for sitem in slist:
		oldopos = opos
		sref = sitem[0]
		if calcpos and 'userbouquet' in sref:
			serviceslist = servicehandler.list(eServiceReference(sref))
			sfulllist = serviceslist and serviceslist.getContent("C", True)
			for sref in sfulllist:
				flags = int(sref.split(":")[1])
				hs = flags & 512  # eServiceReference.isInvisible
				sp = flags & 256  # eServiceReference.isNumberedMarker
				#sp = (sref[:7] == '1:832:D') or (sref[:7] == '1:832:1') or (sref[:6] == '1:320:')
				if not hs or sp:  # 512 is hidden service on sifteam image. Doesn't affect other images
					opos = opos + 1
					if not sp and flags & 64:  # eServiceReference.isMarker:
						opos = opos - 1

		showiptv = True
		if noiptv:
			if '4097:' in sref or '5002:' in sref or 'http%3a' in sref or 'https%3a' in sref:
				showiptv = False
		elif excludevod:  # no VOD
			if '/movie/' in sref and ('4097:' in sref or '5002:' in sref or 'http%3a' in sref or 'https%3a' in sref):  # is VOD
				showiptv = False

		flags = int(sitem[0].split(":")[1])
		sp = flags & 256  # (sitem[0][:7] == '1:832:D') or (sitem[0][:7] == '1:832:1') or (sitem[0][:6] == '1:320:')
		if sp or (not (flags & 512) and not (flags & 64)):
			pos = pos + 1
		if showiptv and (not flags & 512 or showhidden) and (showall or flags == 0):
			service = {}
			service['pos'] = 0 if (flags & 64) else pos
			sr = sitem[0]
			if calcpos:
				service['startpos'] = oldopos
			if picon:
				service['picon'] = getPicon(sr)
			service['servicename'] = sitem[1]
			service['servicereference'] = sr
			if not excludeprogram:
				service['program'] = int(service['servicereference'].split(':')[3], 16)
			if showproviders:
				if sitem[0] in allproviders:
					service['provider'] = allproviders[sitem[0]]
				else:
					service['provider'] = ""
			if flags == 0 and LCNDB:
				lcnref = sr.split(":")
				if len(lcnref) > 6:
					lcnref = lcnref[3:7]
					lcnref = ":".join(lcnref).upper()
					lcn = LCNDB.get(lcnref, "")
					if lcn:
						service['lcn'] = lcn
			if showstreamrelay:
				service['streamrelay'] = sr in streamRelay

			services.append(service)

	timeelapsed = datetime.now() - starttime
	return {
		"result": True,
		"processingtime": f"{timeelapsed}",
		"pos": pos,
		"services": services
	}


def getAllServices(mode, noiptv=False, nolastscanned=False, removenamefromsref=False, showall=True, showproviders=False, excludeprogram=False, excludevod=False, showstreamrelay=False):
	starttime = datetime.now()
	services = []
	if mode is None:
		mode = "tv"
	bouquets = getBouquets(mode)["bouquets"]
	pos = 0
	for bouquet in bouquets:
		if nolastscanned and 'LastScanned' in bouquet[0]:
			continue
		sv = getServices(sref=bouquet[0], showall=showall, showhidden=False, pos=pos, showproviders=showproviders, noiptv=noiptv, removenamefromsref=removenamefromsref, excludeprogram=excludeprogram, excludevod=excludevod, showstreamrelay=showstreamrelay)
		services.append({
			"servicereference": bouquet[0],
			"servicename": bouquet[1],
			"subservices": sv["services"]
		})
		pos = sv["pos"]

	timeelapsed = datetime.now() - starttime

	return {
		"result": True,
		"processingtime": f"{timeelapsed}",
		"services": services
	}


def getPlayableServices(sref, srefplaying):
	if sref == "":
		sref = f'{service_types_tv} FROM BOUQUET "bouquets.tv" ORDER BY bouquet'

	services = []
	servicecenter = eServiceCenter.getInstance()
	servicelist = servicecenter.list(eServiceReference(sref))
	servicelist2 = servicelist and servicelist.getContent('S') or []

	for service in servicelist2:
		if not int(service.split(":")[1]) & 512:  # 512 is hidden service on sifteam image. Doesn't affect other images
			service2 = {}
			service2['servicereference'] = service
			info = servicecenter.info(eServiceReference(service))
			service2['isplayable'] = info.isPlayable(eServiceReference(service), eServiceReference(srefplaying)) > 0
			services.append(service2)

	return {
		"result": True,
		"services": services
	}


def getPlayableService(sref, srefplaying):
	servicecenter = eServiceCenter.getInstance()
	info = servicecenter.info(eServiceReference(sref))
	return {
		"result": True,
		"service": {
			"servicereference": sref,
			"isplayable": info.isPlayable(eServiceReference(sref), eServiceReference(srefplaying)) > 0
		}
	}


def getSubServices(session):
	services = []
	service = session.nav.getCurrentService()
	if service is not None:
		services.append({
			"servicereference": service.info().getInfoString(iServiceInformation.sServiceref),
			"servicename": service.info().getName()
		})
		subservices = service.subServices()
		if subservices and subservices.getNumberOfSubservices() > 0:
			# print(subservices.getNumberOfSubservices())

			for i in list(range(subservices.getNumberOfSubservices())):
				subservice = subservices.getSubservice(i)
				services.append({
					"servicereference": subservice.toString(),
					"servicename": subservice.getName()
				})
	else:
		services.append({
			"servicereference": "N/A",
			"servicename": "N/A"
		})

	return {"services": services}


def getEventDesc(ref, idev, encode=True):
	ref = unquote(ref)
	epg = EPG()
	description = epg.getEventDescription(ref, eventid=idev, encode=encode, default="No description available")
	return {"description": description}


def getTimerEventStatus(starttime, endtime, sref, timers=None):
	# Check if an epgEvent has an associated timer. Unfortunately
	# we cannot simply check against timer.eit, because a timer
	# does not necessarily have one belonging to an epg event id.

	#catch ValueError
	endtime = endtime - 120  # TODO: find out what this 120 means
	timerlist = {}
	if not timers:
		timers = NavigationInstance.instance.RecordTimer.timer_list
	for timer in timers:
		if str(timer.service_ref) not in timerlist:
			timerlist[str(timer.service_ref)] = []
		timerlist[str(timer.service_ref)].append(timer)
	if sref in timerlist:
		for timer in timerlist[sref]:
			timerdetails = {}
			if timer.begin <= starttime and timer.end >= endtime:
				if timer.disabled:
					timerdetails = {
						'isEnabled': 0,
						'basicStatus': 'timer disabled'
					}
				else:
					timerdetails = {
						'isEnabled': 1,
						'isZapOnly': int(timer.justplay),
						'basicStatus': 'timer'
					}
				try:
					timerdetails['isAutoTimer'] = timer.isAutoTimer
				except AttributeError:
					timerdetails['isAutoTimer'] = 0
				return timerdetails

	return None


def getEvent(sref, eventid, encode=True):
	eventlookuptable = 'IBDTSENRWX'
	epg = EPG()
	event = epg.getEvent(sref, eventid, eventlookuptable)
	info = {}
	if event:
		info['id'] = event[0]
		info['begin_str'] = strftime("%H:%M", (localtime(event[1])))
		info['begin'] = event[1]
		info['end'] = strftime("%H:%M", (localtime(event[1] + event[2])))
		info['duration'] = event[2]
		info['title'] = filterName(event[3], encode)
		info['shortdesc'] = convertDesc(event[4], encode)
		info['longdesc'] = convertDesc(event[5], encode)
		info['channel'] = filterName(event[6], encode)
		info['sref'] = event[7]
		info['genre'], info['genreid'] = convertGenre(event[8])
		info['picon'] = getPicon(event[7])
		info['timer'] = getTimerEventStatus(event[1], event[1] + event[2], eventlookuptable, None)
		info['link'] = getIPTVLink(event[7])
	return {'event': info}


def getChannelEpg(ref, begintime=-1, endtime=-1, encode=True, nownext=False):
	ret = []
	ev = {}
	use_empty_ev = False
	if ref:
		ref = unquote(ref)

		# When querying EPG, we don't need URL; also getPicon doesn't like URL
		if "://" in ref:
			_ref = ":".join(ref.split(":")[:10]) + "::" + ref.split(":")[-1]
		else:
			_ref = ref

		picon = getPicon(_ref)
		epg = EPG()
		events = epg.getChannelEvents(_ref, begintime, endtime, encode, picon, nownext)
		if events:
			return {"events": events, "result": True}
# TODO do we need this?
#		else:
#			use_empty_ev = True
#			ev['sref'] = ref
	else:
		use_empty_ev = True
		ev['sref'] = ""

	if use_empty_ev:
		ev['id'] = 0
		ev['date'] = 0
		ev['begin'] = 0
		ev['begin_timestamp'] = 0
		ev['duration'] = 0
		ev['duration_sec'] = 0
		ev['end'] = 0
		ev['title'] = "N/A"
		ev['shortdesc'] = ""
		ev['sname'] = ""
		ev['longdesc'] = ""
		ev['tleft'] = 0
		ev['progress'] = 0
		ev['now_timestamp'] = 0
		ev['genre'] = ""
		ev['genreid'] = 0
		ret.append(ev)

	return {"events": ret, "result": True}


def getBouquetEpg(bqref, begintime=-1, endtime=None, encode=False):

	bqref = unquote(bqref)
	services = eServiceCenter.getInstance().list(eServiceReference(bqref))
	if not services:
		return {"events": [], "result": False}

	query = []

	services = services.getContent('S')

	if endtime:
		# prevent crash
		if endtime > 100000:
			endtime = -1
		for service in services:
			query.append((service, 0, begintime, endtime))
	else:
		for service in services:
			query.append((service, 0, begintime))

	epg = EPG()

	events = epg.getBouquetNowNextEpg(query, encode)

	return {"events": events, "result": True}


def getMultiChannelNowNextEpg(slist, encode=False):
	if not slist:
		return {"events": [], "result": False}

	if not isinstance(slist, list):
		slist = slist.split(",")

	query = []
	for service in slist:
		query.append((service, 0, -1))
		query.append((service, 1, -1))

	epg = EPG()
	events = epg.getBouquetNowNextEpg(query, encode)

	return {"events": events, "result": True}


def getBouquetNowNextEpg(bqref, nowornext, encode=False, showisplayable=False):
	bqref = unquote(bqref)
	services = eServiceCenter.getInstance().list(eServiceReference(bqref))
	if not services:
		return {"events": [], "result": False}

	playingref = None
	if showisplayable and NavigationInstance.instance:
		playingref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()

	isPlayable = []

	query = []

	services = services.getContent('S')
	services = [service for service in services if int(service.split(":", 2)[1]) & eServiceReference.isInvisible == 0]

	if showisplayable:
		if nowornext == EPG.NOW_NEXT:
			for service in services:
				query.append((service, 0, -1))
				query.append((service, 1, -1))
				if service.startswith("1:0:") and not ('http%3a' in service or 'https%3a' in service):
					if playingref:
						sref = eServiceReference(service)
						info = eServiceCenter.getInstance().info(sref)
						if info and info.isPlayable(sref, playingref):
							isPlayable.append(service)
						continue
					isPlayable.append(service)
		else:
			for service in services:
				query.append((service, nowornext, -1))
				if service.startswith("1:0:") and not ('http%3a' in service or 'https%3a' in service):
					if playingref:
						sref = eServiceReference(service)
						info = eServiceCenter.getInstance().info(sref)
						if info and info.isPlayable(sref, playingref):
							isPlayable.append(service)
						continue
					isPlayable.append(service)
	else:
		if nowornext == EPG.NOW_NEXT:
			for service in services:
				query.append((service, 0, -1))
				query.append((service, 1, -1))
		else:
			for service in services:
				query.append((service, nowornext, -1))

	epg = EPG()
	events = epg.getBouquetNowNextEpg(query, encode, alter=True, full=True)

	return {"events": events, "isplayable": isPlayable, "result": True}


def getNowNextEpg(sref, nowornext, encode=False):
	epg = EPG()
	events = epg.getNowNextEpg(unquote(sref), nowornext, encode)
	return {"events": events, "result": True}


# TODO: add sort options
def getSearchEpg(sstr, endtime=None, fulldesc=False, bouquetsonly=False, encode=False):
	ret = []
	ev = {}
	if config.OpenWebif.epg_encoding.value != 'utf-8':
		try:
			sstr = sstr.encode(config.OpenWebif.epg_encoding.value)
		except UnicodeEncodeError:
			pass

	epg = EPG()
	events = epg.search(sstr, fulldesc)
	if events is not None:
		# TODO : discuss #677
		# events.sort(key = lambda x: (x[1],x[6])) # sort by date,sname
		# events.sort(key = lambda x: x[1]) # sort by date
		if bouquetsonly:
			# collect service references from TV bouquets
			bsref = []
			for service in getAllServices('tv', removenamefromsref=True, showall=False, nolastscanned=True)['services']:
				bqservices = [service2['servicereference'] for service2 in service['subservices']]
				bsref += bqservices

		for event in events:
			if bouquetsonly and event[7] not in bsref:
				continue
			ev = {}
			ev['id'] = event[0]
			ev['date'] = f"{tstrings['day_' + strftime('%w', localtime(event[1]))]} {strftime(_('%d.%m.%Y'), localtime(event[1]))}"
			ev['begin_timestamp'] = event[1]
			ev['begin'] = strftime("%H:%M", (localtime(event[1])))
			ev['duration_sec'] = event[2]
			ev['duration'] = int(event[2] / 60)
			ev['end'] = strftime("%H:%M", (localtime(event[1] + event[2])))
			ev['title'] = filterName(event[3], encode)
			ev['shortdesc'] = convertDesc(event[4], encode)
			ev['longdesc'] = convertDesc(event[5], encode)
			ev['sref'] = event[7]
			ev['sname'] = filterName(event[6], encode)
			ev['picon'] = getPicon(event[7])
			ev['now_timestamp'] = None
			ev['genre'], ev['genreid'] = convertGenre(event[8])
			if endtime:
				# don't show events if begin after endtime
				if event[1] <= endtime:
					ret.append(ev)
			else:
				ret.append(ev)

			psref = parse_servicereference(event[7])
			ev['service_type'] = SERVICE_TYPE_LOOKUP.get(psref.get('service_type'), "UNKNOWN")
			nsi = psref.get('ns')
			ns = NS_LOOKUP.get(nsi, "DVB-S")
			if ns == "DVB-S":
				ev['ns'] = getOrb(nsi >> 16 & 0xFFF)
			else:
				ev['ns'] = ns

	return {"events": ret, "result": True}


def getSimilarEpg(ref, eventid, encode=False):

	picons = {}

	def _getPicon(sref):
		if sref in picons:
			return picons[sref]
		else:
			picons[sref] = getPicon(sref)
			return picons[sref]

	ref = unquote(ref)
	ret = []
	ev = {}
	epg = EPG()
	events = epg.similar(ref, eventid)
	if events is not None:
		# TODO : discuss #677
		# events.sort(key = lambda x: (x[1],x[6])) # sort by date,sname
		# events.sort(key = lambda x: x[1]) # sort by date
		for event in events:
			ev = {}
			ev['id'] = event[0]
			ev['date'] = f"{tstrings['day_' + strftime('%w', localtime(event[1]))]} {strftime(_('%d.%m.%Y'), localtime(event[1]))}"
			ev['begin_timestamp'] = event[1]
			ev['begin'] = strftime("%H:%M", (localtime(event[1])))
			ev['duration_sec'] = event[2]
			ev['duration'] = int(event[2] / 60)
			ev['end'] = strftime("%H:%M", (localtime(event[1] + event[2])))
			ev['title'] = filterName(event[3], encode)
			ev['shortdesc'] = convertDesc(event[4], encode)
			ev['longdesc'] = convertDesc(event[5], encode)
			ev['sref'] = event[7]
			ev['sname'] = filterName(event[6], encode)
			ev['picon'] = _getPicon(event[7])
			ev['now_timestamp'] = None
			ev['genre'], ev['genreid'] = convertGenre(event[8])
			ret.append(ev)

	return {"events": ret, "result": True}


def getMultiEpg(self, ref, begintime=-1, endtime=None, mode=1):
	# Fill out details for a timer matching an event
	def getTimerDetails(timer):
		basicstatus = 'timer'
		isenabled = 1
		isautotimer = -1
		if hasattr(timer, "isAutoTimer"):
			isautotimer = timer.isAutoTimer
		if timer.disabled:
			basicstatus = 'timer disabled'
			isenabled = 0
		txt = "REC" if timer.justplay == 0 else "ZAP"
		if timer.justplay == 1 and timer.always_zap == 1:
			txt = "R+Z"
		if isautotimer == 1:
			txt = "AT"
		if hasattr(timer, "ice_timer_id") and timer.ice_timer_id:
			txt = "Ice"
		timerdetails = {
				'isEnabled': isenabled,
				'isZapOnly': int(timer.justplay),
				'basicStatus': basicstatus,
				'isAutoTimer': isautotimer,
				'text': txt
			}
		return timerdetails

	ret = OrderedDict()
	channelnames = {}
	services = eServiceCenter.getInstance().list(eServiceReference(ref))
	if not services:
		return {"events": ret, "channelnames": channelnames, "result": False, "slot": None}

	srefs = services.getContent('S')
	epg = EPG()

	if begintime == -1:
		t = time()
		begintime = int(t)
		if config.epg.histminutes.value and config.OpenWebif.webcache.showepghistory.value:
			# limit begin time to 00:00 of the current day
			bt = localtime(t)
			begintime = int(mktime((bt.tm_year, bt.tm_mon, bt.tm_mday, 0, 0, 0, -1, -1, -1)))

	epgevents = epg.getMultiChannelEvents(srefs, begintime, endtime)
	offset = None
	picons = {}

	if epgevents is not None:
		# If a start time is requested, show all events in a 24 hour frame
		bt = localtime(begintime)
		offset = mktime((bt.tm_year, bt.tm_mon, bt.tm_mday, bt.tm_hour - bt.tm_hour % 2, 0, 0, -1, -1, -1))
		lastevent = offset + 86399

		# We want to display if an event is covered by a timer.
		# To keep the costs low for a nested loop against the timer list, we
		# partition the timers by service reference. For an event we then only
		# have to check the part of the timers that belong to that specific
		# service reference. Partition is generated here.
		timerlist = {}
		timers = self.session.nav.RecordTimer.timer_list + self.session.nav.RecordTimer.processed_timers
		for timer in timers:
			if timer.end >= begintime and timer.begin <= lastevent:
				if str(timer.service_ref) not in timerlist:
					timerlist[str(timer.service_ref)] = []
				timerlist[str(timer.service_ref)].append(timer)

		for event in epgevents:
			sref = event[4]
			# Cut description
			f = sref.rfind("::")
			if f != -1:
				sref = sref[:f + 1]

			end = event[1] + event[6]

			# If we can expect that events and timerlist are sorted by begin time,
			# we should be able to always pick the first timer from the timers list
			# and check if it belongs to the currently processed event.
			# Unfortunately it's not that simple: timers might overlap, so we
			# loop over the timers for the service reference of the event processed.
			# Here we can eliminate the head of the list, when we find a matching timer:
			# it only can contain timer entries older than the currently processed event.
			timer = None
			if sref in timerlist and len(timerlist[sref]) > 0:
				for i, first in enumerate(timerlist[sref]):
					if first.begin <= event[1] and end - 120 <= first.end:
						timer = getTimerDetails(first)
						timerlist[sref] = timerlist[sref][i:]
						break

			ev = {
				'id': event[0],
				'begin_timestamp': event[1],
				'title': event[2],
				'shortdesc': convertDesc(event[3]),
				'ref': event[4],
				'timer': timer
			}

			ev['timerStatus'] = timer['basicStatus'] if timer else ""

			if mode == 2:
				ev['duration'] = event[6]

			channel = filterName(event[5])

			if channel not in ret:
				if mode == 1:
					ret[channel] = [[], [], [], [], [], [], [], [], [], [], [], []]
				else:
					ret[channel] = [[]]

				picons[channel] = getPicon(event[4])
				channelnames[channel] = channel

			if mode == 1:
				slot = int((event[1] - offset) / 7200)

				if slot < 0:
					slot = 0
				if slot < 12 and event[1] < lastevent:
					ret[channel][slot].append(ev)
			else:
				ret[channel][0].append(ev)
	return {"events": ret, "channelnames": channelnames, "result": True, "picons": picons}


def getPicon(sname, pp=None, defaultpicon=True):

	PIC = "/picon/"
	DEFAULTPIC = "/images/default_picon.png"

	if pp is None:
		pp = PICON_PATH
	if pp is not None:
		# remove URL part
		if ("://" in sname) or ("%3a//" in sname) or ("%3A//" in sname):
			cname = unquote(sname.split(":")[-1])
			sname = unquote(sname)
			# sname = ":".join(sname.split(":")[:10]) -> old way
			sname = ":".join(sname.split("://")[:1])
			sname = GetWithAlternative(sname)
			cname = normalize('NFKD', cname)
			cname = sub('[^a-z0-9]', '', cname.replace('&', 'and').replace('+', 'plus').replace('*', 'star').replace(':', '').lower())
			# picon by channel name for URL
			if len(cname) > 0 and isfile(pathjoin(pp, cname + ".png")):
				return pathjoin(PIC, cname + ".png")
			if len(cname) > 2 and cname.endswith('hd') and isfile(pathjoin(pp, cname[:-2] + ".png")):
				return PIC + cname[:-2] + ".png"
			if len(cname) > 5:
				series = sub(r's[0-9]*e[0-9]*$', '', cname)
				if isfile(pathjoin(pp, series + ".png")):
					return pathjoin(PIC, series + ".png")

		sname = GetWithAlternative(sname)
		if sname is not None:
			pos = sname.rfind(':')
		else:
			return DEFAULTPIC
		cname = None
		if pos != -1:
			cname = ServiceReference(sname[:pos].rstrip(':')).getServiceName()
			sname = sname[:pos].rstrip(':').replace(':', '_') + ".png"
		filename = pathjoin(pp, sname)
		if isfile(filename):
			return pathjoin(PIC, sname)
		fields = sname.split('_', 8)
		if len(fields) > 7 and not fields[6].endswith("0000"):
			# remove "sub-network" from namespace
			fields[6] = fields[6][:-4] + "0000"
			sname = '_'.join(fields)
			filename = pathjoin(pp, sname)
			if isfile(filename):
				return pathjoin(PIC, sname)
		if len(fields) > 1 and fields[0] != '1':
			# fallback to 1 for other reftypes
			fields[0] = '1'
			sname = '_'.join(fields)
			filename = pathjoin(pp, sname)
			if isfile(filename):
				return pathjoin(PIC, sname)
		if len(fields) > 3 and fields[2] != '1':
			# fallback to 1 for tv services with nonstandard servicetypes
			fields[2] = '1'
			sname = '_'.join(fields)
			filename = pathjoin(pp, sname)
			if isfile(filename):
				return pathjoin(PIC, sname)
		if cname is not None:  # picon by channel name
			cname1 = filterName(cname).replace('/', '_') + ".png"
			if isfile(pathjoin(pp, cname1)):
				return pathjoin(PIC, cname1)
			cname = normalize('NFKD', cname)
			cname = sub('[^a-z0-9]', '', cname.replace('&', 'and').replace('+', 'plus').replace('*', 'star').lower())
			if len(cname) > 0:
				filename = pathjoin(pp, cname + ".png")
			if isfile(filename):
				return pathjoin(PIC, cname + ".png")
			if len(cname) > 2 and cname.endswith('hd') and isfile(pathjoin(pp, cname[:-2] + ".png")):
				return pathjoin(PIC, cname[:-2] + ".png")

	return DEFAULTPIC if defaultpicon else None


def getParentalControlList():
	if config.ParentalControl.configured.value:
		return {
			"result": True,
			"services": []
		}
	parentalControl.open()
	if config.ParentalControl.type.value == "whitelist":
		tservices = parentalControl.whitelist
	else:
		tservices = parentalControl.blacklist
	services = []
	if tservices is not None:
		for service in tservices:
			tservice = ServiceReference(service)
			services.append({
				"servicereference": service,
				"servicename": tservice.getServiceName()
			})
	return {
		"result": True,
		"type": config.ParentalControl.type.value,
		"services": services
	}


def getServiceRef(name, searchinbouquetsonly=False, bref=None):
	# TODO Radio
	# TODO bRef

	sfulllist = []
	servicehandler = eServiceCenter.getInstance()
	if searchinbouquetsonly:
		s_type = service_types_tv
		s_type2 = "bouquets.tv"
	#		if stype == "radio":
	#			s_type = service_types_radio
	#			s_type2 = "bouquets.radio"
		if bref is None:
			services = servicehandler.list(eServiceReference(f'{s_type} FROM BOUQUET "{s_type2}" ORDER BY bouquet'))
			bouquets = services and services.getContent("SN", True)
			bouquets = removeHiddenBouquets(bouquets)

		for bouquet in bouquets:
			serviceslist = servicehandler.list(eServiceReference(bouquet[0]))
			sfulllist = serviceslist and serviceslist.getContent("SN", True)
			for sv in sfulllist:
				if sv[1] == name:
					return {
						"result": True,
						"sRef": sv[0]
					}

	else:
		refstr = f'{service_types_tv} ORDER BY name'
		serviceslist = servicehandler.list(eServiceReference(refstr))
		sfulllist = serviceslist and serviceslist.getContent("SN", True)
		for sv in sfulllist:
			if sv[1] == name:
				return {
					"result": True,
					"sRef": sv[0]
				}

	return {
		"result": True,
		"sRef": ""
	}

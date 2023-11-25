##########################################################################
# OpenWebif: AjaxController
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

from os.path import exists, isdir
from time import mktime, localtime

from Components.config import config
from Components.SystemInfo import BoxInfo
from Tools.Directories import fileExists

from .models.services import getBouquets, getChannels, getAllServices, getSatellites, getProviders, getEventDesc, getSimilarEpg, getChannelEpg, getSearchEpg, getCurrentFullInfo, getMultiEpg, getEvent
from .models.info import getInfo
from .models.movies import getMovieList, getMovieInfo
from .models.timers import getTimers
from .models.config import getConfigs, getConfigsSections
from .models.stream import GetSession
from .base import BaseController
from .models.locations import getLocations
from .defaults import OPENWEBIFVER, getPublicPath, VIEWS_PATH, TRANSCODING, EXT_EVENT_INFO_SOURCE, HASAUTOTIMER, HASAUTOTIMERTEST, HASAUTOTIMERCHANGE, HASVPS, HASSERIES, ATSEARCHTYPES
from .utilities import getUrlArg, getEventInfoProvider


class AjaxController(BaseController):
	"""
	Ajax Web Controller
	"""

	def __init__(self, session, path=""):
		BaseController.__init__(self, path=path, session=session)

	def NoDataRender(self):
		"""
		ajax requests with no extra data
		"""
		return ['powerstate', 'message', 'myepg', 'radio', 'terminal', 'bqe', 'tv', 'satfinder']

	def P_foldertree(self, request):
		showbookmarks = getUrlArg(request, "showbookmarks", "false") != "false"
		return {"locations": getLocations()['locations'], "showbookmarks": showbookmarks}

	def P_edittimer(self, request):
		pipzap = getInfo()['timerpipzap']
		allow_duplicate = getInfo()['allow_duplicate']
		margins = getInfo()['timermargins']
		response = {"allow_duplicate": allow_duplicate, "pipzap": pipzap, "margins": margins}
		if margins:
			response["margin_before"] = config.recording.margin_before.value
			response["margin_after"] = config.recording.margin_after.value
			response["zap_margin_before"] = config.recording.zap_margin_before.value
			response["zap_margin_after"] = config.recording.zap_margin_after.value
		return response

	def P_current(self, request):
		return getCurrentFullInfo(self.session)

	def P_bouquets(self, request):
		stype = getUrlArg(request, "stype", "tv")
		bouq = getBouquets(stype)
		return {"bouquets": bouq['bouquets'], "stype": stype}

	def P_providers(self, request):
		stype = getUrlArg(request, "stype", "tv")
		prov = getProviders(stype)
		return {"providers": prov['providers'], "stype": stype}

	def P_satellites(self, request):
		stype = getUrlArg(request, "stype", "tv")
		sat = getSatellites(stype)
		return {"satellites": sat['satellites'], "stype": stype}

	# http://enigma2/ajax/channels?id=1%3A7%3A1%3A0%3A0%3A0%3A0%3A0%3A0%3A0%3AFROM%20BOUQUET%20%22userbouquet.favourites.tv%22%20ORDER%20BY%20bouquet&stype=tv
	def P_channels(self, request):
		stype = getUrlArg(request, "stype", "tv")
		idbouquet = getUrlArg(request, "id", "ALL")
		channels = getChannels(idbouquet, stype)
		channels['transcoding'] = TRANSCODING
		channels['type'] = stype
		channels['showpicons'] = config.OpenWebif.webcache.showpicons.value
		channels['showpiconbackground'] = config.OpenWebif.webcache.showpiconbackground.value
		channels['shownownextcolumns'] = config.OpenWebif.webcache.nownext_columns.value
		return channels

	# http://enigma2/ajax/eventdescription?idev=479&sref=1%3A0%3A19%3A1B1F%3A802%3A2%3A11A0000%3A0%3A0%3A0%3A
	def P_eventdescription(self, request):
		return getEventDesc(getUrlArg(request, "sref"), getUrlArg(request, "idev"))

	# http://enigma2/ajax/event?idev=479&sref=1%3A0%3A19%3A1B1F%3A802%3A2%3A11A0000%3A0%3A0%3A0%3A
	def P_event(self, request):
		event = getEvent(getUrlArg(request, "sref"), getUrlArg(request, "idev"))
		if event:
			event['event']['recording_margin_before'] = config.recording.margin_before.value
			event['event']['recording_margin_after'] = config.recording.margin_after.value
			event['at'] = HASAUTOTIMER
			event['transcoding'] = TRANSCODING
			event['moviedb'] = config.OpenWebif.webcache.moviedb.value if config.OpenWebif.webcache.moviedb.value else EXT_EVENT_INFO_SOURCE
			event['extEventInfoProvider'] = getEventInfoProvider(event['moviedb'])
		return event

	def P_about(self, request):
		info = {}
		info["owiver"] = OPENWEBIFVER
		return {"info": info}

	def P_boxinfo(self, request):
		info = getInfo(self.session, need_fullinfo=True)
		boxtype = info["boxtype"]
		info["boximage"] = f"{boxtype}_front.png"
		return info

	# http://enigma2/ajax/epgpop?sstr=test&bouquetsonly=1
	def P_epgpop(self, request):
		events = []
		timers = []
		sref = getUrlArg(request, "sref")
		eventid = getUrlArg(request, "eventid")
		sstr = getUrlArg(request, "sstr")
		if sref is not None:
			if eventid is not None:
				ev = getSimilarEpg(sref, eventid)
			else:
				ev = getChannelEpg(sref)
			events = ev["events"]
		elif sstr is not None:
			fulldesc = False
			if getUrlArg(request, "full") is not None:
				fulldesc = True
			bouquetsonly = False
			if getUrlArg(request, "bouquetsonly") is not None:
				bouquetsonly = True
			ev = getSearchEpg(sstr, None, fulldesc, bouquetsonly)
			events = sorted(ev["events"], key=lambda ev: ev['begin_timestamp'])
		at = False
		if len(events) > 0:
			t = getTimers(self.session)
			timers = t["timers"]
			at = HASAUTOTIMER
		if config.OpenWebif.webcache.theme.value:
			theme = config.OpenWebif.webcache.theme.value
		else:
			theme = 'original'
		moviedb = config.OpenWebif.webcache.moviedb.value if config.OpenWebif.webcache.moviedb.value else EXT_EVENT_INFO_SOURCE
		exteventinfoprovider = getEventInfoProvider(moviedb)

		return {"theme": theme, "events": events, "timers": timers, "at": at, "moviedb": moviedb, "extEventInfoProvider": exteventinfoprovider}

	# http://enigma2/ajax/epgdialog?sstr=test&bouquetsonly=1
	def P_epgdialog(self, request):
		return self.P_epgpop(request)

	def P_screenshot(self, request):
		box = {}
		box['brand'] = "dmm"
		displaybrand = BoxInfo.getItem("displaybrand")
		if displaybrand == 'Vu+':
			box['brand'] = "vuplus"
		elif displaybrand == 'GigaBlue':
			box['brand'] = "gigablue"
		elif displaybrand == 'Edision':
			box['brand'] = "edision"
		elif displaybrand == 'iQon':
			box['brand'] = "iqon"
		elif displaybrand == 'Technomate':
			box['brand'] = "techomate"
		elif fileExists("/proc/stb/info/azmodel"):
			box['brand'] = "azbox"

		return {"box": box,
				"high_resolution": config.OpenWebif.webcache.screenshot_high_resolution.value,
				"refresh_auto": config.OpenWebif.webcache.screenshot_refresh_auto.value,
				"refresh_time": config.OpenWebif.webcache.screenshot_refresh_time.value
				}

	def P_movies(self, request):
		directory = getUrlArg(request, "dirname")
		if directory is None:
			if config.OpenWebif.webcache.moviedir.value and isdir(config.OpenWebif.webcache.moviedir.value):
				directory = config.OpenWebif.webcache.moviedir.value
		elif isdir(directory):
			config.OpenWebif.webcache.moviedir.value = directory
			config.OpenWebif.webcache.moviedir.save()
		else:
			directory = None

		movies = getMovieList(request.args, directory=directory)
		movies['transcoding'] = TRANSCODING

		sorttype = config.OpenWebif.webcache.moviesort.value
		unsort = movies['movies']

		if sorttype == 'name':
			movies['movies'] = sorted(unsort, key=lambda k: k['eventname'])
		elif sorttype == 'named':
			movies['movies'] = sorted(unsort, key=lambda k: k['eventname'], reverse=True)
		elif sorttype == 'date':
			movies['movies'] = sorted(unsort, key=lambda k: k['recordingtime'])
		elif sorttype == 'dated':
			movies['movies'] = sorted(unsort, key=lambda k: k['recordingtime'], reverse=True)

		movies['sort'] = sorttype
		return movies

	def P_timers(self, request):

		timers = getTimers(self.session)
		unsort = timers['timers']

		sorttype = getUrlArg(request, "sort")
		if sorttype is None:
			return timers

		if sorttype == 'name':
			timers['timers'] = sorted(unsort, key=lambda k: k['name'])
		elif sorttype == 'named':
			timers['timers'] = sorted(unsort, key=lambda k: k['name'], reverse=True)
		elif sorttype == 'date':
			timers['timers'] = sorted(unsort, key=lambda k: k['begin'])
		else:
			timers['timers'] = sorted(unsort, key=lambda k: k['begin'], reverse=True)
			sorttype = 'dated'

		timers['sort'] = sorttype
		return timers

	# http://enigma2/ajax/tvradio
	# (`classic` interface only)
	def P_tvradio(self, request):
		epgmode = getUrlArg(request, "epgmode", "tv")
		if epgmode not in ["tv", "radio"]:
			epgmode = "tv"
		return {"epgmode": epgmode}

	def P_config(self, request):
		section = getUrlArg(request, "section", "Usage")
		return getConfigs(section)

	def P_settings(self, request):
		ret = {
			"result": True
		}
		ret['configsections'] = getConfigsSections()['sections']
		if config.OpenWebif.webcache.theme.value:
			if exists(getPublicPath('themes')):
				ret['themes'] = config.OpenWebif.webcache.theme.choices
			else:
				ret['themes'] = ['original', 'clear']
			ret['theme'] = config.OpenWebif.webcache.theme.value
		else:
			ret['themes'] = []
			ret['theme'] = 'original'
		if config.OpenWebif.webcache.moviedb.value:
			ret['moviedbs'] = config.OpenWebif.webcache.moviedb.choices
			ret['moviedb'] = config.OpenWebif.webcache.moviedb.value
		else:
			ret['moviedbs'] = []
			ret['moviedb'] = EXT_EVENT_INFO_SOURCE
		ret['zapstream'] = config.OpenWebif.webcache.zapstream.value
		ret['showpicons'] = config.OpenWebif.webcache.showpicons.value
		ret['showchanneldetails'] = config.OpenWebif.webcache.showchanneldetails.value
		ret['showiptvchannelsinselection'] = config.OpenWebif.webcache.showiptvchannelsinselection.value
		ret['screenshotchannelname'] = config.OpenWebif.webcache.screenshotchannelname.value
		ret['showallpackages'] = config.OpenWebif.webcache.showallpackages.value
		ret['showepghistory'] = config.OpenWebif.webcache.showepghistory.value
		ret['allowipkupload'] = config.OpenWebif.allow_upload_ipk.value
		ret['smallremotes'] = [(x, _('%s Style') % x.capitalize()) for x in config.OpenWebif.webcache.smallremote.choices]
		ret['smallremote'] = config.OpenWebif.webcache.smallremote.value
		loc = getLocations()
		ret['locations'] = loc['locations']
		if exists(VIEWS_PATH + "/responsive"):
			ret['responsivedesign'] = config.OpenWebif.webcache.responsive_enabled.value
		return ret

	# http://enigma2/ajax/multiepg
	def P_multiepg(self, request):
		epgmode = getUrlArg(request, "epgmode", "tv")
		if epgmode not in ["tv", "radio"]:
			epgmode = "tv"

		bouq = getBouquets(epgmode)
		bref = getUrlArg(request, "bref")
		if bref is None:
			bref = bouq['bouquets'][0][0]
		endtime = 1440
		begintime = -1
		day = 0
		week = 0
		wadd = 0
		_week = getUrlArg(request, "week")
		if _week is not None:
			try:
				week = int(_week)
				wadd = week * 7
			except ValueError:
				pass
		_day = getUrlArg(request, "day")
		if _day is not None:
			try:
				day = int(_day)
				if day > 0 or wadd > 0:
					now = localtime()
					begintime = int(mktime((now.tm_year, now.tm_mon, now.tm_mday + day + wadd, 0, 0, 0, -1, -1, -1)))
			except ValueError:
				pass
		mode = 1
		if config.OpenWebif.webcache.mepgmode.value:
			try:
				mode = int(config.OpenWebif.webcache.mepgmode.value)
			except ValueError:
				pass
		epg = getMultiEpg(self, bref, begintime, endtime, mode)
		epg['bouquets'] = bouq['bouquets']
		epg['bref'] = bref
		epg['day'] = day
		epg['week'] = week
		epg['mode'] = mode
		epg['epgmode'] = epgmode
		return epg

	def P_epgr(self, request):
		ret = {}
		ret['showiptvchannelsinselection'] = config.OpenWebif.webcache.showiptvchannelsinselection.value
		return ret

	def P_at(self, request):
		ret = {}
		ret['hasVPS'] = 1 if HASVPS else 0
		ret['hasSeriesPlugin'] = 1 if HASSERIES else 0
		ret['test'] = 1 if HASAUTOTIMERTEST else 0
		ret['hasChange'] = 1 if HASAUTOTIMERCHANGE else 0
		ret['allow_duplicate'] = getInfo()['allow_duplicate']
		ret['searchTypes'] = ATSEARCHTYPES

		if config.OpenWebif.autotimer_regex_searchtype.value:
			ret['searchTypes']['regex'] = 0

		loc = getLocations()
		ret['locations'] = loc['locations']
		ret['showiptvchannelsinselection'] = config.OpenWebif.webcache.showiptvchannelsinselection.value
		return ret

	def P_editmovie(self, request):
		sref = getUrlArg(request, "sRef")
		title = ""
		description = ""
		tags = ""
		resulttext = ""
		result = False
		if sref:
			mi = getMovieInfo(sref, newformat=True)
			result = mi["result"]
			if result:
				title = mi["title"]
				if title:
					description = mi["description"]
					tags = mi["tags"]
				else:
					result = False
					resulttext = "meta file not found"
			else:
				resulttext = mi["resulttext"]
		return {"title": title, "description": description, "sref": sref, "result": result, "tags": tags, "resulttext": resulttext}

	def P_epgplayground(self, request):
		TV = 'tv'
		RADIO = 'radio'

		ret = {
			'tvBouquets': getBouquets(TV),
			'tvChannels': getAllServices(TV),
			'radioBouquets': getBouquets(RADIO),
			'radioChannels': getAllServices(RADIO),
		}
		return {'data': ret}

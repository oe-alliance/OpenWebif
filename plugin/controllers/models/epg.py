##########################################################################
# OpenWebif: EPG
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


from datetime import datetime
from html import escape as html_escape
from time import localtime, strftime

from enigma import eEPGCache, eServiceCenter, eServiceReference

from ..utilities import debug, error, getGenreStringLong, toBinary, toString
from ..i18n import _, tstrings

CASE_SENSITIVE_QUERY = 0
CASE_INSENSITIVE_QUERY = 1
REGEX_QUERY = 2
MAX_RESULTS = 128
MATCH_EVENT_ID = 2
PREVIOUS_EVENT = -1
NOW_EVENT = 0
NEXT_EVENT = +1
TIME_NOW = -1

BOUQUET_NOWNEXT_FIELDS = "IBDCTSEWRNX"  # getBouquetNowNextEvents
BOUQUET_FIELDS = "IBDCTSEWRN"  # getBouquetEvents
MULTI_CHANNEL_FIELDS = "IBTSRND"     # getMultiChannelEvents
MULTI_NOWNEXT_FIELDS = "TBDCIESX"    # getMultiChannelNowNextEvents
SINGLE_CHANNEL_FIELDS = "IBDTSENCW"   # getChannelEvents;
SINGLE_CHANNEL_FIELDS_NN = "IBDTSENCWX"   # getChannelEvents now next;
SEARCH_FIELDS = "IBDTSENRW"   # search, findSimilarEvents


# TODO: load configgy stuff once


def getAlternativeChannels(service):
	alternativeservices = eServiceCenter.getInstance().list(eServiceReference(service))
	return alternativeservices and alternativeservices.getContent("S", True)


def GetWithAlternative(service, onlyfirst=True):
	if service.startswith("1:134:"):
		channels = getAlternativeChannels(service)
		if channels:
			return channels[0] if onlyfirst else channels
	return service if onlyfirst else None


def getBouquetServices(bqref, fields="SN"):
	bqservices = eServiceCenter.getInstance().list(eServiceReference(bqref))
	return bqservices.getContent(fields)


def convertGenre(val):
	if val is not None and len(val) > 0:
		val = val[0]
		if len(val) > 1 and val[0] > 0:
			gid = val[0] * 16 + val[1]
			return str(getGenreStringLong(val[0], val[1])).strip(), gid
	return "", 0


def getIPTVLink(ref):
	first = ref.split(":")[0]
	if first in ["4097", "5003", "5002", "5001"] or "%3A" in ref or "%3a" in ref:
		if "http" in ref:
			if ref.index("http") < ref.rindex(":"):
				ref = ref[:ref.rindex(":")]
			ref = ref[ref.index("http"):]
			ref = ref.replace("%3a", ":").replace("%3A", ":").replace("http://127.0.0.1:8088/", "")
			return ref
	return ""


def removeBadChars(val):
	return val.replace(b"\x1a", b"").replace(b"\xc2\x86", b"").replace(b"\xc2\x87", b"").replace(b"\xc2\x8a", b"")


# The fields fetched by filterName() and convertDesc() all need to be
# html-escaped, so do it there.
#

def filterName(name, encode=True):
	if name is not None:
		name = toString(removeBadChars(toBinary(name)))
		if encode is True:
			return html_escape(name, quote=True)
	return name


def convertDesc(val, encode=True):
	if val is not None:
		if encode is True:
			return html_escape(val, quote=True).replace("\x8a", "\n")
		else:
			# remove control chars
			val = removeBadChars(toBinary(val))
			return val.decode("utf_8", errors="ignore")
	return val


# TODO: move to utilities
class TimedProcess:
	def __init__(self):
		self.timetaken = 0

	def __enter__(self):
		self.tick = datetime.now()
		return self

	def __exit__(self, exc_type, exc_value, exc_tb):
		self.timetaken = datetime.now() - self.tick
		debug("Process took {}".format(self.timetaken), "EPG")

	# def getTimeTaken(self):
	# 	return self.timetaken


class EPG():
	NOW = 0
	NEXT = 1
	NOW_NEXT = 2

	def __init__(self):
		self._instance = eEPGCache.getInstance()
		self.doencode = False
		self.doalter = False
		self.doref = True
		self.currentpicon = ""
		self.currentsref = ""

	def search(self, querystring, searchfulldescription=False):
		querytype = eEPGCache.PARTIAL_TITLE_SEARCH
		if searchfulldescription:
			if hasattr(eEPGCache, "FULL_DESCRIPTION_SEARCH"):
				querytype = eEPGCache.FULL_DESCRIPTION_SEARCH
			elif hasattr(eEPGCache, "PARTIAL_DESCRIPTION_SEARCH"):
				querytype = eEPGCache.PARTIAL_DESCRIPTION_SEARCH

		criteria = (SEARCH_FIELDS, MAX_RESULTS, querytype, querystring, CASE_INSENSITIVE_QUERY)
		return self._instance.search(criteria)

	def getChannelEvents(self, sref, starttime, endtime, encode, picon, nownext):
		if not sref:
			error("A required parameter 'sRef' is missing!", "EPG")
			return []
		else:
			sref = str(sref)

		self.doencode = encode
		self.currentpicon = picon
		self.currentsref = sref
		if nownext:
			criteria = [SINGLE_CHANNEL_FIELDS_NN]
			criteria.append((sref, NOW_EVENT, -1))
			criteria.append((sref, NEXT_EVENT, -1))
		else:
			criteria = [SINGLE_CHANNEL_FIELDS, (sref, NOW_EVENT, starttime, endtime)]
		return self._instance.lookupEvent(criteria, self.convertEventSingle)

	def getMultiChannelEvents(self, srefs, starttime, endtime=None, fields=MULTI_CHANNEL_FIELDS):
		if not srefs:
			error("A required parameter [sRefs] is missing!", "EPG")
			return []

		criteria = [fields]

		for sref in srefs:
			sref = str(sref)
			if endtime:
				criteria.append((sref, NOW_EVENT, starttime, endtime))
			else:
				criteria.append((sref, NOW_EVENT, starttime))

		return self._instance.lookupEvent(criteria)

	def getMultiChannelNowNextEvents(self, srefs, fields=MULTI_NOWNEXT_FIELDS):
		if not srefs:
			error("A required parameter [sRefs] is missing!", "EPG")
			return []

		criteria = []

		for sref in srefs:
			sref = str(sref)
			criteria.append((sref, NOW_EVENT, TIME_NOW))
			criteria.append((sref, NEXT_EVENT, TIME_NOW))

		criteria.insert(0, fields)
		return self._instance.lookupEvent(criteria)

	def getCurrentEvent(self, sref):
		return self._instance.lookupEventTime(sref, TIME_NOW, 0)

	def getEventById(self, sref, eventid):
		eventid = int(eventid)
		return self._instance.lookupEventId(eServiceReference(sref), eventid)

	def getEventIdByTime(self, sref, eventtime):
		if not sref or not eventtime:
			error("A required parameter 'sRef' or eventTime is missing!", "EPG")
			return None
		event = self._instance.lookupEventTime(eServiceReference(sref), eventtime)
		eventid = event and event.getEventId()
		return eventid

	def getEvent(self, sref, eventid, eventlookuptable):
		events = self._instance.lookupEvent([eventlookuptable, (sref, 2, int(eventid))])
		if events:
			return events[0]
		return None

	def getEventDescription(self, sref, eventid, encode=True, default=""):
		if not sref or not eventid:
			error("A required parameter 'sRef' or eventId is missing!", "EPG")
			return None
		else:
			sref = str(sref)
			eventid = int(eventid)

		description = "No description available"
		event = self._instance.lookupEvent(["ESX", (sref, 2, eventid)])
		if event and event[0] and event[0][0] is not None:
			if len(event[0][0]) > 1:
				description = event[0][0]
			elif len(event[0][1]) > 1:
				description = event[0][1]
		return description and convertDesc(description, encode) or default  # TODO: translate

	def convertEvent(self, *event):
		encode = self.doencode
		alter = self.doalter
		ev = {}
		ev["id"] = event[0]
		if event[1]:
			ev["begin_timestamp"] = event[1]
			ev["duration_sec"] = event[2]
			ev["title"] = filterName(event[4], encode)
			ev["shortdesc"] = convertDesc(event[5], encode)
			ev["longdesc"] = convertDesc(event[6], encode)
			if alter and event[8] is not None:
				achannels = GetWithAlternative(event[8], False)
				if achannels:
					ev["asrefs"] = achannels
			ev["sref"] = event[8]
			ev["sname"] = filterName(event[9], encode)
			ev["now_timestamp"] = event[3]
			ev["remaining"] = (event[1] + event[2]) - event[3]
			ev["genre"], ev["genreid"] = convertGenre(event[7])
		else:
			ev["begin_timestamp"] = 0
			ev["duration_sec"] = 0
			ev["title"] = "N/A"
			ev["shortdesc"] = ""
			ev["longdesc"] = ""
			ev["sref"] = event[8]
			ev["sname"] = filterName(event[9])
			ev["now_timestamp"] = 0
			ev["remaining"] = 0
			ev["genre"] = ""
			ev["genreid"] = 0
		return ev

	def convertEventSingle(self, *event):
		encode = self.doencode

		ev = {
			"id": event[0],
			"sref": self.currentsref,
			"picon": self.currentpicon
		}

		if event[1]:
			ev["date"] = "%s %s" % (tstrings[("day_" + strftime("%w", (localtime(event[1]))))], strftime(_("%d.%m.%Y"), (localtime(event[1]))))
			ev["begin"] = strftime("%H:%M", (localtime(event[1])))
			ev["begin_timestamp"] = event[1]
			ev["duration"] = int(event[2] / 60)
			ev["duration_sec"] = event[2]
			ev["end"] = strftime("%H:%M", (localtime(event[1] + event[2])))
			ev["title"] = filterName(event[3], encode)
			ev["shortdesc"] = convertDesc(event[4], encode)
			ev["longdesc"] = convertDesc(event[5], encode)
			ev["sref"] = self.currentsref
			ev["sname"] = filterName(event[6], encode)
			ev["tleft"] = int(((event[1] + event[2]) - event[7]) / 60)
			if ev["duration_sec"] == 0:
				ev["progress"] = 0
			else:
				ev["progress"] = int(((event[7] - event[1]) * 100 / event[2]) * 4)
			ev["now_timestamp"] = event[7]
			ev["genre"], ev["genreid"] = convertGenre(event[8])
			return ev

	def similar(self, sref, eventid):
		return self._instance.search(("IBDTSENRW", 128, self._instance.SIMILAR_BROADCASTINGS_SEARCH, sref, eventid))

	def getNowNextEpg(self, sref, nowornext, encode):
		nn = 0 if nowornext == EPG.NOW else 1
		return self.getBouquetNowNextEpg([(sref, nn, -1)], encode)

	def getBouquetNowNextEpg(self, criteria, encode, alter=False, full=False):
		if full:
			criteria.insert(0, BOUQUET_NOWNEXT_FIELDS)
		else:
			criteria.insert(0, BOUQUET_FIELDS)
		self.doencode = encode
		self.doalter = alter
		return self._instance.lookupEvent(criteria, self.convertEvent)

	# /web/loadepg
	def load(self):
		self._instance.load()

	# /web/saveepg
	def save(self):
		self._instance.save()

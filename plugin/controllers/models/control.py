##########################################################################
# OpenWebif: control
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

from os import access, F_OK
from urllib.parse import unquote

from Components.config import config
from enigma import eServiceReference, eActionMap, eServiceCenter
from .services import getProtection
from ..defaults import DEFAULT_RCU, ROOTTV, ROOTRADIO, service_types_radio, service_types_tv
from Screens.InfoBar import InfoBar, MoviePlayer
import NavigationInstance

ENABLE_QPIP_PROCPATH = "/proc/stb/video/decodermode"

try:
	from enigma import setPrevAsciiCode
except ImportError:
	setPrevAsciiCode = None


def checkIsQPiP():
	if access(ENABLE_QPIP_PROCPATH, F_OK):
		data = ""
		with open(ENABLE_QPIP_PROCPATH, "r") as fd:
			data = fd.read()
		return data.strip() == "mosaic"
	return False


def getPlayingref(ref):
	playingref = None
	if NavigationInstance.instance:
		playingref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
	if not playingref:
		playingref = eServiceReference()
	return playingref


def isPlayableForCur(ref):
	info = eServiceCenter.getInstance().info(ref)
	return info and info.isPlayable(ref, getPlayingref(ref))


def zapInServiceList(service):
	infobarinstance = InfoBar.instance
	servicelist = infobarinstance.servicelist
	if config.usage.multibouquet.value:
		rootstrings = (ROOTTV, ROOTRADIO)
	else:
		rootstrings = (service_types_tv + ' FROM BOUQUET "userbouquet.favourites.tv" ORDER BY bouquet', service_types_radio + ' FROM BOUQUET "userbouquet.favourites.radio" ORDER BY bouquet')
	bouquet_found = False
	for bouquet_rootstr in rootstrings:
		servicelist.bouquet_root = eServiceReference(bouquet_rootstr)
		if bouquet_rootstr.find('radio') != -1:
			servicelist.setModeRadio()
		else:
			servicelist.setModeTv()
		bouquets = servicelist.getBouquetList()
		for bouquet in bouquets:
			reflist = []
			reflist = eServiceCenter.getInstance().list(bouquet[1])
			if reflist:
				while True:
					new_service = reflist.getNext()
					if not new_service.valid():  # check if end of list
						break
					if new_service.flags & (eServiceReference.isDirectory | eServiceReference.isMarker):
						continue
					if new_service == service:
						bouquet_found = True
						break
			if bouquet_found:
				break
		if bouquet_found:
			break
	if bouquet_found:
		bouquet = bouquet[1]
		if servicelist.getRoot() != bouquet:
			servicelist.clearPath()
			if servicelist.bouquet_root != bouquet:
				servicelist.enterPath(servicelist.bouquet_root)
			servicelist.enterPath(bouquet)
	else:
		servicelist.clearPath()
		servicelist.enterPath(service)
	servicelist.setCurrentSelection(service)  # select the service in servicelist
	servicelist.zap()


def zapService(session, sref, title="", stream=False):
	if checkIsQPiP():
		return {
			"result": False,
			"message": "Can not zap service in quad PiP mode."
		}

	# Must NOT unquote id here, breaks zap to streams
	service = eServiceReference(sref)

	if title:
		service.setName(title)
	else:
		title = sref

	isrecording = service.getPath()
	isrecording = isrecording and isrecording.startswith("/")

	if not isrecording:
		if config.ParentalControl.servicepinactive.value and config.OpenWebif.parentalenabled.value:
			if getProtection(service.toString()) != "0":
				return {
					"result": False,
					"message": "Service '%s' is blocked by parental Control" % title
				}

	# use mediaplayer for recording
	if isrecording:
		if isinstance(session.current_dialog, InfoBar):
			session.open(MoviePlayer, service)
		else:
			session.nav.playService(service)
	else:
		if isinstance(session.current_dialog, MoviePlayer):
			session.current_dialog.lastservice = service
			session.current_dialog.close()
		from Screens.Standby import inStandby
		if inStandby is None:
			zapInServiceList(service)
		else:
			if stream:
				stop_text = ""
				if session.nav.getCurrentlyPlayingServiceReference() and isPlayableForCur(service):
					session.nav.stopService()
					stop_text = ": simple stop current service"
				return {
					"result": True,
					"message": "For stream don't need zap in standby %s" % stop_text
				}
			else:
				session.nav.playService(service)

	return {
		"result": True,
		"message": "Active service is now '%s'" % title
	}


def remoteControl(key, rctype="", rcu=DEFAULT_RCU):
	remotetype = "dreambox remote control (native)"
	if rcu == "advanced":
		remotetype = "dreambox advanced remote control (native)"
	elif rcu == "keyboard":
		remotetype = "dreambox ir keyboard"

	amap = eActionMap.getInstance()

	if rctype == "text" and rcu != "":
		message = "RC command text not supported"
		result = False
		if setPrevAsciiCode:
			for k in unquote(rcu):
				setPrevAsciiCode(ord(k))
				amap.keyPressed(remotetype, 510, 0)
				amap.keyPressed(remotetype, 510, 1)
			message = "RC command text '%s' has been issued" % str(rcu)
			result = True
		return {
			"result": result,
			"message": message
		}
	elif rctype == "long":
		amap.keyPressed(remotetype, key, 0)
		amap.keyPressed(remotetype, key, 3)
	elif rctype == "ascii":
		amap.keyPressed(remotetype, key, 4)
	else:
		amap.keyPressed(remotetype, key, 0)

	amap.keyPressed(remotetype, key, 1)
	return {
		"result": True,
		"message": "RC command '%s' has been issued" % str(key)
	}


def setPowerState(session, state):
	from Screens.Standby import Standby, TryQuitMainloop, inStandby
	state = int(state)
	if state == 0:  # Toggle StandBy
		if inStandby is None:
			session.open(Standby)
		else:
			inStandby.Power()
	elif state == 1:  # DeepStandBy
		session.open(TryQuitMainloop, state)
	elif state == 2:  # Reboot
		session.open(TryQuitMainloop, state)
	elif state == 3:  # Restart Enigma
		session.open(TryQuitMainloop, state)
	elif state == 4:  # Wakeup
		if inStandby is not None:
			inStandby.Power()
	elif state == 5:  # Standby
		if inStandby is None:
			session.open(Standby)

	elif state == 6:
		print("HAHA")

	return {
		"result": True,
		"instandby": inStandby is not None
	}


def getStandbyState():
	from Screens.Standby import inStandby
	return {
		"result": True,
		"instandby": inStandby is not None
	}

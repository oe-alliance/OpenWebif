##########################################################################
# OpenWebif: serviceslist
##########################################################################
# Copyright (C) 2011 - 2025 jbleyel and E2OpenPlugins
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

from urllib.parse import unquote
from enigma import eDVBDB
from Components.NimManager import nimmanager
import Components.ParentalControl


def reloadServicesLists(mode):
	msgs = []
	mode = unquote(mode)
	modes = mode.split(",")
	for mode in modes:
		if mode in ("0", "2"):
			eDVBDB.getInstance().reloadBouquets()
			msgs.append("bouquets")
		if mode in ("0", "1"):
			eDVBDB.getInstance().reloadServicelist()
			msgs.append("lamedb")
		elif mode == "3":
			nimmanager.readTransponders()
			msgs.append("transponders")
		elif mode == "4":
			Components.ParentalControl.parentalControl.open()
			msgs.append("parentalcontrol white-/blacklist")
		elif mode == "5":  # whitelist_streamrelay
			try:
				from Screens.InfoBarGenerics import streamrelay
				streamrelay.reload()
				msgs.append("whitelist_streamrelay")
			except ImportError:
				pass
		elif mode == "6":  # autocam
			try:
				from Screens.InfoBarGenerics import autocam
				autocam.reload()
				msgs.append("autocam")
			except ImportError:
				pass

	if msgs:
		return {
			"result": True,
			"message": f"reloaded {' '.join(msgs)}"
		}
	else:
		return {
			"result": False,
			"message": "missing or wrong parameter mode [0 = lamedb and userbouqets, 1 = lamedb only, 2 = userbouqets only, 3 = transponders, 4 = parentalcontrol white/blacklist, 5 = whitelist_streamrelay, 6 = autocam"
		}

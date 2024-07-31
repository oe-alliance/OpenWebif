##########################################################################
# OpenWebif: defaults
##########################################################################
# Copyright (C) 2022 - 2024 jbleyel
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

from glob import glob
from re import search, MULTILINE
from os import symlink
from os.path import dirname, exists, isdir, isfile, join as pathjoin, islink
import sys

from Components.Language import language
from Components.config import config as comp_config
from Components.Network import iNetwork
from Components.SystemInfo import BoxInfo
from Tools.Directories import isPluginInstalled
from Plugins.Extensions.OpenWebif import __version__

OPENWEBIFVER = f"OWIF {__version__}"

PLUGIN_NAME = 'OpenWebif'
PLUGIN_DESCRIPTION = "OpenWebif Configuration"
PLUGIN_WINDOW_TITLE = PLUGIN_DESCRIPTION

PLUGIN_ROOT_PATH = dirname(dirname(__file__))
PUBLIC_PATH = PLUGIN_ROOT_PATH + '/public'
VIEWS_PATH = PLUGIN_ROOT_PATH + '/controllers/views'

sys.path.insert(0, PLUGIN_ROOT_PATH)

STB_LANG = language.getLanguage()

MOBILEDEVICE = False

DEBUG_ENABLED = False

MODEL = BoxInfo.getItem("model")

ROOTTV = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.tv" ORDER BY bouquet'

ROOTRADIO = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.radio" ORDER BY bouquet'

service_types_tv = '1:7:1:0:0:0:0:0:0:0:(type == 1) || (type == 17) || (type == 22) || (type == 25) || (type == 31) || (type == 134) || (type == 195) || (type == 211)'
service_types_radio = '1:7:2:0:0:0:0:0:0:0:(type == 2) || (type == 10)'


def setDebugEnabled(enabled):
	global DEBUG_ENABLED
	DEBUG_ENABLED = enabled


# Get transcoding feature
def getTranscoding():
	if isfile("/proc/stb/encoder/0/bitrate"):
		return isPluginInstalled("TranscodingSetup") or isPluginInstalled("TransCodingSetup") or isPluginInstalled("MultiTransCodingSetup")
	return False


def getExtEventInfoProvider():
	if STB_LANG[0:2] in ['ru', 'uk', 'lv', 'lt', 'et']:
		defaultvalue = 'Kinopoisk'
	elif STB_LANG[0:2] in ['cz', 'sk']:
		defaultvalue = 'CSFD'
	elif STB_LANG[0:5] in ['en_GB']:
		defaultvalue = 'TVguideUK'
	else:
		defaultvalue = 'IMDb'
	return defaultvalue


def setMobile(ismobile=False):
# TODO: do we need this?
	global MOBILEDEVICE
	MOBILEDEVICE = ismobile


def getViewsPath(file=""):
	global MOBILEDEVICE
	if (comp_config.OpenWebif.webcache.responsive_enabled.value or MOBILEDEVICE) and exists(f"{VIEWS_PATH}/responsive") and not (file.startswith('web/') or file.startswith('/web/')):
		return f"{VIEWS_PATH}/responsive/{file}"
	else:
		return f"{VIEWS_PATH}/{file}"


def getPublicPath(file=""):
	return f"{PUBLIC_PATH}/{file}"


def getPiconPath():

	# Alternative locations need to come first, as the default location always exists and needs to be the last resort
	# Sort alternative locations in order of likelyness that they are non-rotational media:
	# CF/MMC are always memory cards
	# USB can be memory stick or magnetic hdd or SSD, but stick is most likely
	# HDD can be magnetic hdd, SSD or even memory stick (if no hdd present) or a NAS
	PICON_PREFIXES = [
		"/media/cf/",
		"/media/mmc/",
		"/media/usb/",
		"/media/hdd/",
		"/usr/share/enigma2/",
		"/"
	]

	#: subfolders containing picons
	PICON_FOLDERS = ('owipicon', 'picon')

	#: extension of picon files
	# PICON_EXT = ".png"

	for prefix in PICON_PREFIXES:
		if isdir(prefix):
			for folder in PICON_FOLDERS:
				current = f"{prefix}{folder}/"
				if isdir(current):
					print(f"Current Picon Path : {current}")
					return current
#: TODO discuss
#					for item in os.listdir(current):
#						if isfile(current + item) and item.endswith(PICON_EXT):
#							PICONPATH = current
#							return PICONPATH

	return None


def refreshPiconPath():
	global PICON_PATH
	PICON_PATH = getPiconPath()


def getIP():
	ifaces = iNetwork.getConfiguredAdapters()
	if len(ifaces):
		ip_list = iNetwork.getAdapterAttribute(ifaces[0], "ip")  # use only the first configured interface
		if ip_list:
			return f"{ip_list[0]}.{ip_list[1]}.{ip_list[2]}.{ip_list[3]}"
	return None


PICON_PATH = getPiconPath()

EXT_EVENT_INFO_SOURCE = getExtEventInfoProvider()

TRANSCODING = getTranscoding()

VXGENABLED = isfile(getPublicPath("/vxg/media_player.pexe"))

WEBTV = VXGENABLED or TRANSCODING


def getOpenwebifPackageVersion():
	control = glob('/var/lib/opkg/info/*openwebif.control')
	version = 'unknown'
	if control:
		with open(control[0]) as file:
			lines = file.read()
			try:
				version = search(r'^Version:\s*(.*)', lines, MULTILINE).group(1)
			except AttributeError:
				pass
	return version


def getAutoTimer():
	try:
		from Plugins.Extensions.AutoTimer.AutoTimer import AutoTimer  # noqa: F401
		return True
	except ImportError:
		return False


def getAutoTimerChangeResource():
	if HASAUTOTIMER:
		try:
			from Plugins.Extensions.AutoTimer.AutoTimerResource import AutoTimerChangeResource  # noqa: F401
			return True
		except ImportError:
			return False
	else:
		return False


def getAutoTimerTestResource():
	if HASAUTOTIMER:
		try:
			from Plugins.Extensions.AutoTimer.AutoTimerResource import AutoTimerTestResource  # noqa: F401
			return True
		except ImportError:
			return False
	else:
		return False


def getVPSPlugin():
	try:
		from Plugins.SystemPlugins.vps import Vps  # noqa: F401
		return True
	except ImportError:
		return False


def getSeriesPlugin():
	try:
		from Plugins.Extensions.SeriesPlugin.plugin import Plugins  # noqa: F401
		return True
	except ImportError:
		return False


def getATSearchtypes():
	try:
		from Plugins.Extensions.AutoTimer.AutoTimer import typeMap
		return typeMap
	except ImportError:
		return {}


def getTextInputSupport():
	try:
		from enigma import setPrevAsciiCode
		return True
	except ImportError:
		return False


def getDefaultRcu():
	remotetype = "standard"
	if comp_config.misc.rcused.value == 0:
		remotetype = "advanced"
	else:
		try:
			# FIXME remove HardwareInfo
			from Tools.HardwareInfo import HardwareInfo
			if HardwareInfo().get_device_model() in ("xp1000", "formuler1", "formuler3", "et9000", "et9200", "hd1100", "hd1200"):
				remotetype = "advanced"
		except:  # nosec # noqa: E722
			print("[OpenWebif] wrong hw detection")
	return remotetype


def isSettingEnabled(setting):
	return "checked" if getattr(comp_config.OpenWebif.webcache, setting).value else ""


def showPiconBackground():
	return "checked" if comp_config.OpenWebif.webcache.showpiconbackground.value else ""


def themeMode():
	return comp_config.OpenWebif.responsive_themeMode.value


def skinColor():
	return comp_config.OpenWebif.responsive_skinColor.value


def showPicons():
	return "checked" if comp_config.OpenWebif.webcache.showpicons.value else ""


def getCustomCSS(css):
	cssfilename = f"openwebif-{css}.css"
	csslinkpath = f"{css + '/' if css == 'modern' else ''}css/{cssfilename}"
	csssrcpath = pathjoin("/etc/enigma2", cssfilename)
	try:
		if isfile(csssrcpath):
			csspath = pathjoin(PUBLIC_PATH, csslinkpath)
			if islink(csspath):
				return csslinkpath
			else:
				symlink(csssrcpath, csspath)
				return csslinkpath
	except OSError as err:
		print(f"[OpenWebif] Error getCustomCSS : {err}")
	return ""


def getLCNs():
	lcns = {}
	try:
		lines = []
		with open("/etc/enigma2/lcndb") as fd:
			lines = [line.strip().upper() for line in fd.readlines()]

		if lines and lines[0] == "#VERSION 2":
			del lines[0]
			for lcn in lines:
				lcnData = lcn.split(":")
				lcnKey = lcnData[7]
				if lcnKey == "0":
					lcnKey = lcnData[6]
				if lcnKey == "0":
					lcnKey = lcnData[5]
				lcns[f"{int(lcnData[0], 16):X}:{int(lcnData[1], 16):X}:{int(lcnData[2], 16):X}:{lcnData[3]}"] = int(lcnKey)
		else:
			for lcn in lines:
				lcnData = lcn.split(":")
				lcnKey = lcnData[:4]
				lcns[f"{int(lcnKey[3], 16):X}:{int(lcnKey[2], 16):X}:{int(lcnKey[1], 16):X}:{lcnKey[0]}"] = int(lcnData[4])
	except OSError:
		pass
	except Exception as err:
		print(f"[OpenWebif] Error parsing lcn db. {err}")
	return lcns


OPENWEBIFPACKAGEVERSION = getOpenwebifPackageVersion()

USERCSSCLASSIC = getCustomCSS("classic")

USERCSSMODERN = getCustomCSS("modern")

HASAUTOTIMER = getAutoTimer()

HASAUTOTIMERCHANGE = getAutoTimerChangeResource()

HASAUTOTIMERTEST = getAutoTimerTestResource()

HASVPS = getVPSPlugin()

HASSERIES = getSeriesPlugin()

ATSEARCHTYPES = getATSearchtypes()

TEXTINPUTSUPPORT = getTextInputSupport()

DEFAULT_RCU = getDefaultRcu()

GRABPIP = BoxInfo.getItem("ArchIsARM")

LCD = ("lcd" in MODEL) or ("lcd" in BoxInfo.getItem("displaytype"))

STREAMRELAY = hasattr(comp_config.misc, "softcam_streamrelay_url") and hasattr(comp_config.misc, "softcam_streamrelay_port")

LCNDB = getLCNs()

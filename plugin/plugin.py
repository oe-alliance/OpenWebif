##########################################################################
# OpenWebif: plugin
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

from Components.config import config, ConfigSubsection, ConfigInteger, ConfigYesNo, ConfigText, ConfigSelection
from Components.SystemInfo import BoxInfo
from Plugins.Plugin import PluginDescriptor
from Screens.Setup import Setup
from enigma import getDesktop
from .controllers.defaults import EXT_EVENT_INFO_SOURCE, getIP, setDebugEnabled, PLUGIN_NAME, PLUGIN_DESCRIPTION

from .httpserver import HttpdStart, HttpdStop, HttpdRestart
from .controllers.i18n import _

# not used redmond -> original , trontastic , ui-lightness
THEMES = [
	'original', 'base', 'black-tie', 'blitzer', 'clear', 'cupertino', 'dark-hive',
	'dot-luv', 'eggplant', 'excite-bike', 'flick', 'hot-sneaks', 'humanity',
	'le-frog', 'mint-choc', 'overcast', 'pepper-grinder', 'smoothness',
	'south-street', 'start', 'sunny', 'swanky-purse', 'ui-darkness', 'vader',
	'original-small-screen'
]

config.OpenWebif = ConfigSubsection()
config.OpenWebif.enabled = ConfigYesNo(default=True)
config.OpenWebif.identifier = ConfigYesNo(default=True)
config.OpenWebif.identifier_custom = ConfigYesNo(default=False)
config.OpenWebif.identifier_text = ConfigText(default="", fixed_size=False)
config.OpenWebif.port = ConfigInteger(default=80, limits=(1, 65535))
config.OpenWebif.streamport = ConfigInteger(default=8001, limits=(1, 65535))
config.OpenWebif.auth = ConfigYesNo(default=False)
config.OpenWebif.xbmcservices = ConfigYesNo(default=False)
config.OpenWebif.webcache = ConfigSubsection()

config.OpenWebif.webcache.collapsedmenus = ConfigText(default="", fixed_size=False)
config.OpenWebif.webcache.zapstream = ConfigYesNo(default=False)
config.OpenWebif.webcache.theme = ConfigSelection(default='original', choices=THEMES)
config.OpenWebif.webcache.moviesort = ConfigSelection(default='name', choices=['name', 'named', 'date', 'dated'])
config.OpenWebif.webcache.showpicons = ConfigYesNo(default=True)
config.OpenWebif.webcache.moviedb = ConfigSelection(default=EXT_EVENT_INFO_SOURCE, choices=['-', 'Kinopoisk', 'CSFD', 'TVguideUK', 'IMDb'])
config.OpenWebif.webcache.mepgmode = ConfigInteger(default=1, limits=(1, 2))
config.OpenWebif.webcache.showchanneldetails = ConfigYesNo(default=True)
config.OpenWebif.webcache.showiptvchannelsinselection = ConfigYesNo(default=True)
config.OpenWebif.webcache.screenshotchannelname = ConfigYesNo(default=False)
config.OpenWebif.webcache.showallpackages = ConfigYesNo(default=False)
config.OpenWebif.webcache.smallremote = ConfigSelection(default='new', choices=['new', 'ims'])
config.OpenWebif.webcache.screenshot_high_resolution = ConfigYesNo(default=True)
config.OpenWebif.webcache.screenshot_refresh_auto = ConfigYesNo(default=False)
config.OpenWebif.webcache.screenshot_refresh_time = ConfigInteger(default=30)
config.OpenWebif.webcache.moviedir = ConfigText(default="", fixed_size=False)

# HTTPS
config.OpenWebif.https_enabled = ConfigYesNo(default=False)
config.OpenWebif.https_port = ConfigInteger(default=443, limits=(1, 65535))
config.OpenWebif.https_auth = ConfigYesNo(default=True)
config.OpenWebif.https_clientcert = ConfigYesNo(default=False)
config.OpenWebif.parentalenabled = ConfigYesNo(default=False)
# Use service name for stream
config.OpenWebif.service_name_for_stream = ConfigYesNo(default=True)
# authentication for streaming
config.OpenWebif.auth_for_streaming = ConfigYesNo(default=False)
config.OpenWebif.no_root_access = ConfigYesNo(default=False)
config.OpenWebif.local_access_only = ConfigSelection(default=' ', choices=[' '])
config.OpenWebif.vpn_access = ConfigYesNo(default=False)
config.OpenWebif.allow_upload_ipk = ConfigYesNo(default=False)
# encoding of EPG data
config.OpenWebif.epg_encoding = ConfigSelection(default='utf-8', choices=['utf-8',
										'iso-8859-15',
										'iso-8859-1',
										'iso-8859-2',
										'iso-8859-3',
										'iso-8859-4',
										'iso-8859-5',
										'iso-8859-6',
										'iso-8859-7',
										'iso-8859-8',
										'iso-8859-9',
										'iso-8859-10',
										'iso-8859-16'])

config.OpenWebif.displayTracebacks = ConfigYesNo(default=False)
config.OpenWebif.playiptvdirect = ConfigYesNo(default=True)
config.OpenWebif.verbose_debug_enabled = ConfigYesNo(default=False)

setDebugEnabled(config.OpenWebif.verbose_debug_enabled.value)

MODERNTHEMES = [
	'supabright', ('city-lights', 'city lights'), ('neon-blackout', 'neon blackout')
]

COLORS = [
	'black', ('grey-darken-4', 'dark grey'), 'blue-grey', 'grey', 'red', 'pink', 'purple',
	('deep-purple', 'deep purple'), 'indigo', 'blue', ('light-blue', 'light blue'), 'cyan',
	'teal', 'green', ('light-green', 'light green'), 'lime', 'yellow', 'amber', 'orange',
	('deep-orange', 'deep orange'), 'brown', 'white'
]

config.OpenWebif.responsive_themeMode = ConfigSelection(default="supabright", choices=MODERNTHEMES)
config.OpenWebif.responsive_skinColor = ConfigSelection(default="black", choices=COLORS)

config.OpenWebif.webcache.nownext_columns = ConfigYesNo(default=False)
config.OpenWebif.webcache.showpiconbackground = ConfigYesNo(default=False)
config.OpenWebif.webcache.responsive_enabled = ConfigYesNo(default=False)
config.OpenWebif.webcache.epgsearch_only_bq = ConfigYesNo(default=True)
config.OpenWebif.webcache.epgsearch_full = ConfigYesNo(default=False)
config.OpenWebif.webcache.rcu_screenshot = ConfigYesNo(default=True)
config.OpenWebif.webcache.rcu_full_view = ConfigYesNo(default=False)
config.OpenWebif.webcache.minepglist = ConfigYesNo(default=False)
config.OpenWebif.webcache.mintimerlist = ConfigYesNo(default=False)
config.OpenWebif.webcache.minmovielist = ConfigYesNo(default=False)

config.OpenWebif.autotimer_regex_searchtype = ConfigYesNo(default=False)  # TODO


class OpenWebifConfig(Setup):
	def __init__(self, session):
		Setup.__init__(self, session, "openwebif", plugin="Extensions/OpenWebif")

		owif_protocol = "https" if config.OpenWebif.https_enabled.value else "http"
		owif_port = config.OpenWebif.https_port.value if config.OpenWebif.https_enabled.value else config.OpenWebif.port.value
		ip = getIP()
		if ip is None:
			ip = _("box_ip")

		ports = ":%d" % owif_port
		if (owif_protocol == "http" and owif_port == 80) or (owif_protocol == "https" and owif_port == 443):
			ports = ""

		self.footnote = "%s %s://%s%s" % (_("OpenWebif url:"), owif_protocol, ip, ports)

	def selectionChanged(self):
		Setup.selectionChanged(self)
		self.setFootnote(self.footnote)

	def keyOK(self):
		if config.OpenWebif.auth.value is not True:
			config.OpenWebif.auth_for_streaming.value = False

		if config.OpenWebif.https_enabled.value is not True:
			config.OpenWebif.https_clientcert.value = False

		if config.OpenWebif.enabled.value is True:
			HttpdRestart(global_session)
		else:
			HttpdStop(global_session)
		Setup.keyOK(self)


def confplug(session, **kwargs):
	session.open(OpenWebifConfig)


def IfUpIfDown(reason, **kwargs):
	if reason is True:
		HttpdStart(global_session)
	else:
		HttpdStop(global_session)


def startSession(reason, session):
	global global_session
	global_session = session
	HttpdStart(global_session)


def main_menu(menuid, **kwargs):
	if menuid == "network":
		return [(PLUGIN_NAME, confplug, "openwebif", 45)]
	else:
		return []


def Plugins(**kwargs):
	p = PluginDescriptor(where=[PluginDescriptor.WHERE_SESSIONSTART], fnc=startSession)
	p.weight = 100  # webif should start as last plugin
	result = [
		p,
		PluginDescriptor(where=[PluginDescriptor.WHERE_NETWORKCONFIG_READ], fnc=IfUpIfDown),
		]
	screenwidth = getDesktop(0).size().width()
	if BoxInfo.getItem("distro") in ("openatv"):
		result.append(PluginDescriptor(name=PLUGIN_NAME, description=_(PLUGIN_DESCRIPTION), where=PluginDescriptor.WHERE_MENU, fnc=main_menu))
	if screenwidth and screenwidth == 1920:
		result.append(PluginDescriptor(name=PLUGIN_NAME, description=_(PLUGIN_DESCRIPTION), icon="openwebifhd.png", where=[PluginDescriptor.WHERE_PLUGINMENU], fnc=confplug))
	else:
		result.append(PluginDescriptor(name=PLUGIN_NAME, description=_(PLUGIN_DESCRIPTION), icon="openwebif.png", where=[PluginDescriptor.WHERE_PLUGINMENU], fnc=confplug))
	return result

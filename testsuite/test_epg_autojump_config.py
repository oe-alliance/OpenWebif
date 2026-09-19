#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import sys
import types
import unittest

if not hasattr(os, 'statvfs'):
	os.statvfs = lambda *args: None

_orig_listdir = os.listdir
os.listdir = lambda path: _orig_listdir(path) if os.path.exists(path) else []

# Setup mock modules for Enigma2 components
components = types.ModuleType('Components')
components.__path__ = []
components_language = types.ModuleType('Components.Language')
components_config = types.ModuleType('Components.config')
components_config.ConfigBoolean = type('ConfigBoolean', (object,), {})
components_systeminfo = types.ModuleType('Components.SystemInfo')
components_systeminfo.BoxInfo = types.ModuleType('BoxInfo')
components_systeminfo.BoxInfo.getItem = lambda *args: ""
components_systeminfo.SystemInfo = {}

tools = types.ModuleType('Tools')
tools.__path__ = []
tools_directories = types.ModuleType('Tools.Directories')
tools_directories.resolveFilename = lambda *args: ""
tools_directories.SCOPE_PLUGINS = 0
tools_directories.SCOPE_PLAYLIST = 0
tools_directories.SCOPE_CONFIG = 0
tools_directories.fileExists = lambda *args: True
tools_directories.isPluginInstalled = lambda *args: False
tools.Directories = tools_directories

from importlib.machinery import ModuleSpec
from unittest.mock import MagicMock


class MockLoader(object):
	def create_module(self, spec):
		mod = MagicMock()
		mod.__name__ = spec.name
		mod.__path__ = []
		return mod

	def exec_module(self, module):
		pass


class MockFinder(object):
	@classmethod
	def find_spec(cls, fullname, path=None, target=None):
		if any(fullname.startswith(p) for p in ('Components.', 'Screens', 'Tools.', 'enigma', 'NavigationInstance', 'RecordTimer', 'ServiceReference', 'timer', 'Plugins')):
			return ModuleSpec(fullname, MockLoader(), is_package=True)
		return None


sys.meta_path.insert(0, MockFinder)

twisted = types.ModuleType('twisted')
twisted.__path__ = []
twisted.version = "20.0.0"
twisted_web = types.ModuleType('twisted.web')
twisted_web.__path__ = []
class FakeResource(object):
	def putChild(self, path, child):
		pass


twisted_web_resource = types.ModuleType('twisted.web.resource')
twisted_web_resource.Resource = FakeResource
twisted_web_resource.EncodingResourceWrapper = type('EncodingResourceWrapper', (object,), {})
twisted_web_server = types.ModuleType('twisted.web.server')
twisted_web_server.NOT_DONE_YET = 1
twisted_web_server.GzipEncoderFactory = type('GzipEncoderFactory', (object,), {})
twisted_web_http = types.ModuleType('twisted.web.http')
twisted_web_http.NOT_FOUND = 404
twisted_web_http.INTERNAL_SERVER_ERROR = 500
twisted_web_http.OK = 200
twisted_web_http.Request = type('Request', (object,), {})
twisted_web.resource = twisted_web_resource
twisted_web.server = twisted_web_server
twisted_web.http = twisted_web_http
twisted.web = twisted_web

twisted_internet = types.ModuleType('twisted.internet')
twisted_internet.defer = types.ModuleType('twisted.internet.defer')
twisted_internet.reactor = types.ModuleType('twisted.internet.reactor')
twisted.internet = twisted_internet

twisted_protocols = types.ModuleType('twisted.protocols')
twisted_protocols_basic = types.ModuleType('twisted.protocols.basic')
twisted_protocols_basic.FileSender = type('FileSender', (object,), {})
twisted_protocols.basic = twisted_protocols_basic
twisted.protocols = twisted_protocols

sys.modules['twisted'] = twisted
sys.modules['twisted.internet'] = twisted_internet
sys.modules['twisted.internet.defer'] = twisted_internet.defer
sys.modules['twisted.internet.reactor'] = twisted_internet.reactor
sys.modules['twisted.protocols'] = twisted_protocols
sys.modules['twisted.protocols.basic'] = twisted_protocols_basic
sys.modules['twisted.web'] = twisted_web
sys.modules['twisted.web.resource'] = twisted_web_resource
sys.modules['twisted.web.server'] = twisted_web_server
sys.modules['twisted.web.http'] = twisted_web_http

cheetah = types.ModuleType('Cheetah')
cheetah_template = types.ModuleType('Cheetah.Template')
cheetah_template.Template = type('Template', (object,), {})
cheetah.Template = cheetah_template
sys.modules['Cheetah'] = cheetah
sys.modules['Cheetah.Template'] = cheetah_template

class LanguageMock(object):
	def getLanguage(self):
		return "de_DE"

	def addCallback(self, cb):
		pass


class ConfigMock(object):
	def __init__(self):
		self.misc = MagicMock()
		self.misc.rcused.value = 1
		self.OpenWebif = MagicMock()


components_language.language = LanguageMock()
components_config.config = ConfigMock()
components.Language = components_language
components.config = components_config
sys.modules['Components'] = components
sys.modules['Components.Language'] = components_language
sys.modules['Components.config'] = components_config
sys.modules['Components.SystemInfo'] = components_systeminfo
sys.modules['Tools'] = tools
sys.modules['Tools.Directories'] = tools_directories
screens = types.ModuleType('Screens')
screens.__path__ = []
screens_infobar = types.ModuleType('Screens.InfoBar')
screens_infobar.InfoBar = types.ModuleType('InfoBar')
screens_infobar.InfoBar.instance = None
screens_infobar.MoviePlayer = type('MoviePlayer', (object,), {})
screens_channelselection = types.ModuleType('Screens.ChannelSelection')
screens_channelselection.service_types_tv = ""
screens_channelselection.service_types_radio = ""
screens_channelselection.FLAG_SERVICE_NEW_FOUND = 0
screens.InfoBar = screens_infobar
screens.ChannelSelection = screens_channelselection

sys.modules['Screens'] = screens
sys.modules['Screens.InfoBar'] = screens_infobar
sys.modules['Screens.ChannelSelection'] = screens_channelselection
class MockModule(types.ModuleType):
	def __getattr__(self, name):
		m = MagicMock()
		setattr(self, name, m)
		return m


enigma = MockModule('enigma')
enigma.eEnv = MockModule('eEnv')
enigma.eEnv.resolve = lambda *args: ""
sys.modules['enigma'] = enigma
sys.modules['twisted'] = twisted
sys.modules['twisted.web'] = twisted_web
sys.modules['twisted.web.resource'] = twisted_web_resource
sys.modules['twisted.web.server'] = twisted_web_server

sys.path.append(os.path.join(os.path.dirname(__file__), '../plugin'))

from controllers.i18n import tstrings


class ConfigItemMock(object):
	def __init__(self, val=False):
		self.value = val

	def save(self):
		pass


class EpgAutoJumpTestCase(unittest.TestCase):
	def test_i18n_keys(self):
		self.assertIn('epg_jump_now', tstrings)
		self.assertIn('epg_jump_active_service', tstrings)
		self.assertEqual(tstrings['epg_jump_now'], "Jump to current time in EPG")
		self.assertEqual(tstrings['epg_jump_active_service'], "Jump to active channel in EPG")

	def test_setwebconfig_epg_jump_keys(self):
		from controllers.web import WebController
		web = WebController(session=None)
		
		class FakeRequest(object):
			def __init__(self, key, val):
				self.args = {key.encode('utf-8'): [val.encode('utf-8')]}

		components_config.config.OpenWebif = ConfigMock()
		components_config.config.OpenWebif.webcache = ConfigMock()
		components_config.config.OpenWebif.webcache.epg_jump_now = ConfigItemMock(False)
		components_config.config.OpenWebif.webcache.epg_jump_active_service = ConfigItemMock(False)

		res1 = web.P_setwebconfig(FakeRequest("epg_jump_now", "true"))
		self.assertEqual(res1, {"result": True})
		self.assertTrue(components_config.config.OpenWebif.webcache.epg_jump_now.value)

		res2 = web.P_setwebconfig(FakeRequest("epg_jump_active_service", "1"))
		self.assertEqual(res2, {"result": True})
		self.assertTrue(components_config.config.OpenWebif.webcache.epg_jump_active_service.value)

		res3 = web.P_setwebconfig(FakeRequest("epg_jump_now", "false"))
		self.assertEqual(res3, {"result": True})
		self.assertFalse(components_config.config.OpenWebif.webcache.epg_jump_now.value)


if __name__ == '__main__':
	unittest.main()

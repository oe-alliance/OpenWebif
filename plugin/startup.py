from functools import partial
from importlib import import_module
from twisted.internet.threads import deferToThread

from .controllers.defaults import globalVars
from . import _  # noqa: F401 - Initialize language callbacks on the GUI thread.


class WebServerStartup:
	def __init__(self):
		self.session = None
		self.server = None
		self.queued = False
		self.initialized = False
		self.wanted = False

	def request(self, action, session):
		if session is not None:
			self.session = session
		self.wanted = action != "stop"
		if self.initialized:
			getattr(self.server, {"start": "HttpdStart", "stop": "HttpdStop", "restart": "HttpdRestart"}[action])(self.session)
		elif self.session is not None and not self.queued:
			self.queued = True
			try:
				from Tools.StartupTasks import startupTasks  # Optional E2 support; older images retain synchronous startup.
			except ImportError:
				self.initialize()
			else:
				prefix = f"{__package__}.controllers"
				steps = [partial(deferToThread, import_module, f"{prefix}.i18n")]
				# E2-dependent modules stay on the GUI thread, with event processing between imports.
				steps.extend(partial(import_module, f"{prefix}.{x}") for x in ("models.info", "base", "web", "root"))
				steps.append(self.initialize)
				startupTasks.add("OpenWebif", steps)

	def initialize(self):
		self.server = import_module(f"{__package__}.httpserver")
		globalVars.initSession()
		self.initialized = True
		if self.wanted:
			self.server.HttpdStart(self.session)
		from .controllers.models.info import updateShares  # Loaded by the preceding startup steps.
		updateShares()


webServerStartup = WebServerStartup()


def HttpdStart(session):
	webServerStartup.request("start", session)


def HttpdStop(session):
	webServerStartup.request("stop", session)


def HttpdRestart(session):
	webServerStartup.request("restart", session)

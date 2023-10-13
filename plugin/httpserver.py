##########################################################################
# OpenWebif: httpserver
##########################################################################
# Copyright (C) 2011 - 2023 jbleyel and E2OpenPlugins
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

import ipaddress
from importlib.util import spec_from_file_location, module_from_spec
from os import listdir, makedirs, remove, symlink
from os.path import exists, islink
from socket import has_ipv6
import sys
from OpenSSL import SSL
from OpenSSL import crypto
from twisted import version
from twisted.internet import reactor, ssl
from twisted.web import server, http, resource
from twisted.internet.error import CannotListenError

from enigma import eEnv
from Screens.MessageBox import MessageBox
from Components.config import config
from Components.Network import iNetwork

from .controllers.root import RootController
from .controllers.utilities import toString
from .sslcertificate import SSLCertificateGenerator, KEY_FILE, CERT_FILE, CA_FILE, CHAIN_FILE


global listener, server_to_stop, site, sslsite
listener = []

INET6 = "/proc/net/if_inet6"


def getAllNetworks():
	tempaddrs = []
	# Get all IP networks
	if exists(INET6):
		if has_ipv6 and version.major >= 12:
			proc = INET6
			for line in open(proc).readlines():
				# Skip localhost
				if line.startswith('00000000000000000000000000000001'):
					continue

				tmp = line.split()
				tmpaddr = str(ipaddress.ip_address(int(tmp[0], 16)))
				if tmp[2].lower() != "ff":
					tmpaddr = f"{tmpaddr}/{int(tmp[2].lower(), 16)}"
					tmpaddr = str(ipaddress.IPv6Network(str(tmpaddr), strict=False))

				tempaddrs.append(tmpaddr)
	# Crappy legacy IPv4 has no proc entry with clean addresses
	ifaces = iNetwork.getConfiguredAdapters()
	for iface in ifaces:
		# IPv4 and old fashioned netmask are served as silly arrays
		crap = iNetwork.getAdapterAttribute(iface, "ip")
		if not crap or len(crap) != 4:
			continue
		ip = '.'.join(str(x) for x in crap)
		netmask = str(sum([bin(int(x)).count('1') for x in iNetwork.getAdapterAttribute(iface, "netmask")]))
		ip = ip + "/" + netmask
		tmpaddr = str(ipaddress.IPv4Network(str(ip), strict=False))
		tempaddrs.append(tmpaddr)

	if tempaddrs == []:
		return None
	else:
		return tempaddrs


def verifyCallback(connection, x509, errnum, errdepth, ok):
	if not ok:
		print(f'[OpenWebif] Invalid cert from subject: {str(x509.get_subject())}')
		return False
	else:
		print(f'[OpenWebif] Successful cert authed as: {str(x509.get_subject())}')
	return True


def isOriginalWebifInstalled():
	pluginpath = eEnv.resolve('${libdir}/enigma2/python/Plugins/Extensions/WebInterface/plugin.py')
	if exists(pluginpath) or exists(pluginpath + "c"):
		return True

	return False


def buildRootTree(session):
	root = RootController(session)

	if not isOriginalWebifInstalled():
		# this is an hack! any better idea?
		origwebifpath = eEnv.resolve('${libdir}/enigma2/python/Plugins/Extensions/WebInterface')
		hookpath = eEnv.resolve('${libdir}/enigma2/python/Plugins/Extensions/OpenWebif/pluginshook.src')
		if not islink(origwebifpath + "/WebChilds/Toplevel.py"):
			print("[OpenWebif] hooking original webif plugins")

			cleanuplist = [
				"/__init__.py",
				"/__init__.pyo",
				"/__init__.pyc",
				"/WebChilds/__init__.py",
				"/WebChilds/__init__.pyo",
				"/WebChilds/__init__.pyc",
				"/WebChilds/External/__init__.py",
				"/WebChilds/External/__init__.pyo",
				"/WebChilds/External/__init__.pyc",
				"/WebChilds/Toplevel.py",
				"/WebChilds/Toplevel.pyo"
				"/WebChilds/Toplevel.pyc"
			]

			for cleanupfile in cleanuplist:
				if exists(origwebifpath + cleanupfile):
					remove(origwebifpath + cleanupfile)

			if not exists(origwebifpath + "/WebChilds/External"):
				makedirs(origwebifpath + "/WebChilds/External")
			open(origwebifpath + "/__init__.py", "w").close()
			open(origwebifpath + "/WebChilds/__init__.py", "w").close()
			open(origwebifpath + "/WebChilds/External/__init__.py", "w").close()

			symlink(hookpath, origwebifpath + "/WebChilds/Toplevel.py")

		# import modules
		print("[OpenWebif] loading external plugins...")
		from Plugins.Extensions.WebInterface.WebChilds.Toplevel import loaded_plugins
		if len(loaded_plugins) == 0:
			externals = listdir(origwebifpath + "/WebChilds/External")
			loaded = []
			for external in externals:
				if external.endswith(".py"):
					modulename = external[:-3]
				elif external.endswith(".pyc"):
					modulename = external[:-4]
				else:
					continue

				if modulename == "__init__":
					continue

				if modulename in loaded:
					continue

				loaded.append(modulename)
				try:
					spec = spec_from_file_location(modulename, origwebifpath + "/WebChilds/External/" + modulename + ".py")
					module = module_from_spec(spec)
					sys.modules[modulename] = module
					spec.loader.exec_module(module)
				except Exception as err:
					print(f"[OpenWebif] Error load external module '{modulename}'. {err}")
					# maybe there's only the compiled version
					try:
						spec = spec_from_file_location(modulename, origwebifpath + "/WebChilds/External/" + external)
						module = module_from_spec(spec)
						sys.modules[modulename] = module
						spec.loader.exec_module(module)
					except Exception as err:
						print(f"[OpenWebif] Error load external module '{modulename}'. {err}")

		if len(loaded_plugins) > 0:
			for plugin in loaded_plugins:
				root.putChild2(plugin[0], plugin[1])
				print(f"[OpenWebif] plugin '{plugin[2]}' loaded on path '/{plugin[0]}'")
		else:
			print("[OpenWebif] no plugins to load")
	return root


def HttpdStart(session):
	"""
	Helper class to start web server

	Args:
		session: (?) session object
	"""
	if config.OpenWebif.enabled.value is True:
		global listener, site, sslsite
		port = config.OpenWebif.port.value
		if listener is not None and len(listener) > 0:
			print("[OpenWebif] httpserver already started")
			return

		temproot = buildRootTree(session)
		root = AuthResource(session, temproot)
		site = server.Site(root)
		site.displayTracebacks = config.OpenWebif.displayTracebacks.value

		# start http webserver on configured port
		try:
			if has_ipv6 and exists(INET6) and version.major >= 12:
				# use ipv6
				listener.append(reactor.listenTCP(port, site, interface='::'))
			else:
				# ipv4 only
				listener.append(reactor.listenTCP(port, site))
			print(f"[OpenWebif] started on {port}")
			BJregisterService('http', port)
		except CannotListenError:
			print(f"[OpenWebif] failed to listen on Port {port}")

		if config.OpenWebif.https_clientcert.value is True and not exists(CA_FILE):
			# Disable https
			config.OpenWebif.https_enabled.value = False
			config.OpenWebif.https_enabled.save()
			# Inform the user
			session.open(MessageBox, "Cannot read CA certs for HTTPS access\nHTTPS access is disabled!", MessageBox.TYPE_ERROR)

		if config.OpenWebif.https_enabled.value is True:
			httpsport = config.OpenWebif.https_port.value
			installCertificates(session)
			# start https webserver on port configured port
			try:
				try:
					key = crypto.load_privatekey(crypto.FILETYPE_PEM, open(KEY_FILE, 'rt').read())
					cert = crypto.load_certificate(crypto.FILETYPE_PEM, open(CERT_FILE, 'rt').read())
					print(f"[OpenWebif] CHAIN_FILE = {CHAIN_FILE}")
					chain = None
					if exists(CHAIN_FILE):
						chain = [crypto.load_certificate(crypto.FILETYPE_PEM, open(CHAIN_FILE, 'rt').read())]
						print("[OpenWebif] ssl chain file found - loading")
					context = ssl.CertificateOptions(privateKey=key, certificate=cert, extraCertChain=chain)
				except:  # nosec # noqa: E722
					# THIS EXCEPTION IS ONLY CATCHED WHEN CERT FILES ARE BAD (look below for error)
					print("[OpenWebif] failed to get valid cert files. (It could occure bad file save or format, removing...)")
					# removing bad files
					if exists(KEY_FILE):
						remove(KEY_FILE)
					if exists(CERT_FILE):
						remove(CERT_FILE)
					# regenerate new ones
					installCertificates(session)
					context = ssl.DefaultOpenSSLContextFactory(KEY_FILE, CERT_FILE)

				if config.OpenWebif.https_clientcert.value is True:
					ctx = context.getContext()
					ctx.set_verify(
						SSL.VERIFY_PEER | SSL.VERIFY_FAIL_IF_NO_PEER_CERT,
						verifyCallback
						)
					ctx.load_verify_locations(CA_FILE)

				sslroot = AuthResource(session, temproot)
				sslsite = server.Site(sslroot)

				if has_ipv6 and exists(INET6) and version.major >= 12:
					# use ipv6
					listener.append(reactor.listenSSL(httpsport, sslsite, context, interface='::'))
				else:
					# ipv4 only
					listener.append(reactor.listenSSL(httpsport, sslsite, context))
				print(f"[OpenWebif] started on port:{httpsport}")
				BJregisterService('https', httpsport)
			except CannotListenError:
				print(f"[OpenWebif] failed to listen on Port: {httpsport}")
			except:  # nosec # noqa: E722
				print("[OpenWebif] failed to start https, disabling...")
				# Disable https
				config.OpenWebif.https_enabled.value = False
				config.OpenWebif.https_enabled.save()

		# Streaming requires listening on 127.0.0.1:80
		if port != 80:
			try:
				if has_ipv6 and exists(INET6) and version.major >= 12:
					# use ipv6
					# Dear Twisted devs: Learning English, lesson 1 - interface != address
					listener.append(reactor.listenTCP(80, site, interface='::1'))
					listener.append(reactor.listenTCP(80, site, interface='::ffff:127.0.0.1'))
				else:
					# ipv4 only
					listener.append(reactor.listenTCP(80, site, interface='127.0.0.1'))
				print("[OpenWebif] started stream listening on port 80")
			except CannotListenError:
				print("[OpenWebif] port 80 busy")


def HttpdStop(session):
	StopServer(session).doStop()


def HttpdRestart(session):
	StopServer(session, HttpdStart).doStop()


class AuthResource(resource.Resource):
	def __init__(self, session, root):
		resource.Resource.__init__(self)
		self.resource = root

	def noShell(self, user):
		if exists('/etc/passwd'):
			for line in open('/etc/passwd').readlines():
				line = line.strip()
				if line.startswith(user + ":") and (line.endswith(":/bin/false") or line.endswith(":/sbin/nologin")):
					return True
		return False

	def render(self, request):
		host = request.getHost().host
		peer = request.getClientIP()
		if peer is None:
			peer = request.transport.socket.getpeername()[0]

		if peer.startswith("::ffff:"):
			peer = peer.replace("::ffff:", "")

		if peer.startswith("fe80::") and "%" in peer:
			peer = peer.split("%")[0]

		if self.login(request.getUser(), request.getPassword(), peer) is False:
			request.setHeader('WWW-authenticate', f'Basic realm="OpenWebif"')
			errpage = resource.ErrorPage(http.UNAUTHORIZED, "Unauthorized", "401 Authentication required")
			return errpage.render(request)
		else:
			return self.resource.render(request)

	def getChildWithDefault(self, path, request):
		global site, sslsite
		session = request.getSession().sessionNamespaces
		host = request.getHost().host
		peer = request.getClientIP()
		host = toString(host)
		if request.getHeader("x-forwarded-for"):
			peer = request.getHeader("x-forwarded-for")

		if peer is None:
			peer = request.transport.socket.getpeername()[0]

		peer = toString(peer)
		if peer.startswith("::ffff:"):
			peer = peer.replace("::ffff:", "")

		if peer.startswith("fe80::") and "%" in peer:
			peer = peer.split("%")[0]

		# Handle all conditions where auth may be skipped/disabled

		# #1: Auth is disabled and access is from local network
		if (not request.isSecure() and config.OpenWebif.auth.value is False) or (request.isSecure() and config.OpenWebif.https_auth.value is False):
			networks = getAllNetworks()
			if networks:
				for network in networks:
					if ipaddress.ip_address(str(peer)) in ipaddress.ip_network(str(network), strict=False):
						return self.resource.getChildWithDefault(path, request)

		# #2: Auth is disabled and access is from private address space (Usually VPN) and access for VPNs has been granted
		if (not request.isSecure() and config.OpenWebif.auth.value is False) or (request.isSecure() and config.OpenWebif.https_auth.value is False):
			if config.OpenWebif.vpn_access.value is True and ipaddress.ip_address(str(peer)).is_private:
				return self.resource.getChildWithDefault(path, request)

		# #3: Access is from localhost and streaming auth is disabled - or - we only want to see our IPv6 (For inadyn-mt)
		if ((host == "localhost" or host == "127.0.0.1" or host == "::ffff:127.0.0.1" or host == "::1") and not (request.uri.startswith(b"/web/stream?StreamService=") and config.OpenWebif.auth_for_streaming.value) or request.uri == b"/web/getipv6"):
			return self.resource.getChildWithDefault(path, request)

		# #4: Web TV is accessing streams and "auths" by parent session id
		ruser = toString(request.getUser())
		rpw = toString(request.getPassword())
		if ruser == "-sid":
			sid = str(rpw)
			try:
				oldsession = site.getSession(sid).sessionNamespaces
				if "logged" in list(oldsession.keys()) and oldsession["logged"]:
					session = request.getSession().sessionNamespaces
					session["logged"] = True
					return self.resource.getChildWithDefault(path, request)
			except:  # nosec # noqa: E722
				pass

			try:
				oldsession = sslsite.getSession(sid).sessionNamespaces
				if "logged" in list(oldsession.keys()) and oldsession["logged"]:
					session = request.getSession().sessionNamespaces
					session["logged"] = True
					return self.resource.getChildWithDefault(path, request)
			except:  # nosec # noqa: E722
				pass

		# If we get to here, no exception applied
		# Either block with forbidden (If auth is disabled) ...
		if (not request.isSecure() and config.OpenWebif.auth.value is False) or (request.isSecure() and config.OpenWebif.https_auth.value is False):
			return resource.ErrorPage(http.FORBIDDEN, 'Forbidden', '403.6 IP address rejected')

		# ... or auth
		if "logged" in list(session.keys()) and session["logged"]:
			return self.resource.getChildWithDefault(path, request)

		if self.login(ruser, rpw, peer) is False:
			request.setHeader('WWW-authenticate', f'Basic realm="OpenWebif"')
			return resource.ErrorPage(http.UNAUTHORIZED, "Unauthorized", "401 Authentication required")
		else:
			session["logged"] = True
			session["user"] = ruser
			session["pwd"] = None
			if self.noShell(ruser):
				session["pwd"] = rpw
			return self.resource.getChildWithDefault(path, request)

	def login(self, user, passwd, peer):
		if user == "root" and config.OpenWebif.no_root_access.value:
			# Override "no root" for logins from local/private networks
			samenet = False
			networks = getAllNetworks()
			if networks:
				for network in networks:
					if ipaddress.ip_address(str(peer)) in ipaddress.ip_network(str(network), strict=False):
						samenet = True
			if not (ipaddress.ip_address(str(peer)).is_private or samenet):
				return False
		from crypt import crypt
		from pwd import getpwnam
		from spwd import getspnam
		cpass = None
		try:
			cpass = getpwnam(user)[1]
		except:  # nosec # noqa: E722
			return False
		if cpass:
			if cpass == 'x' or cpass == '*':
				try:
					cpass = getspnam(user)[1]
				except:  # nosec # noqa: E722
					return False
			return crypt(passwd, cpass) == cpass
		return False


class StopServer:
	"""
	Helper class to stop running web servers; we use a class here to reduce use
	of global variables. Resembles code prior found in HttpdStop et. al.
	"""
	server_to_stop = 0

	def __init__(self, session, callback=None):
		self.session = session
		self.callback = callback

	def doStop(self):
		global listener
		self.server_to_stop = 0
		for interface in listener:
			print(f"[OpenWebif] Stopping server on port:{str(interface.port)}")
			deferred = interface.stopListening()
			try:
				self.server_to_stop += 1
				deferred.addCallback(self.callbackStopped)
			except AttributeError:
				pass
		listener = []
		if self.server_to_stop < 1:
			self.doCallback()

	def callbackStopped(self, reason):
		self.server_to_stop -= 1
		if self.server_to_stop < 1:
			self.doCallback()

	def doCallback(self):
		if self.callback is not None:
			self.callback(self.session)

#
# create a self signed SSL certificate if necessary
#


def installCertificates(session):
	certgenerator = SSLCertificateGenerator()
	try:
		certgenerator.installCertificates()
	except OSError as e:
		# Disable https
		config.OpenWebif.https_enabled.value = False
		config.OpenWebif.https_enabled.save()
		# Inform the user
		session.open(MessageBox, "Cannot install generated SSL-Certifactes for https access\nHttps access is disabled!", MessageBox.TYPE_ERROR)
# BJ


def BJregisterService(protocol, port):
	try:
		from Plugins.Extensions.Bonjour.Bonjour import bonjour
		service = bonjour.buildService(protocol, port, 'OpenWebif')
		bonjour.registerService(service, True)
	except:  # nosec # noqa: E722
		pass
	try:
		from enigma import e2avahi_announce
		e2avahi_announce(None, f"_{protocol}._tcp", port)
	except:  # nosec # noqa: E722
		pass

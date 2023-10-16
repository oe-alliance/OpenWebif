##########################################################################
# OpenWebif: sslcertificate
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

from OpenSSL import crypto
from socket import gethostname
from time import time

from Tools.Directories import resolveFilename, SCOPE_CONFIG
from .controllers.utilities import toString

import os

CA_FILE = resolveFilename(SCOPE_CONFIG, "ca.pem")
KEY_FILE = resolveFilename(SCOPE_CONFIG, "key.pem")
CERT_FILE = resolveFilename(SCOPE_CONFIG, "cert.pem")
CHAIN_FILE = resolveFilename(SCOPE_CONFIG, "chain.pem")


class SSLCertificateGenerator:

	def __init__(self):
		# define some defaults
		self.type = crypto.TYPE_RSA
		self.bits = 2048
		self.digest = 'sha256'
		self.certsubjectoptions = {
			'O': 'Home',
			'OU': gethostname(),
			'CN': gethostname()
		}

	# generate and install a self signed SSL certificate if none exists
	def installCertificates(self):
		if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
			return
		keypair = self.__genKeyPair()
		certificate = self.__genCertificate(keypair)
		print("[OpenWebif] Install newly generated key pair and certificate")
		open(KEY_FILE, "w").write(toString(crypto.dump_privatekey(crypto.FILETYPE_PEM, keypair)))
		open(CERT_FILE, "w").write(toString(crypto.dump_certificate(crypto.FILETYPE_PEM, certificate)))

	# generate a key pair
	def __genKeyPair(self):
		keypair = crypto.PKey()
		keypair.generate_key(self.type, self.bits)
		return keypair

	# create a SSL certificate and sign it
	def __genCertificate(self, keypair):
		certificate = crypto.X509()
		subject = certificate.get_subject()
		for key, val in self.certsubjectoptions.items():
			setattr(subject, key, val)
		certificate.set_serial_number(int(time()))
		certificate.gmtime_adj_notBefore(0)
		certificate.gmtime_adj_notAfter(60 * 60 * 24 * 365 * 5)
		certificate.set_issuer(subject)
		certificate.set_pubkey(keypair)
		certificate.sign(keypair, self.digest)
		return certificate

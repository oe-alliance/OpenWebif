# LICENCE
#
# This File is part of the Webbouqueteditor plugin
# and licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported
# License if not stated otherwise in a files head. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc-sa/3.0/ or send a letter to Creative
# Commons, 559 Nathan Abbott Way, Stanford, California 94305, USA.

from os import remove
from os.path import exists, join as pathjoin
from re import compile
import tarfile
from .i18n import _
from enigma import eServiceReference, eServiceCenter, eDVBDB, eEnv
from Components.Sources.Source import Source
from Screens.ChannelSelection import MODE_TV, MODE_RADIO
from Components.config import config
from Screens.InfoBar import InfoBar
from ServiceReference import ServiceReference
from Components.ParentalControl import parentalControl
from Components.NimManager import nimmanager

from .defaults import ROOTTV, ROOTRADIO

ETCENIGMA = eEnv.resolve("${sysconfdir}/enigma2")
ETCTUXBOX = eEnv.resolve("${sysconfdir}/tuxbox")


class BouquetEditor(Source):

	ADD_BOUQUET = 0
	REMOVE_BOUQUET = 1
	MOVE_BOUQUET = 2
	ADD_SERVICE_TO_BOUQUET = 3
	REMOVE_SERVICE = 4
	MOVE_SERVICE = 5
	ADD_PROVIDER_TO_BOUQUETLIST = 6
	ADD_SERVICE_TO_ALTERNATIVE = 7
	REMOVE_ALTERNATIVE_SERVICES = 8
	TOGGLE_LOCK = 9
	BACKUP = 10
	RESTORE = 11
	RENAME_SERVICE = 12
	ADD_MARKER_TO_BOUQUET = 13
	IMPORT_BOUQUET = 14

	BACKUP_PATH = "/tmp"  # nosec
	BACKUP_FILENAME = "webbouqueteditor_backup.tar"

	def __init__(self, session, func=ADD_BOUQUET):
		Source.__init__(self)
		self.func = func
		self.session = session
		self.command = None
		self.bouquet_rootstr = ""
		self.result = (False, "one two three four unknown command")

	def noService(self):
		return (False, _("No service given!"))

	def noBouquet(self):
		return (False, _("No bouquet given!"))

	def noBouquetName(self):
		return (False, _("No bouquet name given!"))

	def handleCommand(self, cmd):
		print("[WebComponents.BouquetEditor] handleCommand with cmd = %s" % cmd)
		if self.func is self.ADD_BOUQUET:
			self.result = self.addToBouquet(cmd)
		elif self.func is self.MOVE_BOUQUET:
			self.result = self.moveBouquet(cmd)
		elif self.func is self.MOVE_SERVICE:
			self.result = self.moveService(cmd)
		elif self.func is self.REMOVE_BOUQUET:
			self.result = self.removeBouquet(cmd)
		elif self.func is self.REMOVE_SERVICE:
			self.result = self.removeService(cmd)
		elif self.func is self.ADD_SERVICE_TO_BOUQUET:
			self.result = self.addServiceToBouquet(cmd)
		elif self.func is self.ADD_PROVIDER_TO_BOUQUETLIST:
			self.result = self.addProviderToBouquetlist(cmd)
		elif self.func is self.ADD_SERVICE_TO_ALTERNATIVE:
			self.result = self.addServiceToAlternative(cmd)
		elif self.func is self.REMOVE_ALTERNATIVE_SERVICES:
			self.result = self.removeAlternativeServices(cmd)
		elif self.func is self.TOGGLE_LOCK:
			self.result = self.toggleLock(cmd)
		elif self.func is self.BACKUP:
			self.result = self.backupFiles(cmd)
		elif self.func is self.RESTORE:
			self.result = self.restoreFiles(cmd)
		elif self.func is self.RENAME_SERVICE:
			self.result = self.renameService(cmd)
		elif self.func is self.ADD_MARKER_TO_BOUQUET:
			self.result = self.addMarkerToBouquet(cmd)
		elif self.func is self.IMPORT_BOUQUET:
			self.result = self.importBouquet(cmd)
		else:
			self.result = (False, _("one two three four unknown command"))

	def addToBouquet(self, param):
		print("[WebComponents.BouquetEditor] addToBouquet with param = %s" % param)
		bname = param["name"]
		if bname is None:
			return self.noBouquetName()
		mode = MODE_TV  # init
		if "mode" in param and param["mode"] is not None:
			mode = int(param["mode"])
		return self.addBouquet(bname, mode, None)

	def addBouquet(self, bname, mode, services):
		if config.usage.multibouquet.value:
			mutablebouquetlist = self.getMutableBouquetList(mode)
			if mutablebouquetlist:
				prefix = "userbouquet"
				name, filename = self.buildBouquetID(bname, prefix, mode)
				if mode == MODE_TV:
					bname += " (TV)"
					sref = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET \"%s.%s.tv\" ORDER BY bouquet' % (prefix, name)
				else:
					bname += " (Radio)"
					sref = '1:7:2:0:0:0:0:0:0:0:FROM BOUQUET \"%s.%s.radio\" ORDER BY bouquet' % (prefix, name)
				new_bouquet_ref = eServiceReference(sref)
				if not mutablebouquetlist.addService(new_bouquet_ref):
					mutablebouquetlist.flushChanges()
					eDVBDB.getInstance().reloadBouquets()
					mutablebouquet = self.getMutableList(new_bouquet_ref)
					if mutablebouquet:
						mutablebouquet.setListName(bname)
						if services is not None:
							for service in services:
								if mutablebouquet.addService(service):
									print("add %s to new bouquet failed" % service.toString())
						mutablebouquet.flushChanges()
						self.setRoot(self.bouquet_rootstr)
						return (True, _("Bouquet %s created.") % bname)
					else:
						return (False, _("Get mutable list for new created bouquet failed!"))

				else:
					return (False, _("Bouquet %s already exists.") % bname)
			else:
				return (False, _("Bouquetlist is not editable!"))
		else:
			return (False, _("Multi-Bouquet is not enabled!"))

	def addProviderToBouquetlist(self, param):
		print("[WebComponents.BouquetEditor] addProviderToBouquet with param = %s" % param)
		refstr = param["sProviderRef"]
		if refstr is None:
			return (False, _("No provider given!"))
		mode = MODE_TV  # init
		if "mode" in param and param["mode"] is not None:
			mode = int(param["mode"])
		ref = eServiceReference(refstr)
		provider = ServiceReference(ref)
		providername = provider.getServiceName()
		servicehandler = eServiceCenter.getInstance()
		services = servicehandler.list(provider.ref)
		return self.addBouquet(providername, mode, services and services.getContent('R', True))

	def removeBouquet(self, param):
		print("[WebComponents.BouquetEditor] removeBouquet with param = %s" % param)
		refstr = sref = param["sBouquetRef"]
		if refstr is None:
			return self.noBouquetName()
		mode = MODE_TV  # init
		if "mode" in param and param["mode"] is not None:
			mode = int(param["mode"])

		# only when removing alternative
		bouquet_root = param["BouquetRefRoot"] if "BouquetRefRoot" in param else None
		pos = refstr.find('FROM BOUQUET "')
		filename = None
		if pos != -1:
			refstr = refstr[pos + 14:]
			pos = refstr.find('"')
			if pos != -1:
				filename = pathjoin(ETCENIGMA, refstr[:pos])
		ref = eServiceReference(sref)
		bouquetname = self.getName(ref)
		if not bouquetname:
			bouquetname = filename
		if bouquet_root:
			mutablelist = self.getMutableList(eServiceReference(bouquet_root))
		else:
			mutablelist = self.getMutableBouquetList(mode)

		if ref.valid() and mutablelist is not None:
			if not mutablelist.removeService(ref):
				mutablelist.flushChanges()
				self.setRoot(self.bouquet_rootstr)
			else:
				return (False, _("Bouquet %s removed failed.") % filename)
		else:
			return (False, _("Bouquet %s removed failed, sevicerefence or mutable list is not valid.") % filename)
		try:
			if filename is not None:
				if not exists(filename + '.del'):
					remove(filename)
				return (True, _("Bouquet %s deleted.") % bouquetname)
		except OSError:
			return (False, _("Error: Bouquet %s could not deleted, OSError.") % filename)

	def moveBouquet(self, param):
		print("[WebComponents.BouquetEditor] moveBouquet with param = %s" % param)
		sbouquetref = param["sBouquetRef"]
		if sbouquetref is None:
			return self.noBouquetName()
		mode = MODE_TV  # init
		if "mode" in param and param["mode"] is not None:
			mode = int(param["mode"])
		position = None
		if "position" in param and param["position"] is not None:
			position = int(param["position"])
		if position is None:
			return (False, _("No position given!"))
		mutablebouquetlist = self.getMutableBouquetList(mode)
		if mutablebouquetlist is not None:
			ref = eServiceReference(sbouquetref)
			mutablebouquetlist.moveService(ref, position)
			mutablebouquetlist.flushChanges()
			self.setRoot(self.bouquet_rootstr)
			return (True, _("Bouquet %s moved.") % self.getName(ref))
		else:
			ref = eServiceReference(sbouquetref)
			return (False, _("Bouquet %s can not be moved.") % self.getName(ref))

	def removeService(self, param):
		print("[WebComponents.BouquetEditor] removeService with param = %s" % param)
		sbouquetref = param["sBouquetRef"]
		if sbouquetref is None:
			return self.noBouquet()
		sref = param["sRef"] if "sRef" in param else None
		if sref is None:
			return self.noService()
		ref = eServiceReference(sref)
		if ref.flags & eServiceReference.isGroup:  # check if service is an bouquet, if so delete it with removeBouquet
			new_param = {}
			new_param["sBouquetRef"] = sref
			new_param["mode"] = None  # of no interest when passing BouquetRefRoot
			new_param["BouquetRefRoot"] = sbouquetref
			returnvalue = self.removeBouquet(new_param)
			if returnvalue[0]:
				return (True, _("Service %s removed.") % self.getName(ref))
		else:
			bouquetref = eServiceReference(sbouquetref)
			mutablebouquetlist = self.getMutableList(bouquetref)
			if mutablebouquetlist is not None:
				if not mutablebouquetlist.removeService(ref):
					mutablebouquetlist.flushChanges()
					self.setRoot(sbouquetref)
					return (True, _("Service %s removed from bouquet %s.") % (self.getName(ref), self.getName(bouquetref)))
		return (False, _("Service %s can not be removed.") % self.getName(ref))

	def moveService(self, param):
		print("[WebComponents.BouquetEditor] moveService with param = %s" % param)
		sbouquetref = param["sBouquetRef"]
		if sbouquetref is None:
			return self.noBouquet()
		sref = param["sRef"] if "sRef" in param else None
		if sref is None:
			return self.noService()
		position = None
		if "position" in param and param["position"] is not None:
			position = int(param["position"])
		if position is None:
			return (False, _("No position given!"))
		mutablebouquetlist = self.getMutableList(eServiceReference(sbouquetref))
		if mutablebouquetlist is not None:
			ref = eServiceReference(sref)
			mutablebouquetlist.moveService(ref, position)
			mutablebouquetlist.flushChanges()
			self.setRoot(sbouquetref)
			return (True, _("Service %s moved.") % self.getName(ref))
		return (False, _("Service can not be moved."))

	def addServiceToBouquet(self, param):
		print("[WebComponents.BouquetEditor] addService with param = %s" % param)
		sbouquetref = param["sBouquetRef"]
		if sbouquetref is None:
			return self.noBouquet()
		sref = param["sRef"] if "sRef" in param else None
		srefurl = False
		sname = param["Name"] if "Name" in param else None
		ssubname = param["SubName"] if "SubName" in param else None
		if sref is None and "sRefUrl" in param:
			# check IPTV
			if param["sRefUrl"] is not None and sname is not None:
				sref = param["sRefUrl"]
				srefurl = True
		elif sref is None and ssubname is None:
			return self.noService()
		srefbefore = eServiceReference()
		if "sRefBefore" in param and param["sRefBefore"] is not None:
			srefbefore = eServiceReference(param["sRefBefore"])
		if ssubname is not None:
			mode = MODE_TV
			if "mode" in param and param["mode"] is not None:
				mode = int(param["mode"])
			sname = ssubname
			srefurl = False
			prefix = "subbouquet"
			name, filename = self.buildBouquetID(sname, prefix, mode)
			if mode == MODE_TV:
				sref = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET \"%s.%s.tv\" ORDER BY bouquet' % (prefix, name)
			else:
				sref = '1:7:2:0:0:0:0:0:0:0:FROM BOUQUET \"%s.%s.radio\" ORDER BY bouquet' % (prefix, name)
			# create bouquet file
			try:
				with open(filename, "w") as fd:
					fd.write("#NAME %s\n" % sname)
			except OSError as err:
				print("Error %d: Unable to create file '%s'!  (%s)" % (err.errno, filename, err.strerror))

		bouquetref = eServiceReference(sbouquetref)
		mutablebouquetlist = self.getMutableList(bouquetref)
		if mutablebouquetlist is not None:
			if srefurl:
				ref = eServiceReference(4097, 0, sref)
			else:
				ref = eServiceReference(sref)
			if sname:
				ref.setName(sname)
			if not mutablebouquetlist.addService(ref, srefbefore):
				mutablebouquetlist.flushChanges()
				self.setRoot(sbouquetref)
				return (True, _("Service %s added.") % self.getName(ref))
			else:
				bouquetname = self.getName(bouquetref)
				return (False, _("Service %s already exists in bouquet %s.") % (self.getName(ref), bouquetname))
		return (False, _("This service can not be added."))

	def addMarkerToBouquet(self, param):
		print("[WebComponents.BouquetEditor] addMarkerToBouquet with param = %s" % param)
		sbouquetref = param["sBouquetRef"]
		if sbouquetref is None:
			return self.noBouquet()
		name = param["Name"] if "Name" in param else None
		if name is None and "SP" not in param:
			return (False, _("No marker-name given!"))
		srefbefore = eServiceReference()
		if "sRefBefore" in param and param["sRefBefore"] is not None:
			srefbefore = eServiceReference(param["sRefBefore"])
		bouquet_ref = eServiceReference(sbouquetref)
		mutablebouquetlist = self.getMutableList(bouquet_ref)
		cnt = 0
		while mutablebouquetlist:
			if name is None:
				service_str = '1:832:D:%d:0:0:0:0:0:0:' % cnt
			else:
				service_str = '1:64:%d:0:0:0:0:0:0:0::%s' % (cnt, name)
			ref = eServiceReference(service_str)
			if not mutablebouquetlist.addService(ref, srefbefore):
				mutablebouquetlist.flushChanges()
				self.setRoot(sbouquetref)
				return (True, _("Marker added."))
			cnt += 1
		return (False, _("Internal error!"))

	def renameService(self, param):
		sref = param["sRef"] if "sRef" in param else None
		if sref is None:
			return self.noService()
		sname = param["newName"] if "newName" in param else None
		if sname is None:
			return (False, _("No new servicename given!"))
		sbouquetref = param["sBouquetRef"] if "sBouquetRef" in param else None
		cur_ref = eServiceReference(sref)
		if cur_ref.flags & eServiceReference.mustDescent:
			# bouquets or alternatives can be renamed with setListName directly
			mutablebouquetlist = self.getMutableList(cur_ref)
			if mutablebouquetlist:
					mutablebouquetlist.setListName(sname)
					mutablebouquetlist.flushChanges()
					if sbouquetref:  # BouquetRef is given when renaming alternatives
						self.setRoot(sbouquetref)
					else:
						mode = MODE_TV  # mode is given when renaming bouquet
						if "mode" in param and param["mode"] is not None:
							mode = int(param["mode"])
						if mode == MODE_TV:
							bouquet_rootstr = ROOTTV
						else:
							bouquet_rootstr = ROOTRADIO
						self.setRoot(bouquet_rootstr)
					return (True, _("Bouquet renamed successfully."))
		else:  # service
			# services can not be renamed directly, so delete the current and add it again with new servicename
			srefbefore = param["sRefBefore"] if "sRefBefore" in param else None
			new_param = {}
			new_param["sBouquetRef"] = sbouquetref
			new_param["sRef"] = sref
			new_param["Name"] = sname
			new_param["sRefBefore"] = srefbefore
			returnvalue = self.removeService(new_param)
			if returnvalue[0]:
				returnvalue = self.addServiceToBouquet(new_param)
				if returnvalue[0]:
					return (True, _("Service renamed successfully."))
		return (False, _("Service can not be renamed."))

	def addServiceToAlternative(self, param):
		sbouquetref = param["sBouquetRef"]
		if sbouquetref is None:
			return self.noBouquet()
		sref = param["sRef"] if "sRef" in param else None
		if sref is None:
			return self.noService()
		scurrentref = param["sCurrentRef"]  # alternative service
		if scurrentref is None:
			return (False, _("No current service given!"))
		cur_ref = eServiceReference(scurrentref)
		# check if  service is already an alternative
		if not (cur_ref.flags & eServiceReference.isGroup):
			# sCurrentRef is not an alternative service yet, so do this and add itself to new alternative liste
			mode = MODE_TV  # init
			if "mode" in param and param["mode"] is not None:
				mode = int(param["mode"])
			mutablebouquetlist = self.getMutableList(eServiceReference(sbouquetref))
			if mutablebouquetlist:
				cur_service = ServiceReference(cur_ref)
				name = cur_service.getServiceName()
				prefix = "alternatives"
				name, filename = self.buildBouquetID(name, prefix, mode)
				if mode == MODE_TV:
					sref = '1:134:1:0:0:0:0:0:0:0:FROM BOUQUET \"%s.%s.tv\" ORDER BY bouquet' % (prefix, name)
				else:
					sref = '1:134:2:0:0:0:0:0:0:0:FROM BOUQUET \"%s.%s.radio\" ORDER BY bouquet' % (prefix, name)
				new_ref = eServiceReference(sref)
				if not mutablebouquetlist.addService(new_ref, cur_ref):
					mutablebouquetlist.removeService(cur_ref)
					mutablebouquetlist.flushChanges()
					eDVBDB.getInstance().reloadBouquets()
					mutablealternatives = self.getMutableList(new_ref)
					if mutablealternatives:
						mutablealternatives.setListName(name)
						if mutablealternatives.addService(cur_ref):
							print("add %s to new alternatives failed" % cur_ref.toString())
						mutablealternatives.flushChanges()
						self.setRoot(sbouquetref)
						scurrentref = sref  # currentRef is now an alternative (bouquet)
					else:
						return (False, _("Get mutable list for new created alternative failed!"))
				else:
					return (False, _("Alternative %s created failed.") % name)
			else:
				return (False, _("Bouquetlist is not editable!"))
		# add service to alternative-bouquet
		new_param = {}
		new_param["sBouquetRef"] = scurrentref
		new_param["sRef"] = sref
		returnvalue = self.addServiceToBouquet(new_param)
		if returnvalue[0]:
			cur_ref = eServiceReference(scurrentref)
			cur_service = ServiceReference(cur_ref)
			name = cur_service.getServiceName()
			service_ref = ServiceReference(sref)
			service_name = service_ref.getServiceName()
			return (True, _("Added %s to alternative service %s.") % (service_name, name))
		else:
			return returnvalue

	def removeAlternativeServices(self, param):
		print("[WebComponents.BouquetEditor] removeAlternativeServices with param = %s" % param)
		sbouquetref = param["sBouquetRef"]
		if sbouquetref is None:
			return self.noBouquet()
		sref = param["sRef"] if "sRef" in param else None
		if sref is None:
			return self.noService()
		cur_ref = eServiceReference(sref)
		# check if service is an alternative
		if cur_ref.flags & eServiceReference.isGroup:
			cur_service = ServiceReference(cur_ref)
			_list = cur_service.list()
			first_in_alternative = _list and _list.getNext()
			if first_in_alternative:
				mutablebouquetlist = self.getMutableList(eServiceReference(sbouquetref))
				if mutablebouquetlist is not None:
					if mutablebouquetlist.addService(first_in_alternative, cur_service.ref):
						print("couldn't add first alternative service to current root")
				else:
					print("couldn't edit current root")
			else:
				print("remove empty alternative list")
		else:
			return (False, _("Service is not an alternative."))
		new_param = {}
		new_param["sBouquetRef"] = sref
		new_param["mode"] = None  # of no interest when passing BouquetRefRoot
		new_param["BouquetRefRoot"] = sbouquetref
		returnvalue = self.removeBouquet(new_param)
		if returnvalue[0]:
			self.setRoot(sbouquetref)
			return (True, _("All alternative services deleted."))
		else:
			return returnvalue

	def toggleLock(self, param):
		if not config.ParentalControl.configured.value:
			return (False, _("Parent Control is not activated."))
		sref = param["sRef"] if "sRef" in param else None
		if sref is None:
			return self.noService()
		if "setuppinactive" in list(config.ParentalControl.dict().keys()) and config.ParentalControl.setuppinactive.value:
			password = param["password"] if "password" in param else None
			if password is None:
				return (False, _("No Parent Control Setup Pin given!"))
			else:
				if password.isdigit():
					if int(password) != config.ParentalControl.setuppin.value:
						return (False, _("Parent Control Setup Pin is wrong!"))
				else:
					return (False, _("Parent Control Setup Pin is wrong!"))
		cur_ref = eServiceReference(sref)
		protection = parentalControl.getProtectionLevel(cur_ref.toCompareString())
		if protection:
			parentalControl.unProtectService(cur_ref.toCompareString())
		else:
			parentalControl.protectService(cur_ref.toCompareString())
		if cur_ref.flags & eServiceReference.mustDescent:
			servicetype = "Bouquet"
		else:
			servicetype = "Service"
		if protection:
			if config.ParentalControl.type.value == "blacklist":
				if sref in parentalControl.blacklist:
					if "SERVICE" in (sref in parentalControl.blacklist):
						protectiontext = _("Service %s is locked.") % self.getName(cur_ref)
					elif "BOUQUET" in (sref in parentalControl.blacklist):
						protectiontext = _("Bouquet %s is locked.") % self.getName(cur_ref)
					else:
						protectiontext = _("%s %s is locked.") % (servicetype, self.getName(cur_ref))
			else:
				if hasattr(parentalControl, "whitelist") and sref in parentalControl.whitelist:
					if "SERVICE" in (sref in parentalControl.whitelist):
						protectiontext = _("Service %s is unlocked.") % self.getName(cur_ref)
					elif "BOUQUET" in (sref in parentalControl.whitelist):
						protectiontext = _("Bouquet %s is unlocked.") % self.getName(cur_ref)
		return (True, protectiontext)

	def backupFiles(self, param):
		filename = param
		if not filename:
			filename = self.BACKUP_FILENAME
		invalidcharacters = compile(r'[^A-Za-z0-9_. ]+|^\.|\.$|^ | $|^$')
		tarfilename = "%s.tar" % invalidcharacters.sub('_', filename)
		backupfilename = pathjoin(self.BACKUP_PATH, tarfilename)
		if exists(backupfilename):
			remove(backupfilename)
		checkfile = pathjoin(self.BACKUP_PATH, '.webouquetedit')
		try:
			with open(checkfile, "w") as fd:
				fd.write("created with WebBouquetEditor")

			with tarfile.open(backupfilename, "w:gz") as tar:
				tar.add(checkfile)
				tar.add(pathjoin(ETCENIGMA, "bouquets.tv"))
				tar.add(pathjoin(ETCENIGMA, "bouquets.radio"))
				tar.add(pathjoin(ETCENIGMA, "lamedb"))
				for xml in (pathjoin(ETCTUXBOX, "cables.xml"), pathjoin(ETCTUXBOX, "terrestrial.xml"), pathjoin(ETCTUXBOX, "satellites.xml"), pathjoin(ETCTUXBOX, "atsc.xml"), pathjoin(ETCENIGMA, "lamedb5")):
					if exists(xml):
						tar.add(xml)
				if config.ParentalControl.configured.value:
					if config.ParentalControl.type.value == "blacklist":
						tar.add(pathjoin(ETCENIGMA, "blacklist"))
					else:
						tar.add(pathjoin(ETCENIGMA, "whitelist"))
				files = []
				files += self.getPhysicalFilenamesFromServicereference(eServiceReference(ROOTTV))
				files += self.getPhysicalFilenamesFromServicereference(eServiceReference(ROOTRADIO))
				for file in files:
					if exists(file):
						tar.add(file)
#				for arg in files:
#					if not exists(arg):
#						return (False, _("Error while preparing backup file, %s does not exists.") % arg)
		except Exception as err:
			print("[OpenWebif] Error: preparing backup file '%s'" % str(err))
			return (False, _("Error while preparing backup file."))

		remove(checkfile)
		return (True, tarfilename)

	def getPhysicalFilenamesFromServicereference(self, ref):
		files = []
		servicehandler = eServiceCenter.getInstance()
		services = servicehandler.list(ref)
		servicelist = services and services.getContent("S", True)
		for service in servicelist:
			sref = service
			pos = sref.find('FROM BOUQUET "')
			filename = None
			if pos != -1:
				sref = sref[pos + 14:]
				pos = sref.find('"')
				if pos != -1:
					filename = pathjoin(ETCENIGMA, sref[:pos])
					files.append(filename)
					files += self.getPhysicalFilenamesFromServicereference(eServiceReference(service))
		return files

	def restoreFiles(self, param):
		tarfilename = param
		backupfilename = tarfilename  # path.join(self.BACKUP_PATH, tarfilename)
		if exists(backupfilename):
			check_tar = False
			try:
				with tarfile.open(backupfilename, "r", debug=3) as tar:
					check_tar = tar.getmember("tmp/.webouquetedit")
					if check_tar:
						eDVBDB.getInstance().removeServices()
						files = []
						files += self.getPhysicalFilenamesFromServicereference(eServiceReference(ROOTTV))
						files += self.getPhysicalFilenamesFromServicereference(eServiceReference(ROOTRADIO))
						for bouquetfiles in files:
							if exists(bouquetfiles):
								remove(bouquetfiles)
						tar.extractall("/")

				if check_tar:
					nimmanager.readTransponders()
					eDVBDB.getInstance().reloadServicelist()
					eDVBDB.getInstance().reloadBouquets()
					infobarinstance = InfoBar.instance
					if infobarinstance is not None:
						servicelist = infobarinstance.servicelist
						root = servicelist.getRoot()
						currentref = servicelist.getCurrentSelection()
						servicelist.setRoot(root)
						servicelist.setCurrentSelection(currentref)
				remove("/tmp/.webouquetedit")
				remove(backupfilename)
				if check_tar:
					return (True, _("Bouquet-settings were restored successfully"))
				else:
					return (False, _("Error, %s was not created with WebBouquetEditor...") % backupfilename)
			except Exception as err:
				print("[OpenWebif] Error: extract files from backup '%s'" % str(err))
				return (False, _("Error, extract files from backup '%s'") % backupfilename)
		else:
			return (False, _("Error, %s does not exists, restore is not possible...") % backupfilename)

	def getMutableBouquetList(self, mode):
		if mode == MODE_TV:
			self.bouquet_rootstr = ROOTTV
		else:
			self.bouquet_rootstr = ROOTRADIO
		return self.getMutableList(eServiceReference(self.bouquet_rootstr))

	def getMutableList(self, ref):
		servicehandler = eServiceCenter.getInstance()
		return servicehandler.list(ref).startEdit()

	def setRoot(self, bouquet_rootstr):
		infobarinstance = InfoBar.instance
		if infobarinstance is not None:
			servicelist = infobarinstance.servicelist
			root = servicelist.getRoot()
			if bouquet_rootstr == root.toString():
				currentref = servicelist.getCurrentSelection()
				servicelist.setRoot(root)
				servicelist.setCurrentSelection(currentref)

	def buildBouquetID(self, str, prefix, mode):
		tmp = str.lower()
		name = ''
		for c in tmp:
			if (c >= 'a' and c <= 'z') or (c >= '0' and c <= '9'):
				name += c
			else:
				name += '_'
		# check if file is unique
		suffix = ""
		if mode == MODE_TV:
			suffix = "tv"
		else:
			suffix = "radio"
		filename = pathjoin(ETCENIGMA, "%s.%s.%s" % (prefix, name, suffix))
		if exists(filename):
			i = 1
			while True:
				filename = pathjoin(ETCENIGMA, "%s.%s_%d.%s" % (prefix, name, i, suffix))
				if exists(filename):
					i += 1
				else:
					name = "%s_%d" % (name, i)
					break
		return name, filename

	def getName(self, ref):
		servicehandler = eServiceCenter.getInstance()
		info = servicehandler.info(ref)
		if info:
			name = info.getName(ref)
		else:
			name = ""
		return name

	def importBouquet(self, param):
		if config.usage.multibouquet.value:
			import json
			ret = [False, 'json format error']
			mode = MODE_TV
			try:
				bqimport = json.loads(param["json"][0])
				filename = bqimport["filename"]
				_mode = bqimport["mode"]
				overwrite = bqimport["overwrite"]
				lines = bqimport["lines"]
			except (ValueError, KeyError):
				return ret

			if _mode == 1:
				mode = MODE_RADIO

			fullfilename = pathjoin(ETCENIGMA, filename)

			if mode == MODE_TV:
				sref = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET \"%s\" ORDER BY bouquet' % (filename)
			else:
				sref = '1:7:2:0:0:0:0:0:0:0:FROM BOUQUET \"%s\" ORDER BY bouquet' % (filename)

			if not exists(fullfilename):
				new_bouquet_ref = eServiceReference(str(sref))
				mutablebouquetlist = self.getMutableBouquetList(mode)
				mutablebouquetlist.addService(new_bouquet_ref)
				mutablebouquetlist.flushChanges()

			if overwrite == 1:
				f = open(fullfilename, 'w')
			else:
				f = open(fullfilename, 'a')
			if f:
				for line in lines:
					f.write(line)
					f.write("\n")
				f.close()
			else:
				return [False, 'error creating bouquet file']

			eDVBDB.getInstance().reloadBouquets()
			return [True, 'bouquet added']
		else:
			return [False, _("Multi-Bouquet is not enabled!")]

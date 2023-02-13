##########################################################################
# OpenWebif: movies
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

from os import listdir, stat as osstat, rename, remove, statvfs
from os.path import join as pathjoin, split as pathsplit, realpath, abspath, isdir, splitext, exists, isfile, normpath

from struct import Struct
from time import localtime
from urllib.parse import unquote
from glob import glob

from enigma import eServiceReference, iServiceInformation, eServiceCenter
from ServiceReference import ServiceReference
from Components.config import config
from Components.MovieList import MovieList
from Screens.MovieSelection import defaultMoviePath
from Tools.CopyFiles import copyFiles, moveFiles
from Tools.Directories import fileExists
from ..i18n import _
from ..utilities import getUrlArg2, toString

from Components.MovieList import moviePlayState


def FuzzyTime2(t):
	d = localtime(t)
	n = localtime()
	dayofweek = (_("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun"))

	if d[:3] == n[:3]:
		day = _("Today")
	elif d[0] == n[0] and d[7] == n[7] - 1:
		day = _("Yesterday")
	else:
		day = dayofweek[d[6]]

	if d[0] == n[0]:
		# same year
		date = _("%s %02d.%02d.") % (day, d[2], d[1])
	else:
		date = _("%s %02d.%02d.%d") % (day, d[2], d[1], d[0])

	timeres = _("%02d:%02d") % (d[3], d[4])
	return date + ", " + timeres


MOVIETAGFILE = "/etc/enigma2/movietags"
TRASHDIRNAME = "movie_trash"

MOVIE_LIST_SREF_ROOT = '2:0:1:0:0:0:0:0:0:0:'
MOVIE_LIST_ROOT_FALLBACK = '/media'

#  TODO : optimize move using FileTransferJob if available
#  TODO : add copy api

cutsParser = Struct('>QI')  # big-endian, 64-bit PTS and 32-bit type


def checkParentalProtection(directory):
	if hasattr(config.ParentalControl, 'moviepinactive'):
		if config.ParentalControl.moviepinactive.value:
			directory = pathsplit(directory)[0]
			directory = realpath(directory)
			directory = abspath(directory)
			directory = pathjoin(directory, "")
			is_protected = config.movielist.moviedirs_config.getConfigValue(directory, "protect")
			if is_protected is not None and is_protected == 1:
				return True
	return False


def getMovieList(rargs=None, locations=None, directory=None):
	movieliste = []
	tag = None
	fields = None
	internal = None
	bookmarklist = []

	if rargs:
		tag = getUrlArg2(rargs, "tag")
		directory = getUrlArg2(rargs, "dirname")
		fields = getUrlArg2(rargs, "fields")
		internal = getUrlArg2(rargs, "internal")

	if directory is None:
		directory = defaultMoviePath()

	if not directory:
		directory = MOVIE_LIST_ROOT_FALLBACK
	elif directory.startswith("/hdd/movie/"):
		directory = directory.replace("/hdd/movie/", "/media/hdd/movie/")

	directory = pathjoin(directory, "")

	if not isdir(directory):
		return {
			"movies": [],
			"locations": [],
			"bookmarks": [],
			"directory": [],
		}

	root = eServiceReference(MOVIE_LIST_SREF_ROOT + directory)

	for item in sorted(listdir(directory)):
		abs_p = pathjoin(directory, item)
		if isdir(abs_p):
			bookmarklist.append(item)

	folders = [root]
	brecursive = False
	if rargs and b"recursive" in list(rargs.keys()):
		brecursive = True
		dirs = []
		locations = []
		for subdirpath in glob(directory + "**/", recursive=True):
			locations.append(subdirpath)
			subdirpath = subdirpath[len(directory):]
			dirs.append(subdirpath)

		for f in sorted(dirs):
			if f != '':
				ff = eServiceReference(MOVIE_LIST_SREF_ROOT + pathjoin(directory, f))
				folders.append(ff)
	else:
		# get all locations
		if locations is not None:
			folders = []

			for f in locations:
				ff = eServiceReference(MOVIE_LIST_SREF_ROOT + pathjoin(f, ""))
				folders.append(ff)

	if config.OpenWebif.parentalenabled.value:
		dir_is_protected = checkParentalProtection(directory)
	else:
		dir_is_protected = False

	if not dir_is_protected:
		if internal:
			try:
				from .OWFMovieList import MovieList as OWFMovieList
				movielist = OWFMovieList(None)
			except ImportError:
				movielist = MovieList(None)
		else:
			movielist = MovieList(None)
		for root in folders:
			if tag is not None:
				movielist.load(root=root, filter_tags=[tag])
			else:
				movielist.load(root=root, filter_tags=None)

			for (serviceref, info, begin, unknown) in movielist.list:
				if serviceref.flags & eServiceReference.mustDescent:
					continue

				# BAD fix
				_serviceref = serviceref.toString().replace('%25', '%')
				length_minutes = 0
				txtdesc = ""
				filename = '/'.join(_serviceref.split("/")[1:])
				filename = '/' + filename
				name, ext = splitext(filename)

				sourceref = ServiceReference(
					info.getInfoString(
						serviceref, iServiceInformation.sServiceref))
				rtime = info.getInfo(
					serviceref, iServiceInformation.sTimeCreate)

				movie = {
					'filename': filename,
					'filename_stripped': filename.split("/")[-1],
					'serviceref': _serviceref,
					'length': "?:??",
					'lastseen': 0,
					'filesize_readable': '',
					'recordingtime': rtime,
					'begintime': 'undefined',
					'eventname': ServiceReference(serviceref).getServiceName().replace('\xc2\x86', '').replace('\xc2\x87', ''),
					'servicename': sourceref.getServiceName().replace('\xc2\x86', '').replace('\xc2\x87', ''),
					'tags': info.getInfoString(serviceref, iServiceInformation.sTags),
					'fullname': _serviceref,
				}

				if rtime > 0:
					movie['begintime'] = FuzzyTime2(rtime)

				try:
					length_minutes = info.getLength(serviceref)
				except:  # nosec # noqa: E722
					pass

				if length_minutes:
					movie['length'] = "%d:%02d" % (length_minutes / 60, length_minutes % 60)
					if fields is None or 'pos' in fields:
						movie['lastseen'] = moviePlayState(filename + '.cuts', serviceref, length_minutes) or 0

				if fields is None or 'desc' in fields:
					txtfile = name + '.txt'
					if ext.lower() != '.ts' and isfile(txtfile):
						with open(txtfile, "rb") as handle:
							txtdesc = toString(b''.join(handle.readlines()))

					event = info.getEvent(serviceref)
					extended_description = event and event.getExtendedDescription() or ""
					if extended_description == '' and txtdesc != '':
						extended_description = txtdesc
					movie['descriptionExtended'] = extended_description

					desc = info.getInfoString(serviceref, iServiceInformation.sDescription)
					movie['description'] = desc

				if fields is None or 'size' in fields:
					size = 0
					sz = ''

					try:
						size = osstat(filename).st_size
						if size > 1073741824:
							sz = "%.2f %s" % ((size / 1073741824.), _("GB"))
						elif size > 1048576:
							sz = "%.2f %s" % ((size / 1048576.), _("MB"))
						elif size > 1024:
							sz = "%.2f %s" % ((size / 1024.), _("kB"))
					except:  # nosec # noqa: E722
						pass

					movie['filesize'] = size
					movie['filesize_readable'] = sz

				movieliste.append(movie)
#		del movielist

	if locations is None:
		return {
			"movies": movieliste,
			"bookmarks": bookmarklist,
			"directory": directory,
			"recursive": brecursive
		}

	if brecursive:
		return {
			"movies": movieliste,
			"locations": locations,
			"directory": directory,
			"bookmarks": bookmarklist,
			"recursive": brecursive
		}
	else:
		return {
			"movies": movieliste,
			"locations": locations,
			"recursive": brecursive
		}


def getAllMovies():
	locations = config.movielist.videodirs.value[:] or []
	return getMovieList(locations=locations)


def removeMovie(session, sref, force=False):
	service = ServiceReference(sref)
	result = False
	deleted = False
	message = "service error"

	if service is not None:
		servicehandler = eServiceCenter.getInstance()
		offline = servicehandler.offlineOperations(service.ref)
		info = servicehandler.info(service.ref)
		name = info and info.getName(service.ref) or "this recording"

	if offline is not None:
		if force is True:
			message = "force delete"
		elif hasattr(config.usage, 'movielist_trashcan'):
			fullpath = service.ref.getPath()
			srcpath = '/'.join(fullpath.split('/')[:-1]) + '/'
			# TODO: check trash
			# TODO: check enable trash default value
			if '.Trash' not in fullpath and config.usage.movielist_trashcan.value:
				result = False
				message = "trashcan"
				try:
					import Tools.Trashcan
					from Screens.MovieSelection import moveServiceFiles
					trash = Tools.Trashcan.createTrashFolder(srcpath)
					moveServiceFiles(service.ref, trash)
					result = True
					message = "The recording '%s' has been successfully moved to trashcan" % name
				except ImportError:
					message = "trashcan exception"
				except Exception as e:
					message = "Failed to move to .Trash folder: %s" + str(e)
					print(message)
				deleted = True
		if not deleted and not offline.deleteFromDisk(0):
			result = True
	else:
		message = "no offline object"

	if result is False:
		return {
			"result": False,
			"message": "Could not delete Movie '%s' / %s" % (name, message)
		}
	else:
		# EMC reload
		try:
			config.EMC.needsreload.value = True
		except (AttributeError, KeyError):
			pass
		return {
			"result": True,
			"message": "The movie '%s' has been deleted successfully" % name
		}


def movieAction(session, sref, dirname=None, domove=False, newname=None):
	service = eServiceReference(sref)
	action = "rename"
	result = False
	if newname is None:
		action = "move" if domove else "copy"

	if service is not None:
		servicehandler = eServiceCenter.getInstance()
		info = servicehandler.info(service)
		name = info and info.getName(service) or "this recording"
		if dirname:
			dirname = pathjoin(dirname, "")

		message = "The recording '%s' has been %sd successfully" % (name, action)

		try:
			movieActionService(service, dirname, name, domove, newname, action)
			try:
				config.EMC.needsreload.value = True
			except (AttributeError, KeyError):
				pass
			result = True
		except Exception as err:
			message = "The recording '%s' has not been %sd / error: %s" % (name, action, err)

		return {
			"result": result,
			"message": message}
	else:
		return {
			"result": result,
			"message": "Could not %s recording" % action
		}


def createActionList(serviceref, dest, newname=None):
	free = 0
	if newname is None:
		try:
			stat = statvfs(dest)
			free = stat.f_bfree * stat.f_bsize
		except OSError as err:
			raise Exception("Error checking free space: %s" % str(err))

	# normpath is to remove the trailing "/" from directories
	src = normpath(serviceref.getPath())
	srcPath, srcName = pathsplit(src)
	if newname:
		dest = normpath(srcPath)
	elif normpath(srcPath) == dest:
		# Move file to itself is allowed, so we have to check it.
		raise Exception("Refusing to move to the same directory")
	# Make a list of items to move
	moveList = [(src, pathjoin(dest, srcName))]
	if not serviceref.flags & eServiceReference.mustDescent:
		# Real movie, add extra files...
		srcBase, fileext = splitext(src)
		baseName = pathsplit(srcBase)[1]
		if newname:
			baseName = newname
		suffixes = [".eit", ".jpg", "%s.cuts" % fileext, "%s.meta" % fileext, ".txt"]
		if fileext == '.ts':
			suffixes.extend([".ts.ap", ".ts.sc", ".ts_mp.jpg"])

		for suffix in suffixes:
			fileName = "%s%s" % (baseName, suffix)
			candidate = pathjoin(srcPath, fileName)
			if exists(candidate):
				moveList.append((candidate, pathjoin(dest, fileName)))

		size = 0
		if newname is None:
			try:
				for src in moveList:
					size += osstat(src[0]).st_size
			except OSError as err:
				raise Exception("Error checking free space: %s" % str(err))

			if size > free:
				raise Exception("Not enough free space")

	return moveList


def movieActionService(serviceref, dest, name, domove, newname, action):
	try:
		items = createActionList(serviceref, dest, newname)
		if name is None:
			name = pathsplit(items[-1][0])[1]
		if domove:
			print("movieActionService")
			print(items)
			moveFiles(items, name)
			if newname:
				metafilename = None
				for item in items:
					if item[1].endswith(".meta"):
						metafilename = item[1]
						break
				if metafilename and exists(metafilename):
					lines = []
					with open(metafilename, 'r') as fd:
						lines = fd.read().splitlines()
					lines[1] = newname
					with open(metafilename, 'w') as fd:
						lines.append("")
						lines = "\n".join(lines)
						fd.write(lines)
		else:
			copyFiles(items, name)
	except Exception as err:
		print("[OpenWebif] fail to %s %s Error:%s" % (action, name, err))
		# rethrow exception
		raise


def getMovieInfo(sref=None, addtag=None, deltag=None, title=None, cuts=None, description=None, newformat=False):

	if sref is not None:
		sref = unquote(sref)
		result = False
		service = ServiceReference(sref)
		newtags = []
		newtitle = ''
		newdesc = ''
		newcuts = []
		if service is not None:
			fullpath = service.ref.getPath()
			srcPath, srcName = pathsplit(fullpath)
			metafilename = pathjoin(srcPath, "%s.meta" % srcName)
			if exists(metafilename):
				lines = []
				with open(metafilename, 'r') as fd:
					lines = fd.read().splitlines()
				if lines:
					meta = ["", "", "", "", "", "", ""]
					lines = [l.strip() for l in lines]
					le = len(lines)
					meta[0:le] = lines[0:le]
					oldtags = meta[4].split(' ')
					newtitle = meta[1]
					newdesc = meta[2]
					deltags = []
					save = False

					if addtag is not None:
						save = True
						for _add in addtag.split(','):
							__add = _add.replace(' ', '_')
							if __add not in oldtags:
								oldtags.append(__add)
					if deltag is not None:
						save = True
						for _del in deltag.split(','):
							__del = _del.replace(' ', '_')
							deltags.append(__del)

					for _add in oldtags:
						if _add not in deltags:
							newtags.append(_add)

					lines[4] = ' '.join(newtags)

					if title is not None and len(title) > 0:
						save = True
						lines[1] = title
						newtitle = title

					if description is not None and len(description) > 0:
						save = True
						lines[2] = description
						newdesc = description

					if save:
						with open(metafilename, 'w') as fd:
							lines.append("")
							lines = "\n".join(lines)
							fd.write(lines)

					if not newformat:
						return {
							"result": result,
							"tags": newtags
						}

				cutsfilename = pathjoin(srcPath, "%s.cuts" % srcName)
				if exists(cutsfilename):
					try:
						f = open(cutsfilename, 'rb')
						while True:
							data = f.read(cutsParser.size)
							if len(data) < cutsParser.size:
								break
							_pos, _type = cutsParser.unpack(data)
							newcuts.append({
								"type": _type,
								"pos": _pos
								}
							)
						f.close()
					except:  # nosec # noqa: E722
						print('Error')

					if cuts is not None:
						newcuts = []
						f = open(cutsfilename, 'wb')
						for cut in cuts.split(','):
							item = cut.split(':')
							f.write(cutsParser.pack(int(item[1]), int(item[0])))
							newcuts.append({
								"type": item[0],
								"pos": item[1]
								}
							)
						f.close()

				result = True
				return {
					"result": result,
					"tags": newtags,
					"title": newtitle,
					"description": newdesc,
					"cuts": newcuts
				}

		return {
			"result": result,
			"resulttext": "Recording not found"
		}

	tags = []
	wr = False
	if fileExists(MOVIETAGFILE):
		for tag in open(MOVIETAGFILE).read().split("\n"):
			if len(tag.strip()) > 0:
				if deltag != tag:
					tags.append(tag.strip())
				if addtag == tag:
					addtag = None
		if deltag is not None:
			wr = True
	if addtag is not None:
		tags.append(addtag)
		wr = True
	if wr:
		with open(MOVIETAGFILE, 'w') as f:
			f.write("\n".join(tags))
	return {
		"result": True,
		"tags": tags
	}


def getMovieDetails(sref=None):

	service = ServiceReference(sref)
	if service is not None:
		serviceref = service.ref
		length_minutes = 0
		txtdesc = ""
		fullpath = serviceref.getPath()
		filename = '/'.join(fullpath.split("/")[1:])
		filename = '/' + filename
		name, ext = splitext(filename)

		servicehandler = eServiceCenter.getInstance()
		info = servicehandler.info(serviceref)

		sourceref = ServiceReference(
			info.getInfoString(
				serviceref, iServiceInformation.sServiceref))
		rtime = info.getInfo(
			serviceref, iServiceInformation.sTimeCreate)

		movie = {
			'filename': filename,
			'filename_stripped': filename.split("/")[-1],
			'serviceref': serviceref.toString(),
			'length': "?:??",
			'lastseen': 0,
			'filesize_readable': '',
			'recordingtime': rtime,
			'begintime': 'undefined',
			'eventname': service.getServiceName().replace('\xc2\x86', '').replace('\xc2\x87', ''),
			'servicename': sourceref.getServiceName().replace('\xc2\x86', '').replace('\xc2\x87', ''),
			'tags': info.getInfoString(serviceref, iServiceInformation.sTags),
			'fullname': serviceref.toString(),
		}

		if rtime > 0:
			movie['begintime'] = FuzzyTime2(rtime)

		try:
			length_minutes = info.getLength(serviceref)
		except:  # nosec # noqa: E722
			pass

		if length_minutes:
			movie['length'] = "%d:%02d" % (length_minutes / 60, length_minutes % 60)
			movie['lastseen'] = moviePlayState(filename + '.cuts', serviceref, length_minutes) or 0

		txtfile = name + '.txt'
		if ext.lower() != '.ts' and isfile(txtfile):
			with open(txtfile, "rb") as handle:
				txtdesc = toString(b''.join(handle.readlines()))

		event = info.getEvent(serviceref)
		extended_description = event and event.getExtendedDescription() or ""
		if extended_description == '' and txtdesc != '':
			extended_description = txtdesc
		movie['descriptionExtended'] = extended_description
		desc = info.getInfoString(serviceref, iServiceInformation.sDescription)
		movie['description'] = desc

		size = 0
		sz = ''

		try:
			size = osstat(filename).st_size
			if size > 1073741824:
				sz = "%.2f %s" % ((size / 1073741824.), _("GB"))
			elif size > 1048576:
				sz = "%.2f %s" % ((size / 1048576.), _("MB"))
			elif size > 1024:
				sz = "%.2f %s" % ((size / 1024.), _("kB"))
		except:  # nosec # noqa: E722
			pass

		movie['filesize'] = size
		movie['filesize_readable'] = sz

		return {
			"result": True,
			"movie": movie
		}
	else:
		return {
			"result": False,
		}

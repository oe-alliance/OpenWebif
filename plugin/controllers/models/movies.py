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

from os import listdir, stat as osstat, rename, remove
from os.path import join as pathjoin, split as pathsplit, realpath, abspath, isdir, splitext, exists, isfile

from struct import Struct
from time import localtime
from urllib.parse import unquote
from glob import glob

from enigma import eServiceReference, iServiceInformation, eServiceCenter
from ServiceReference import ServiceReference
from Components.config import config
from Components.MovieList import MovieList
from Tools.Directories import fileExists
from Screens.MovieSelection import defaultMoviePath
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
		elif hasattr(config.usage, 'movielist_use_trash_dir'):
			fullpath = service.ref.getPath()
			if TRASHDIRNAME not in fullpath and config.usage.movielist_use_trash_dir.value:
				message = "trashdir"
				try:
					from Screens.MovieSelection import getTrashDir
					from Components.FileTransfer import FileTransferJob
					from Components.Task import job_manager
					trash_dir = getTrashDir(fullpath)
					if trash_dir:
						src_file = str(fullpath)
						dst_file = trash_dir
						if dst_file.endswith("/"):
							dst_file = trash_dir[:-1]
						text = _("remove")
						job_manager.AddJob(FileTransferJob(src_file, dst_file, False, False, "%s : %s" % (text, src_file)))
						# No Result because of async job
						message = "The recording '%s' has been successfully moved to trashcan" % name
						result = True
					else:
						message = _("Delete failed, because there is no movie trash !\nDisable movie trash in configuration to delete this item")
				except ImportError:
					message = "trashdir exception"
				except Exception as e:
					message = "Failed to move to trashdir: %s" + str(e)
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


def _moveMovie(session, sref, destpath=None, newname=None):
	service = ServiceReference(sref)
	result = True
	errtext = 'unknown Error'

	if destpath:
		destpath = pathjoin(destpath, "")

	if service is not None:
		servicehandler = eServiceCenter.getInstance()
		info = servicehandler.info(service.ref)
		name = info and info.getName(service.ref) or "this recording"
		fullpath = service.ref.getPath()
		srcpath = '/'.join(fullpath.split('/')[:-1]) + '/'
		fullfilename = fullpath.split('/')[-1]
		filename, fileext = splitext(fullfilename)
		if newname is not None:
			newfullpath = srcpath + newname + fileext

		# TODO: check splitted recording
		# TODO: use FileTransferJob
		def domove():
			errorlist = []
			if fileext == '.ts':
				suffixes = ".ts.meta", ".ts.cuts", ".ts.ap", ".ts.sc", ".eit", ".ts", ".jpg", ".ts_mp.jpg"
			else:
				suffixes = "%s.ts.meta" % fileext, "%s.cuts" % fileext, fileext, '.jpg', '.eit'

			for suffix in suffixes:
				src = srcpath + filename + suffix
				if exists(src):
					try:
						if newname is not None:
							# rename title in meta file
							if suffix == '.ts.meta':
								# todo error handling
								lines = []
								with open(src, "r") as fin:
									for line in fin:
										lines.append(line)
								lines[1] = newname + '\n'
								lines[4] = '\n'
								with open(srcpath + newname + suffix, 'w') as fout:
									fout.write(''.join(lines))
								remove(src)
							else:
								rename(src, srcpath + newname + suffix)
						else:
							rename(src, destpath + filename + suffix)
					except OSError as err:
						errorlist.append(str(err))
						break
			return errorlist

		# MOVE
		if newname is None:
			if srcpath == destpath:
				result = False
				errtext = 'Equal Source and Destination Path'
			elif not exists(fullpath):
				result = False
				errtext = 'File not exist'
			elif not exists(destpath):
				result = False
				errtext = 'Destination Path not exist'
			elif exists(destpath + fullfilename):
				errtext = 'Destination File exist'
				result = False
		# rename
		else:
			if not exists(fullpath):
				result = False
				errtext = 'File not exist'
			elif exists(newfullpath):
				result = False
				errtext = 'New File exist'

		if result:
			errlist = domove()
			if not errlist:
				result = True
			else:
				errtext = errlist[0]
				result = False

	etxt = "rename"
	if newname is None:
		etxt = "move"
	if result is False:
		return {
			"result": False,
			"message": "Could not %s recording '%s' Err: '%s'" % (etxt, name, errtext)
		}
	else:
		# EMC reload
		try:
			config.EMC.needsreload.value = True
		except (AttributeError, KeyError):
			pass
		return {
			"result": True,
			"message": "The recording '%s' has been %sd successfully" % (name, etxt)
		}


def moveMovie(session, sref, destpath):
	return _moveMovie(session, sref, destpath=destpath)


def renameMovie(session, sref, newname):
	return _moveMovie(session, sref, newname=newname)


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
			filename = '/'.join(fullpath.split("/")[1:])
			metafilename = '/' + filename + '.meta'
			if fileExists(metafilename):
				lines = []
				with open(metafilename, 'r') as f:
					lines = f.readlines()
				if lines:
					meta = ["", "", "", "", "", "", ""]
					lines = [l.strip() for l in lines]
					le = len(lines)
					meta[0:le] = lines[0:le]
					oldtags = meta[4].split(' ')
					newtitle = meta[1]
					newdesc = meta[2]
					deltags = []

					if addtag is not None:
						for _add in addtag.split(','):
							__add = _add.replace(' ', '_')
							if __add not in oldtags:
								oldtags.append(__add)
					if deltag is not None:
						for _del in deltag.split(','):
							__del = _del.replace(' ', '_')
							deltags.append(__del)

					for _add in oldtags:
						if _add not in deltags:
							newtags.append(_add)

					lines[4] = ' '.join(newtags)

					if title is not None and len(title) > 0:
						lines[1] = title
						newtitle = title

					if description is not None and len(description) > 0:
						lines[2] = description
						newdesc = description

					with open(metafilename, 'w') as f:
						f.write('\n'.join(lines))

					if not newformat:
						return {
							"result": result,
							"tags": newtags
						}

				cutsfilename = '/' + filename + '.cuts'
				if fileExists(cutsfilename):
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
						cutsfilename = '/' + filename + '.cuts'
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

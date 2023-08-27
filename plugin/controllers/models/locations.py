##############################################################################
#                        2011 - 2022 E2OpenPlugin                            #
#                                                                            #
#  This file is open source software; you can redistribute it and/or modify  #
#     it under the terms of the GNU General Public License version 2 as      #
#               published by the Free Software Foundation.                   #
#                                                                            #
##############################################################################
from os import makedirs, rmdir
from os.path import exists
from Components.config import config


def getLocations():
	return {
		"result": True,
		"locations": config.movielist.videodirs.value,
		"default": config.usage.default_path.value
	}


def getCurrentLocation():
	path = config.movielist.last_videodir.value or "/hdd/movie"
	if not exists(path):
		path = "/hdd/movie"

	return {
		"result": True,
		"location": path
	}


def addLocation(dirname, create):
	if not exists(dirname):
		if create:
			try:
				makedirs(dirname)
			except OSError:
				return {
					"result": False,
					"message": f"Creation of folder '{dirname}' failed"
				}
		else:
			return {
				"result": False,
				"message": f"Folder '{dirname}' does not exist"
			}

	locations = config.movielist.videodirs.value[:] or []
	if dirname in locations:
		return {
			"result": False,
			"message": f"Location '{dirname}' is already defined"
		}

	locations.append(dirname)
	config.movielist.videodirs.value = locations
	config.movielist.videodirs.save()

	return {
		"result": True,
		"message": f"Location '{dirname}' added succesfully"
	}


def removeLocation(dirname, remove):
	locations = config.movielist.videodirs.value[:] or []
	res = False
	msg = f"Location '{dirname}' is not defined"
	if dirname in locations:
		res = True
		locations.remove(dirname)
		config.movielist.videodirs.value = locations
		config.movielist.videodirs.save()
		if exists(dirname) and remove:
			try:
				rmdir(dirname)
				msg = f"Location and Folder '{dirname}' removed succesfully"
			except OSError:
				msg = f"Location '{dirname}' removed succesfully but the Folder not exists or is not empty"
		else:
			msg = f"Location '{dirname}' removed succesfully"
	return {
		"result": res,
		"message": msg
	}

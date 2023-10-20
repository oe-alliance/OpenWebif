# -*- coding: utf-8 -*-

from Tools.ISO639 import LanguageCodes


def getAudioTracks(session):
	service = session.nav.getCurrentService()
	audio = service and service.audioTracks()
	ret = {"tracklist": [], "result": False}
	if audio is not None and service is not None:
		current = audio.getCurrentTrack()
		for i in list(range(0, audio.getNumberOfTracks())):
			track = audio.getTrackInfo(i)
			languages = track.getLanguage().split('/')
			language = ""
			for lang in languages:
				if len(language) > 0:
					language += " / "

				if lang in LanguageCodes:
					language += LanguageCodes[lang][0]
				else:
					language += lang

			description = track.getDescription()
			if description:
				description += f" ({language})"
			else:
				description = language

			ret["result"] = True
			ret["tracklist"].append({
				"description": description,
				"index": i,
				"pid": track.getPID(),
				"active": i == current
			})

	return ret


def setAudioTrack(session, audioid):
	service = session.nav.getCurrentService()
	audio = service and service.audioTracks()
	if audio is not None and service is not None:
		if audio.getNumberOfTracks() > audioid and audioid >= 0:
			audio.selectTrack(audioid)
			return {"result": True}

	return {"result": False}

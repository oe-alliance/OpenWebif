# -*- coding: utf-8 -*-

from time import localtime, strftime
from urllib.parse import quote
from Plugins.Extensions.OpenWebif.controllers.i18n import tstrings


class renderEvtBlock:
	def __init__(self):
		self.template = """
		<article onclick="loadeventepg('%s', '%s'); return false;" class="epg__event event %s" data-ref="%s" data-id="%s" data-toggle="modal" data-target="#EventModal">
			<time class="epg__time--start">%s</time>
			<span class="epg__title title">
				%s
			</span>
			%s
		</article>
		"""

	def render(self, event):
		eventcssclass = ''

		timer = event['timer']
		if timer:
			eventcssclass = eventcssclass + ' event--has-timer'
			if timer['isEnabled']:
				timereventsymbol = '<i class="material-icons material-icons-centered">alarm_on</i>'
			else:
				timereventsymbol = '<i class="material-icons material-icons-centered">alarm_off</i>'
			if timer['isAutoTimer']:
				timereventsymbol = timereventsymbol + '<i class="material-icons material-icons-centered">av_timer</i>'
		else:
			timereventsymbol = ''

		if event['title'] != event['shortdesc']:
			shortdesc = '<summary class="epg__desc desc"><span class="epg__timer-status">%s</span>%s</summary>' % (
				timereventsymbol,
				event['shortdesc']
			)
		else:
			shortdesc = ''

		sref = quote(event['ref'], safe=' ~@#$&()*!+=:;,.?/\'')

		return self.template % (
			event['id'],
			sref,
			eventcssclass,
			sref,
			event['id'],
			strftime("%H:%M", localtime(event['begin_timestamp'])),
			event['title'],
			shortdesc
		)

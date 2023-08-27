from time import localtime, strftime
from urllib.parse import quote
#from Plugins.Extensions.OpenWebif.controllers.i18n import tstrings


class renderEvtBlock:

    def __init__(self):
        pass

    def render(self, event):
        if event['title'] != event['shortdesc']:
            shortdesc = f"<div class=\"desc\">{event['shortdesc']}</div>"
        else:
            shortdesc = ''

        if event['timerStatus'] != '':
            text = event['timer']['text']
            timerEventSymbol = f"<div class=\"{event['timerStatus']}\">{text}</div>"
            timerbar = "background-color:red;"
        else:
            timerEventSymbol = ''
            timerbar = ''

        ref = quote(event['ref'], safe=' ~@#$&()*!+=:;,.?/\'')
        hourmin = strftime("%H:%M", localtime(event['begin_timestamp']))

        return f"""
        <div class="event" data-ref="{ref}" data-id="{event['id']}">
            <div style="width:40px; float:left; padding: 0 3px">{hourmin}{timerEventSymbol}</div>
            <div style="width:144px; float:left">
                <div class="title">{event['title']}</div>{shortdesc}
            </div>
            <div style="clear:left;height:2px;{timerbar}"></div>
        </div>
        """

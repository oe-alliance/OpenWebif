from gettext import bindtextdomain, dgettext, gettext

from Components.Language import language
from Tools.Directories import SCOPE_PLUGINS, resolveFilename

__version__ = "2.4.0"

LOCALES_DOMAIN = "OpenWebif"
LOCALES_RELPATH = "Extensions/OpenWebif/locale"


def _locale_init():
	bindtextdomain(LOCALES_DOMAIN, resolveFilename(SCOPE_PLUGINS, LOCALES_RELPATH))


def _(txt):
	try:
		translated = dgettext(LOCALES_DOMAIN, txt)
		return gettext(txt) if translated == txt else translated
	except Exception:
		return txt


_locale_init()
language.addCallback(_locale_init)

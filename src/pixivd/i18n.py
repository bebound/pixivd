import gettext
import os
import sys
import locale

languages = [locale.getdefaultlocale()[0], 'en_US']

current_path = os.path.dirname(os.path.abspath(__file__))
t = gettext.translation('messages', os.path.join(current_path, "locale"), languages=languages)
i18n = t.gettext

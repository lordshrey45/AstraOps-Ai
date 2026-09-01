"""
Translation Service — Centralized localization manager for Wari Mitra.

Loads translation files for English (en), Marathi (mr), and Hindi (hi).
Provides template filter/helper `t(key)` with fallback to English.
"""

import os
import json
from flask import session


SUPPORTED_LANGUAGES = {
    'en': 'English',
    'mr': 'मराठी',
    'hi': 'हिन्दी'
}

DEFAULT_LANGUAGE = 'en'
_TRANSLATIONS = {}


def load_translations(app_root=None):
    """Load JSON translation dictionaries into memory."""
    global _TRANSLATIONS
    _TRANSLATIONS = {}

    if not app_root:
        app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    translations_dir = os.path.join(app_root, 'translations')

    for lang in SUPPORTED_LANGUAGES.keys():
        file_path = os.path.join(translations_dir, f'{lang}.json')
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                _TRANSLATIONS[lang] = json.load(f)
        else:
            _TRANSLATIONS[lang] = {}


def get_current_language():
    """Get the active language code from Flask session."""
    lang = session.get('lang', DEFAULT_LANGUAGE)
    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE
    return lang


def set_current_language(lang_code):
    """Set active language code in session."""
    if lang_code in SUPPORTED_LANGUAGES:
        session['lang'] = lang_code
        return True
    return False


def get_translation(key, lang=None, default=None):
    """
    Lookup a translation key with fallback.
    Fallback order: Specified lang -> Session lang -> English ('en') -> key string.
    """
    load_translations()

    if not lang:
        lang = get_current_language()

    # 1. Try requested language
    lang_dict = _TRANSLATIONS.get(lang, {})
    if key in lang_dict:
        return lang_dict[key]

    # 2. Try English fallback
    en_dict = _TRANSLATIONS.get(DEFAULT_LANGUAGE, {})
    if key in en_dict:
        return en_dict[key]

    # 3. Fallback to default arg or raw key
    return default if default is not None else key


def get_all_translations_json(lang=None):
    """Return dictionary of current language translations for client JS."""
    load_translations()
    if not lang:
        lang = get_current_language()
    return _TRANSLATIONS.get(lang, _TRANSLATIONS.get(DEFAULT_LANGUAGE, {}))

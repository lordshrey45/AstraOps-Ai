"""
TTS Service — Server-side text-to-speech audio generation for Wari Mitra.

Supports complete native pronunciation for:
- Marathi ('mr')
- Hindi ('hi')
- English ('en')

Preserves full response text without sentence slicing or truncation.
Uses LRU memory caching for instant repeat playback.
"""

import io
import re
import functools
from gtts import gTTS


def _clean_speech_text(text):
    """
    Clean HTML tags and whitespace without truncating or dropping text content.
    Preserves complete multi-paragraph responses, Unicode characters, bullets, and numbers.
    """
    if not text:
        return ""
    # Strip HTML tags
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = clean.replace('DEMO DATA', '').strip()
    clean = re.sub(r'[ \t]+', ' ', clean)
    return clean.strip()


@functools.lru_cache(maxsize=256)
def _synthesize_cached_mp3(clean_text, target_lang):
    """
    LRU cached audio synthesis helper.
    Returns raw MP3 bytes for the full text.
    """
    tts = gTTS(text=clean_text, lang=target_lang, slow=False)
    mp3_fp = io.BytesIO()
    tts.write_to_fp(mp3_fp)
    return mp3_fp.getvalue()


def generate_speech_audio(text, lang='en'):
    """
    Synthesize complete text into MP3 audio stream using native language pronunciation.

    Args:
        text (str): Plain text to speak.
        lang (str): Language code ('en', 'mr', 'hi').

    Returns:
        io.BytesIO: In-memory MP3 audio bytes stream, or None on failure.
    """
    if not text or not text.strip():
        return None

    # Clean text without any truncation or sentence slicing
    clean_text = _clean_speech_text(text)
    if not clean_text:
        return None

    # Map language code to gTTS supported code
    lang_str = (lang or 'en').lower()
    if lang_str.startswith('mr'):
        target_lang = 'mr'
    elif lang_str.startswith('hi'):
        target_lang = 'hi'
    else:
        target_lang = 'en'

    print(f"[TTS DEBUG] Input text len: {len(text)}, Clean text len sent to gTTS ({target_lang}): {len(clean_text)}")

    try:
        mp3_bytes = _synthesize_cached_mp3(clean_text, target_lang)
        return io.BytesIO(mp3_bytes)
    except Exception as e:
        print(f"TTS Service generation error for lang '{lang}': {e}")
        return None

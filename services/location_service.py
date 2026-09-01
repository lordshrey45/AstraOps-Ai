"""
Location Service — Centralized reverse-geocoding & location name manager for Wari Mitra.

Resolves (latitude, longitude) coordinates to human-readable place names with:
- Multilingual support ('en', 'mr', 'hi')
- Proximity lookup to known Wari halts/route points
- Reverse-geocoding via Nominatim API with rate-limit friendly caching
- Safe fallbacks ('Location unavailable' or English fallback, never crashes/null)
"""

import math
import requests
from flask import session
from services.translation_service import get_current_language, get_translation

# In-memory location cache: key -> location_name string
_LOCATION_CACHE = {}

# Known Wari Route Halts & Landmark reference points for fast offline lookup
KNOWN_LOCATIONS = [
    {"lat": 18.7153, "lon": 73.7714, "en": "Dehu", "mr": "देहू", "hi": "देहु", "state": "Maharashtra", "state_mr": "महाराष्ट्र", "state_hi": "महाराष्ट्र"},
    {"lat": 18.6749, "lon": 73.8899, "en": "Alandi", "mr": "आळंदी", "hi": "आलंदी", "state": "Maharashtra", "state_mr": "महाराष्ट्र", "state_hi": "महाराष्ट्र"},
    {"lat": 18.5204, "lon": 73.8567, "en": "Pune", "mr": "पुणे", "hi": "पुणे", "state": "Maharashtra", "state_mr": "महाराष्ट्र", "state_hi": "महाराष्ट्र"},
    {"lat": 18.3418, "lon": 73.9877, "en": "Saswad", "mr": "सासवड", "hi": "सासवड", "state": "Maharashtra", "state_mr": "महाराष्ट्र", "state_hi": "महाराष्ट्र"},
    {"lat": 18.2742, "lon": 74.1565, "en": "Jejuri", "mr": "जेजुरी", "hi": "जेजुरी", "state": "Maharashtra", "state_mr": "महाराष्ट्र", "state_hi": "महाराष्ट्र"},
    {"lat": 18.0411, "lon": 74.1872, "en": "Lonand", "mr": "लोणंद", "hi": "लोनंद", "state": "Maharashtra", "state_mr": "महाराष्ट्र", "state_hi": "महाराष्ट्र"},
    {"lat": 17.9897, "lon": 74.4339, "en": "Phaltan", "mr": "फलटण", "hi": "फलटन", "state": "Maharashtra", "state_mr": "महाराष्ट्र", "state_hi": "महाराष्ट्र"},
    {"lat": 17.9012, "lon": 74.6985, "en": "Natepute", "mr": "नातेपुते", "hi": "नातेपुते", "state": "Maharashtra", "state_mr": "महाराष्ट्र", "state_hi": "महाराष्ट्र"},
    {"lat": 17.8288, "lon": 74.8021, "en": "Malshiras", "mr": "माळशिरस", "hi": "मालशिरस", "state": "Maharashtra", "state_mr": "महाराष्ट्र", "state_hi": "महाराष्ट्र"},
    {"lat": 17.7512, "lon": 75.0214, "en": "Velapur", "mr": "वेळापूर", "hi": "वेलापुर", "state": "Maharashtra", "state_mr": "महाराष्ट्र", "state_hi": "महाराष्ट्र"},
    {"lat": 17.7012, "lon": 75.2514, "en": "Wakhari", "mr": "वाखारी", "hi": "वाखारी", "state": "Maharashtra", "state_mr": "महाराष्ट्र", "state_hi": "महाराष्ट्र"},
    {"lat": 17.6774, "lon": 75.3283, "en": "Pandharpur", "mr": "पंढरपूर", "hi": "पंढरपुर", "state": "Maharashtra", "state_mr": "महाराष्ट्र", "state_hi": "महाराष्ट्र"},
]

def _haversine_km(lat1, lon1, lat2, lon2):
    """Calculate distance between two GPS coordinates in kilometers."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def clear_location_cache():
    """Clear the in-memory location cache (used in tests)."""
    global _LOCATION_CACHE
    _LOCATION_CACHE.clear()

def get_location_name(lat, lon, lang=None):
    """
    Get a human-readable location name for given coordinates.

    Args:
        lat (float): Latitude
        lon (float): Longitude
        lang (str, optional): Language code ('en', 'mr', 'hi'). Defaults to session language.

    Returns:
        str: Human-readable location name (e.g. "Pandharpur, Maharashtra") or fallback string.
    """
    if lat is None or lon is None:
        return get_translation('location_unavailable', lang, 'Location unavailable')

    try:
        lat = float(lat)
        lon = float(lon)
    except (ValueError, TypeError):
        return get_translation('location_unavailable', lang, 'Location unavailable')

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return get_translation('location_unavailable', lang, 'Location unavailable')

    if not lang:
        try:
            lang = get_current_language()
        except RuntimeError:
            lang = 'en'

    if lang not in ('en', 'mr', 'hi'):
        lang = 'en'

    # Cache key rounded to 3 decimal places (~110m precision)
    cache_key = f"{round(lat, 3)},{round(lon, 3)}:{lang}"
    if cache_key in _LOCATION_CACHE:
        return _LOCATION_CACHE[cache_key]

    # 1. Proximity check against known Wari locations (~15.0 km radius)
    best_known = None
    min_dist = 15.0  # km
    for item in KNOWN_LOCATIONS:
        dist = _haversine_km(lat, lon, item['lat'], item['lon'])
        if dist < min_dist:
            min_dist = dist
            best_known = item

    if best_known:
        name = best_known.get(lang, best_known['en'])
        state = best_known.get(f'state_{lang}', best_known['state'])
        res_str = f"{name}, {state}"
        _LOCATION_CACHE[cache_key] = res_str
        return res_str

    # 2. Reverse-geocoding via Nominatim API with timeout and User-Agent
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            'lat': lat,
            'lon': lon,
            'format': 'jsonv2',
            'accept-language': lang
        }
        headers = {
            'User-Agent': 'WariMitra/1.0 (warimitra@example.com)'
        }
        resp = requests.get(url, params=params, headers=headers, timeout=3.5)
        if resp.status_code == 200:
            data = resp.json()
            address = data.get('address', {})
            place = (
                address.get('village') or
                address.get('town') or
                address.get('city') or
                address.get('suburb') or
                address.get('county') or
                address.get('district') or
                address.get('state_district')
            )
            state = address.get('state') or 'Maharashtra'

            if place:
                res_str = f"{place}, {state}"
                _LOCATION_CACHE[cache_key] = res_str
                return res_str
            elif data.get('display_name'):
                parts = [p.strip() for p in data['display_name'].split(',') if p.strip()]
                if len(parts) >= 2:
                    res_str = f"{parts[0]}, {parts[-2]}"
                else:
                    res_str = parts[0]
                _LOCATION_CACHE[cache_key] = res_str
                return res_str
    except Exception:
        pass

    # 3. Fallback: try English lookup if lang != 'en'
    if lang != 'en':
        en_name = get_location_name(lat, lon, lang='en')
        if en_name and en_name != get_translation('location_unavailable', 'en', 'Location unavailable'):
            _LOCATION_CACHE[cache_key] = en_name
            return en_name

    # 4. Regional fallback if within Wari region / Maharashtra bounding box
    if 15.0 <= lat <= 22.5 and 72.0 <= lon <= 81.0:
        if lang == 'mr':
            regional_str = "महाराष्ट्र, भारत"
        elif lang == 'hi':
            regional_str = "महाराष्ट्र, भारत"
        else:
            regional_str = "Maharashtra, India"
        _LOCATION_CACHE[cache_key] = regional_str
        return regional_str

    # 5. Final Fallback
    fallback_str = get_translation('location_unavailable', lang, 'Location unavailable')
    _LOCATION_CACHE[cache_key] = fallback_str
    return fallback_str

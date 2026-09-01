"""
Weather Routes — Flask Blueprint for the Weather module.

Serves the weather page and provides the weather API endpoint.

Page Routes:
    GET /weather — Weather page

API Routes:
    GET /api/weather?latitude=<lat>&longitude=<lon> — Weather data (JSON)
"""

from flask import Blueprint, render_template, request, jsonify, current_app
from services.weather_service import get_weather
from models.schedule_model import get_all_route_points


# Create the Blueprint
weather_bp = Blueprint('weather', __name__)

# Demo halt names (reused from map module for location selector)
DEMO_HALT_NAMES = {
    1: 'Dehu', 2: 'Loni Kalbhor', 3: 'Jejuri approach', 4: 'Jejuri',
    5: 'Walhe approach', 6: 'Walhe', 7: 'Lonand approach', 8: 'Lonand',
    9: 'Taradgaon approach', 10: 'Taradgaon', 11: 'Phaltan approach',
    12: 'Phaltan', 13: 'Baramati Road approach', 14: 'Baramati Road',
    15: 'Natepute approach', 16: 'Natepute', 17: 'Malshiras approach',
    18: 'Malshiras', 19: 'Velapur approach', 20: 'Velapur',
    21: 'Bhandishegaon approach', 22: 'Bhandishegaon',
    23: 'Wakhari approach', 24: 'Wakhari',
    25: 'Pandharpur approach', 26: 'Pandharpur'
}


@weather_bp.route('/weather')
def weather_page():
    """
    Weather page. Loads route points for the location selector.
    Weather data is fetched dynamically via weather.js.
    """
    db_path = current_app.config['DATABASE']
    raw_points = get_all_route_points(db_path)

    # Build location list for the selector (only halt points, not approach points)
    locations = []
    seen = set()
    for p in raw_points:
        name = DEMO_HALT_NAMES.get(p['sequence'], f"Point {p['sequence']}")
        # Skip approach points for cleaner dropdown
        if 'approach' in name.lower():
            continue
        if name not in seen:
            locations.append({
                'name': name,
                'latitude': p['latitude'],
                'longitude': p['longitude'],
                'day': p['day_number'],
                'sequence': p['sequence']
            })
            seen.add(name)

    return render_template('weather.html', locations=locations)


@weather_bp.route('/api/weather')
def api_weather():
    """
    GET /api/weather?latitude=<lat>&longitude=<lon>

    Returns current weather + 7-day forecast from Open-Meteo.

    Query Parameters:
        latitude (required): GPS latitude (-90 to 90)
        longitude (required): GPS longitude (-180 to 180)

    Returns:
        JSON with current conditions, daily forecast, and alerts.
    """
    lat = request.args.get('latitude')
    lon = request.args.get('longitude')

    if lat is None or lon is None:
        return jsonify({
            "success": False,
            "error": "Latitude and longitude are required."
        }), 400

    result = get_weather(lat, lon)

    if not result.get("success"):
        return jsonify(result), 400

    return jsonify(result)

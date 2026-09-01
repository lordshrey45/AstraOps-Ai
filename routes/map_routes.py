"""
Map Routes — Flask Blueprint for the Interactive Wari Route Map.

Serves the map page and provides API endpoints for route data.

Page Routes:
    GET /map — Interactive map page

API Routes:
    GET /api/route — Route polyline points (JSON), optionally filtered by day
"""

from flask import Blueprint, render_template, jsonify, request, current_app
from models.schedule_model import (
    get_all_route_points,
    get_route_points_by_day,
    get_full_schedule
)


# Create the Blueprint
map_bp = Blueprint('map', __name__)


# ============================================================
# Page Route
# ============================================================

@map_bp.route('/map')
def map_page():
    """
    Interactive Wari Route Map page.
    Renders the Leaflet map template. Route data is loaded
    dynamically via fetch calls to /api/route from map.js.
    """
    # Get schedule for the day filter dropdown
    db_path = current_app.config['DATABASE']
    schedule = get_full_schedule(db_path)

    # Convert sqlite3.Row objects to dicts for template
    schedule_list = []
    for entry in schedule:
        schedule_list.append({
            'day_number': entry['day_number'],
            'halt_village': entry['halt_village'],
            'date': entry['date']
        })

    return render_template('map.html', schedule=schedule_list)


# ============================================================
# API Route — Route Points
# ============================================================

@map_bp.route('/api/route')
def api_route():
    """
    GET /api/route — Returns route polyline points as JSON.

    Query Parameters:
        day (optional): Filter by day number. If omitted, returns all points.

    Returns:
        JSON array of {lat, lng, day_number, sequence} objects,
        ordered by day_number and sequence.
    """
    db_path = current_app.config['DATABASE']

    # Optional day filter
    day = request.args.get('day', type=int)

    if day:
        points = get_route_points_by_day(db_path, day)
    else:
        points = get_all_route_points(db_path)

    # Convert sqlite3.Row objects to JSON-serializable dicts
    result = []
    for point in points:
        result.append({
            'id': point['id'],
            'lat': point['latitude'],
            'lng': point['longitude'],
            'day_number': point['day_number'],
            'sequence': point['sequence']
        })

    return jsonify(result)


# ============================================================
# API Route — Schedule (for map info panel)
# ============================================================

@map_bp.route('/api/schedule')
def api_schedule():
    """
    GET /api/schedule — Returns the full daily schedule as JSON.
    Used by the map info panel to show halt details.
    """
    db_path = current_app.config['DATABASE']
    schedule = get_full_schedule(db_path)

    result = []
    for entry in schedule:
        result.append({
            'day_number': entry['day_number'],
            'date': entry['date'],
            'halt_village': entry['halt_village'],
            'distance_km': entry['distance_km'],
            'start_time': entry['start_time'],
            'end_time': entry['end_time'],
            'notes': entry['notes']
        })

    return jsonify(result)


# ============================================================
# API Route — Location Name Reverse Geocoding
# ============================================================

@map_bp.route('/api/location_name')
def api_location_name():
    """
    GET /api/location_name — Returns human-readable location name for lat/lon.

    Query Parameters:
        latitude (float): Latitude
        longitude (float): Longitude
        lang (str, optional): Language code ('en', 'mr', 'hi')

    Returns:
        JSON response with location_name string.
    """
    from services.location_service import get_location_name
    from services.translation_service import get_current_language

    lat = request.args.get('latitude', type=float)
    lon = request.args.get('longitude', type=float)
    lang = request.args.get('lang', type=str)

    print(f"[GPS TEST] Backend received:\nlatitude = {lat}\nlongitude = {lon}")

    if lat is None or lon is None:
        return jsonify({
            'success': False,
            'error': 'Latitude and longitude parameters are required.'
        }), 400

    name = get_location_name(lat, lon, lang=lang)
    print(f"[GPS TEST] Resolved location:\n{name}")
    return jsonify({
        'success': True,
        'location_name': name,
        'latitude': lat,
        'longitude': lon,
        'lang': lang or get_current_language()
    })

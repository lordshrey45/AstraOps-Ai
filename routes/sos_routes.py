"""
SOS Routes — Flask Blueprint for the Emergency SOS module.

Serves the SOS page and provides the SOS API endpoint.

Page Routes:
    GET /sos — Emergency SOS page

API Routes:
    POST /api/sos — Create an SOS request
"""

from flask import Blueprint, render_template, request, jsonify, session, current_app
from models.sos_model import (
    create_sos_request,
    get_sos_requests_by_user
)
from models.user_model import get_user_by_id
from models.facility_model import get_all_facilities


# Create the Blueprint
sos_bp = Blueprint('sos', __name__)

# Validation constants
MAX_MESSAGE_LENGTH = 500


# ============================================================
# Page Route
# ============================================================

@sos_bp.route('/sos')
def sos_page():
    """
    Emergency SOS page.
    If user is authenticated, loads their emergency contact, medical info,
    and SOS history.
    """
    user_info = None
    sos_history = []

    db_path = current_app.config['DATABASE']

    if 'user_id' in session:
        user = get_user_by_id(db_path, session['user_id'])
        if user:
            user_info = {
                'name': user['name'],
                'phone': user['phone'],
                'emergency_contact': user['emergency_contact'],
                'medical_info': user['medical_info']
            }

        raw_history = get_sos_requests_by_user(db_path, session['user_id'])
        for entry in raw_history:
            sos_history.append({
                'id': entry['id'],
                'latitude': entry['latitude'],
                'longitude': entry['longitude'],
                'message': entry['message'],
                'status': entry['status'],
                'created_at': entry['created_at']
            })

    return render_template('sos.html', user_info=user_info, sos_history=sos_history)


# ============================================================
# API Route — Create SOS
# ============================================================

@sos_bp.route('/api/sos', methods=['POST'], strict_slashes=False)
def api_create_sos():
    """
    POST /api/sos — Create a new SOS emergency request.

    Request JSON:
        {
            "latitude": 18.XXXX,
            "longitude": 73.XXXX,
            "message": "optional emergency message"
        }

    Response JSON:
        {
            "success": true,
            "sos_id": 123,
            "status": "pending"
        }

    Validation:
        - latitude required, must be -90 to 90
        - longitude required, must be -180 to 180
        - message optional, max MAX_MESSAGE_LENGTH chars
    """
    data = request.get_json()

    if not data:
        return jsonify({
            'success': False,
            'error': 'Invalid request. Please try again.'
        }), 400

    # Validate latitude
    lat = data.get('latitude')
    lon = data.get('longitude')

    if lat is None or lon is None:
        return jsonify({
            'success': False,
            'error': 'Location coordinates are required. Please enable location services.'
        }), 400

    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return jsonify({
            'success': False,
            'error': 'Invalid location coordinates.'
        }), 400

    if lat < -90 or lat > 90:
        return jsonify({
            'success': False,
            'error': 'Invalid latitude value.'
        }), 400

    if lon < -180 or lon > 180:
        return jsonify({
            'success': False,
            'error': 'Invalid longitude value.'
        }), 400

    # Validate message
    raw_msg = data.get('message')
    message = raw_msg.strip() if isinstance(raw_msg, str) and raw_msg.strip() else None

    if message and len(message) > MAX_MESSAGE_LENGTH:
        return jsonify({
            'success': False,
            'error': f'Message is too long. Maximum {MAX_MESSAGE_LENGTH} characters.'
        }), 400

    # Determine user_id (None for anonymous SOS)
    user_id = session.get('user_id', None)

    # Create the SOS request using existing model
    db_path = current_app.config['DATABASE']
    sos_id = create_sos_request(
        db_path=db_path,
        latitude=lat,
        longitude=lon,
        message=message,
        user_id=user_id
    )

    if sos_id is None:
        return jsonify({
            'success': False,
            'error': 'Unable to create SOS request. Please try again.'
        }), 500

    return jsonify({
        'success': True,
        'sos_id': sos_id,
        'status': 'pending'
    })



# ============================================================
# API Route — Nearby Emergency Facilities
# ============================================================

@sos_bp.route('/api/sos/nearby')
def api_nearby_emergency():
    """
    GET /api/sos/nearby?latitude=<lat>&longitude=<lon>

    Returns nearby medical and emergency facilities sorted by distance.
    Reuses existing facility data.
    """
    import math

    lat = request.args.get('latitude')
    lon = request.args.get('longitude')

    if lat is None or lon is None:
        return jsonify([])

    try:
        user_lat = float(lat)
        user_lon = float(lon)
    except (TypeError, ValueError):
        return jsonify([])

    db_path = current_app.config['DATABASE']
    all_facilities = get_all_facilities(db_path)

    # Filter to medical and emergency facilities
    emergency_types = {'medical', 'emergency'}
    relevant = []

    for f in all_facilities:
        if f['type'] in emergency_types:
            # Haversine distance calculation
            dist = _haversine(user_lat, user_lon, f['latitude'], f['longitude'])
            relevant.append({
                'id': f['id'],
                'name': f['name'],
                'type': f['type'],
                'latitude': f['latitude'],
                'longitude': f['longitude'],
                'description': f['description'],
                'distance_km': round(dist, 1)
            })

    # Sort by distance
    relevant.sort(key=lambda x: x['distance_km'])

    return jsonify(relevant)


def _haversine(lat1, lon1, lat2, lon2):
    """Haversine formula — approximate distance in km between two GPS points."""
    import math
    R = 6371
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = (math.sin(dLat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dLon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

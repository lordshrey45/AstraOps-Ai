"""
Facility Routes — Flask Blueprint for the Nearby Facilities module.

Serves the facilities page and provides API endpoints for facility data.

Page Routes:
    GET /facilities — Facilities listing page

API Routes:
    GET /api/facilities — Facilities data (JSON), optionally filtered by type
"""

from flask import Blueprint, render_template, jsonify, request, current_app
from models.facility_model import get_all_facilities, get_facilities_by_type


# Create the Blueprint
facility_bp = Blueprint('facility', __name__)


# ============================================================
# Page Route
# ============================================================

@facility_bp.route('/facilities')
def facilities_page():
    """
    Nearby Facilities page.
    Renders the facility listing with search, filters, and mini-map.
    Data is loaded dynamically via fetch calls from facilities.js.
    """
    return render_template('facilities.html')


# ============================================================
# API Route — Facilities
# ============================================================

@facility_bp.route('/api/facilities')
def api_facilities():
    """
    GET /api/facilities — Returns facilities as JSON.

    Query Parameters:
        type (optional): Filter by facility type.
            Values: medical, food, water, toilet, shelter, emergency
        lat (optional): User latitude (for future distance sorting).
        lng (optional): User longitude (for future distance sorting).

    Returns:
        JSON array of facility objects.
    """
    db_path = current_app.config['DATABASE']

    # Optional type filter
    facility_type = request.args.get('type', '').strip().lower()

    if facility_type and facility_type != 'all':
        facilities = get_facilities_by_type(db_path, facility_type)
    else:
        facilities = get_all_facilities(db_path)

    # Convert sqlite3.Row objects to JSON-serializable dicts
    result = []
    for f in facilities:
        result.append({
            'id': f['id'],
            'name': f['name'],
            'type': f['type'],
            'latitude': f['latitude'],
            'longitude': f['longitude'],
            'description': f['description']
        })

    return jsonify(result)

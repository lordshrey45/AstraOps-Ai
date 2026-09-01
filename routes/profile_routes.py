"""
Profile Routes — Flask Blueprint for the User Profile module.

Serves the profile page and provides profile API endpoints.

Page Routes:
    GET /profile — Profile page (requires authentication)

API Routes:
    GET  /api/profile — Get current user's profile data
    PUT  /api/profile — Update current user's profile fields
"""

from flask import Blueprint, render_template, request, jsonify, session, current_app
from routes.auth_routes import login_required
from models.user_model import get_user_by_id, update_user
from models.sos_model import get_sos_requests_by_user


# Create the Blueprint
profile_bp = Blueprint('profile', __name__)

# Validation limits
MAX_NAME_LENGTH = 100
MAX_PHONE_LENGTH = 20
MAX_EMERGENCY_CONTACT_LENGTH = 100
MAX_MEDICAL_INFO_LENGTH = 500


# ============================================================
# Page Route
# ============================================================

@profile_bp.route('/profile')
@login_required
def profile_page():
    """
    Profile page — requires authentication.
    Displays user info, emergency information, and SOS history.
    """
    db_path = current_app.config['DATABASE']
    user = get_user_by_id(db_path, session['user_id'])

    # Get SOS history
    sos_history = []
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

    return render_template('profile.html', user=user, sos_history=sos_history)


# ============================================================
# API — Get Profile
# ============================================================

@profile_bp.route('/api/profile')
@login_required
def api_get_profile():
    """
    GET /api/profile — Returns the authenticated user's profile.

    The user is determined from the server-side session.
    Never returns password_hash.
    """
    db_path = current_app.config['DATABASE']
    user = get_user_by_id(db_path, session['user_id'])

    if not user:
        return jsonify({'success': False, 'error': 'User not found.'}), 404

    return jsonify({
        'success': True,
        'profile': {
            'name': user['name'],
            'phone': user['phone'],
            'emergency_contact': user['emergency_contact'] or '',
            'medical_info': user['medical_info'] or '',
            'created_at': user['created_at']
        }
    })


# ============================================================
# API — Update Profile
# ============================================================

@profile_bp.route('/api/profile', methods=['PUT'])
@login_required
def api_update_profile():
    """
    PUT /api/profile — Update the authenticated user's profile fields.

    Request JSON:
        {
            "name": "...",
            "emergency_contact": "...",
            "medical_info": "..."
        }

    The user is determined from the server-side session.
    Never accepts user_id from the client.
    """
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'error': 'Invalid request.'}), 400

    # Extract and validate fields
    name = data.get('name', '').strip() if data.get('name') is not None else None
    emergency_contact = data.get('emergency_contact', '').strip() if data.get('emergency_contact') is not None else None
    medical_info = data.get('medical_info', '').strip() if data.get('medical_info') is not None else None

    # Validate name
    if name is not None:
        if not name:
            return jsonify({'success': False, 'error': 'Name cannot be empty.'}), 400
        if len(name) > MAX_NAME_LENGTH:
            return jsonify({'success': False, 'error': f'Name is too long. Maximum {MAX_NAME_LENGTH} characters.'}), 400

    # Validate emergency contact
    if emergency_contact is not None and len(emergency_contact) > MAX_EMERGENCY_CONTACT_LENGTH:
        return jsonify({'success': False, 'error': f'Emergency contact is too long. Maximum {MAX_EMERGENCY_CONTACT_LENGTH} characters.'}), 400

    # Validate medical info
    if medical_info is not None and len(medical_info) > MAX_MEDICAL_INFO_LENGTH:
        return jsonify({'success': False, 'error': f'Medical information is too long. Maximum {MAX_MEDICAL_INFO_LENGTH} characters.'}), 400

    # Update using existing model — user_id from session only
    db_path = current_app.config['DATABASE']
    success = update_user(
        db_path=db_path,
        user_id=session['user_id'],
        name=name,
        emergency_contact=emergency_contact,
        medical_info=medical_info
    )

    if success:
        # Update session name if changed
        if name:
            session['user_name'] = name

        return jsonify({'success': True, 'message': 'Profile updated successfully.'})
    else:
        return jsonify({'success': False, 'error': 'Unable to update profile. Please try again.'}), 500

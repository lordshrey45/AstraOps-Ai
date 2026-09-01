"""
Volunteer Routes — Flask Blueprint for Volunteer Operations and Location Management (Phase 33 & 34).

Routes:
    GET  /volunteer               — Volunteer Operations Dashboard
    GET  /volunteer/profile       — Volunteer Profile View
    POST /volunteer/status        — Update availability status (AVAILABLE / OFF DUTY)
    POST /api/volunteer/status    — API update availability status
    POST /api/volunteer/location  — Secure GPS location submission for authenticated volunteers
    GET  /api/volunteer/location  — Get authenticated volunteer's own current location
    POST /api/volunteer/stop-sharing — Stop location sharing
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, session, current_app
from routes.auth_routes import volunteer_required
from models.volunteer_model import (
    get_volunteer_by_user_id, create_volunteer, update_volunteer_location,
    set_volunteer_availability, set_volunteer_sharing, calculate_freshness
)
from models.user_model import get_user_by_id

volunteer_bp = Blueprint('volunteer', __name__)


@volunteer_bp.route('/volunteer')
@volunteer_bp.route('/volunteer/dashboard')
@volunteer_required
def volunteer_dashboard():
    """
    GET /volunteer — Dedicated Volunteer Operations Dashboard (Phase 33 & Phase 3).
    """
    user_id = session.get('user_id')
    db_path = current_app.config['DATABASE']

    volunteer = get_volunteer_by_user_id(db_path, user_id)
    if not volunteer:
        # If user has volunteer flag but no volunteer row, auto-create linked record
        user = get_user_by_id(db_path, user_id)
        if user:
            vol_id = create_volunteer(db_path, user['name'], user['phone'], user_id=user['id'])
            volunteer = get_volunteer_by_user_id(db_path, user_id)

    if not volunteer:
        flash('Volunteer record not found.', 'danger')
        return redirect(url_for('home.home'))

    freshness, _ = calculate_freshness(volunteer['location_updated_at'], volunteer['status'])
    
    # Fetch active emergencies assigned to this volunteer (Phase 33)
    from models.volunteer_assignment_model import get_assignments_for_volunteer, format_approx_distance
    from models.volunteer_model import haversine_distance
    from services.location_service import get_location_name

    assignments = get_assignments_for_volunteer(db_path, volunteer['id'])
    for a in assignments:
        a['location_name'] = get_location_name(a['sos_latitude'], a['sos_longitude'])
        dist_km = None
        if volunteer['latitude'] is not None and volunteer['longitude'] is not None and a['sos_latitude'] is not None and a['sos_longitude'] is not None:
            dist_km = haversine_distance(volunteer['latitude'], volunteer['longitude'], a['sos_latitude'], a['sos_longitude'])
        a['distance_km'] = dist_km
        a['distance_str'] = format_approx_distance(dist_km)

    return render_template(
        'volunteer/dashboard.html',
        volunteer=volunteer,
        freshness=freshness,
        assignments=assignments
    )




@volunteer_bp.route('/volunteer/profile')
@volunteer_required
def volunteer_profile():
    """
    GET /volunteer/profile — Dedicated Volunteer Profile View (Phase 33).
    """
    user_id = session.get('user_id')
    db_path = current_app.config['DATABASE']

    volunteer = get_volunteer_by_user_id(db_path, user_id)
    if not volunteer:
        flash('Volunteer profile not found.', 'danger')
        return redirect(url_for('volunteer.volunteer_dashboard'))

    return render_template(
        'volunteer/profile.html',
        volunteer=volunteer
    )


@volunteer_bp.route('/volunteer/status', methods=['POST'])
@volunteer_bp.route('/api/volunteer/status', methods=['POST', 'GET'])
@volunteer_required
def set_availability():
    """
    POST /volunteer/status & /api/volunteer/status — Update volunteer operational availability (AVAILABLE / OFF DUTY).
    GET  /api/volunteer/status — Return current volunteer status.
    """
    user_id = session.get('user_id')
    db_path = current_app.config['DATABASE']

    if request.method == 'GET':
        vol = get_volunteer_by_user_id(db_path, user_id)
        if not vol:
            return jsonify({'success': False, 'error': 'Volunteer not found'}), 404
        freshness, delta = calculate_freshness(vol['location_updated_at'], vol['status'])
        avail = vol['availability'] if 'availability' in vol.keys() else 'AVAILABLE'
        return jsonify({
            'success': True,
            'volunteer_id': vol['id'],
            'status': vol['status'],
            'availability': avail,
            'is_sharing': vol['is_sharing'] if 'is_sharing' in vol.keys() else 0,
            'freshness': freshness,
            'delta_seconds': delta,
            'volunteer': {
                'id': vol['id'],
                'name': vol['name'],
                'phone': vol['phone'],
                'status': vol['status'],
                'availability': avail,
                'is_sharing': vol['is_sharing'] if 'is_sharing' in vol.keys() else 0,
                'freshness': freshness,
                'delta_seconds': delta
            }
        }), 200


    # Handle POST
    data = request.get_json(silent=True) or request.form
    availability = data.get('availability', '').strip().upper()
    if availability not in ['AVAILABLE', 'OFF DUTY', 'ACTIVE', 'INACTIVE']:
        availability = 'AVAILABLE'

    success = set_volunteer_availability(db_path, user_id, availability)
    if not success:
        return jsonify({'success': False, 'error': 'Failed to update availability'}), 500

    try:
        from models.admin_activity_model import create_admin_activity
        create_admin_activity(
            db_path=db_path,
            admin_user_id=user_id,
            action_type='VOLUNTEER_STATUS_CHANGED',
            description=f"Volunteer updated availability to '{availability}'.",
            entity_type='VOLUNTEER',
            entity_id=user_id
        )
    except Exception:
        pass

    if request.is_json:
        return jsonify({'success': True, 'availability': availability}), 200

    flash(f'Availability set to {availability}.', 'success')
    return redirect(url_for('volunteer.volunteer_dashboard'))


@volunteer_bp.route('/api/volunteer/location', methods=['POST', 'GET'])
@volunteer_required
def submit_volunteer_location():
    """
    POST /api/volunteer/location — Update current volunteer location.
    GET  /api/volunteer/location — Retrieve authenticated volunteer's own last known location.
    """
    user_id = session.get('user_id')
    db_path = current_app.config['DATABASE']

    volunteer = get_volunteer_by_user_id(db_path, user_id)
    if not volunteer or volunteer['status'] != 'ACTIVE':
        return jsonify({
            'success': False,
            'error': 'Volunteer authorization required or account inactive'
        }), 403

    if request.method == 'GET':
        freshness, delta = calculate_freshness(volunteer['location_updated_at'], volunteer['status'])
        return jsonify({
            'success': True,
            'volunteer_id': volunteer['id'],
            'name': volunteer['name'],
            'latitude': volunteer['latitude'],
            'longitude': volunteer['longitude'],
            'accuracy': volunteer['accuracy'] if 'accuracy' in volunteer.keys() else None,
            'is_sharing': volunteer['is_sharing'] if 'is_sharing' in volunteer.keys() else 0,
            'availability': volunteer['availability'] if 'availability' in volunteer.keys() else 'AVAILABLE',
            'freshness': freshness,
            'delta_seconds': delta,
            'location_updated_at': str(volunteer['location_updated_at']) if volunteer['location_updated_at'] else None
        }), 200

    # POST Location
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({
            'success': False,
            'error': 'Invalid request body'
        }), 400

    if 'latitude' not in data or 'longitude' not in data:
        return jsonify({
            'success': False,
            'error': 'Missing coordinates'
        }), 400

    try:
        latitude = float(data['latitude'])
        longitude = float(data['longitude'])
    except (ValueError, TypeError):
        return jsonify({
            'success': False,
            'error': 'Invalid coordinates format'
        }), 400

    # Validate coordinate boundaries
    if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
        return jsonify({
            'success': False,
            'error': 'Coordinates out of valid range (-90 to 90 lat, -180 to 180 lon)'
        }), 400

    accuracy = None
    if 'accuracy' in data and data['accuracy'] is not None:
        try:
            accuracy = float(data['accuracy'])
            if accuracy < 0 or accuracy > 100000:
                return jsonify({
                    'success': False,
                    'error': 'Invalid accuracy value'
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'Accuracy must be numeric'
            }), 400

    # Update database record and set is_sharing=1
    updated = update_volunteer_location(db_path, user_id, latitude, longitude, accuracy=accuracy, is_sharing=1)
    if not updated:
        return jsonify({
            'success': False,
            'error': 'Failed to update location'
        }), 500

    return jsonify({
        'success': True,
        'message': 'Location updated successfully.',
        'volunteer_id': volunteer['id'],
        'latitude': latitude,
        'longitude': longitude,
        'accuracy': accuracy
    }), 200



@volunteer_bp.route('/api/volunteer/stop-sharing', methods=['POST'])
@volunteer_bp.route('/volunteer/stop-sharing', methods=['POST'])
@volunteer_required
def stop_volunteer_sharing():
    """
    POST /api/volunteer/stop-sharing — Explicitly stop location sharing (Phase 33).
    """
    user_id = session.get('user_id')
    db_path = current_app.config['DATABASE']

    set_volunteer_sharing(db_path, user_id, is_sharing=0)
    if request.path.startswith('/api/') or request.is_json:
        return jsonify({'success': True, 'message': 'Location sharing stopped.'}), 200

    flash('Location sharing stopped.', 'info')
    return redirect(url_for('volunteer.volunteer_dashboard'))


# ============================================================
# Phase 3 — Volunteer Emergency Response Endpoints
# ============================================================

@volunteer_bp.route('/api/volunteer/sos/<int:sos_id>/acknowledge', methods=['POST'])
@volunteer_required
def volunteer_acknowledge_sos(sos_id):
    """
    POST /api/volunteer/sos/<sos_id>/acknowledge — Volunteer acknowledges assigned emergency.
    Strict IDOR protection: only the assigned volunteer can acknowledge.
    """
    user_id = session.get('user_id')
    db_path = current_app.config['DATABASE']

    vol = get_volunteer_by_user_id(db_path, user_id)
    if not vol:
        return jsonify({'success': False, 'error': 'Volunteer account not found'}), 403

    from models.sos_model import get_sos_request_by_id, acknowledge_sos_request
    sos = get_sos_request_by_id(db_path, sos_id)
    if not sos:
        return jsonify({'success': False, 'error': f'Emergency #{sos_id} not found'}), 404

    # IDOR Check
    if sos.get('assigned_volunteer_id') != vol['id']:
        return jsonify({'success': False, 'error': 'Unauthorized: Emergency is not assigned to you.'}), 403

    if sos.get('status') == 'resolved':
        return jsonify({'success': False, 'error': 'Emergency is already resolved.'}), 400

    success = acknowledge_sos_request(db_path, sos_id)
    if success:
        try:
            from models.admin_activity_model import create_admin_activity
            create_admin_activity(
                db_path=db_path,
                admin_user_id=user_id,
                action_type='SOS_ACKNOWLEDGED',
                description=f"Volunteer '{vol['name']}' acknowledged emergency #{sos_id}.",
                entity_type='SOS',
                entity_id=sos_id
            )
        except Exception:
            pass
        return jsonify({'success': True, 'message': f'Emergency #{sos_id} acknowledged.'}), 200

    return jsonify({'success': False, 'error': 'Failed to acknowledge emergency.'}), 500


@volunteer_bp.route('/api/volunteer/sos/<int:sos_id>/respond', methods=['POST'])
@volunteer_required
def volunteer_respond_sos(sos_id):
    """
    POST /api/volunteer/sos/<sos_id>/respond — Volunteer indicates response in progress.
    Strict IDOR protection: only the assigned volunteer can update status.
    """
    user_id = session.get('user_id')
    db_path = current_app.config['DATABASE']

    vol = get_volunteer_by_user_id(db_path, user_id)
    if not vol:
        return jsonify({'success': False, 'error': 'Volunteer account not found'}), 403

    from models.sos_model import get_sos_request_by_id, update_sos_dispatch_status
    sos = get_sos_request_by_id(db_path, sos_id)
    if not sos:
        return jsonify({'success': False, 'error': f'Emergency #{sos_id} not found'}), 404

    # IDOR Check
    if sos.get('assigned_volunteer_id') != vol['id']:
        return jsonify({'success': False, 'error': 'Unauthorized: Emergency is not assigned to you.'}), 403

    if sos.get('status') == 'resolved':
        return jsonify({'success': False, 'error': 'Emergency is already resolved.'}), 400

    success = update_sos_dispatch_status(db_path, sos_id, 'IN_PROGRESS')
    if success:
        try:
            from models.admin_activity_model import create_admin_activity
            create_admin_activity(
                db_path=db_path,
                admin_user_id=user_id,
                action_type='SOS_STATUS_CHANGED',
                description=f"Volunteer '{vol['name']}' started response for emergency #{sos_id} (IN_PROGRESS).",
                entity_type='SOS',
                entity_id=sos_id
            )
        except Exception:
            pass
        return jsonify({'success': True, 'message': f'Response in progress for Emergency #{sos_id}.'}), 200

    return jsonify({'success': False, 'error': 'Failed to update emergency response status.'}), 500


@volunteer_bp.route('/api/volunteer/sos/<int:sos_id>/resolve', methods=['POST'])
@volunteer_required
def volunteer_resolve_sos(sos_id):
    """
    POST /api/volunteer/sos/<sos_id>/resolve — Volunteer marks assigned emergency as resolved upon assistance.
    Strict IDOR protection: only the assigned volunteer can resolve their assignment.
    """
    user_id = session.get('user_id')
    db_path = current_app.config['DATABASE']

    vol = get_volunteer_by_user_id(db_path, user_id)
    if not vol:
        return jsonify({'success': False, 'error': 'Volunteer account not found'}), 403

    from models.sos_model import get_sos_request_by_id, resolve_sos_request
    sos = get_sos_request_by_id(db_path, sos_id)
    if not sos:
        return jsonify({'success': False, 'error': f'Emergency #{sos_id} not found'}), 404

    # IDOR Check
    if sos.get('assigned_volunteer_id') != vol['id']:
        return jsonify({'success': False, 'error': 'Unauthorized: Emergency is not assigned to you.'}), 403

    if sos.get('status') == 'resolved':
        return jsonify({'success': False, 'error': 'Emergency is already resolved.'}), 400

    data = request.get_json(silent=True) or request.form
    notes = data.get('notes', f"Assisted on ground by volunteer '{vol['name']}'.")

    success = resolve_sos_request(db_path, sos_id, resolved_by=user_id, notes=notes)
    if success:
        try:
            from models.admin_activity_model import create_admin_activity
            create_admin_activity(
                db_path=db_path,
                admin_user_id=user_id,
                action_type='SOS_RESOLVED',
                description=f"Volunteer '{vol['name']}' resolved emergency #{sos_id}.",
                entity_type='SOS',
                entity_id=sos_id
            )
        except Exception:
            pass
        return jsonify({'success': True, 'message': f'Emergency #{sos_id} marked as RESOLVED.'}), 200

    return jsonify({'success': False, 'error': 'Failed to resolve emergency.'}), 500


# ============================================================
# Phase 33 — Volunteer Emergency Assignment Endpoints
# ============================================================

@volunteer_bp.route('/volunteer/assignments', methods=['GET'])
@volunteer_required
def volunteer_assignments_list():
    """
    GET /volunteer/assignments — View active and past emergency assignments for this volunteer.
    """
    user_id = session.get('user_id')
    db_path = current_app.config['DATABASE']

    vol = get_volunteer_by_user_id(db_path, user_id)
    if not vol:
        return jsonify({'success': False, 'error': 'Volunteer account not found'}), 403

    from models.volunteer_assignment_model import get_assignments_for_volunteer, format_approx_distance
    from models.volunteer_model import haversine_distance
    from services.location_service import get_location_name

    assignments = get_assignments_for_volunteer(db_path, vol['id'])
    for a in assignments:
        a['location_name'] = get_location_name(a['sos_latitude'], a['sos_longitude'])
        dist_km = None
        if vol['latitude'] is not None and vol['longitude'] is not None and a['sos_latitude'] is not None and a['sos_longitude'] is not None:
            dist_km = haversine_distance(vol['latitude'], vol['longitude'], a['sos_latitude'], a['sos_longitude'])
        a['distance_km'] = dist_km
        a['distance_str'] = format_approx_distance(dist_km)

    if request.is_json or (request.content_type and 'application/json' in request.content_type):
        return jsonify({'success': True, 'assignments': assignments}), 200

    return redirect(url_for('volunteer.volunteer_dashboard'))


@volunteer_bp.route('/volunteer/assignments/<int:assignment_id>/accept', methods=['POST'])
@volunteer_required
def volunteer_accept_assignment_endpoint(assignment_id):
    """
    POST /volunteer/assignments/<id>/accept — Volunteer accepts an assigned emergency incident.
    """
    user_id = session.get('user_id')
    db_path = current_app.config['DATABASE']
    is_json = request.is_json or (request.content_type and 'application/json' in request.content_type) or (request.headers.get('Accept') and 'application/json' in request.headers.get('Accept'))

    from models.volunteer_assignment_model import accept_assignment
    success, message = accept_assignment(db_path, assignment_id, user_id)

    if success:
        if is_json:
            return jsonify({'success': True, 'message': message}), 200
        flash(message, 'success')
    else:
        status_code = 403 if 'Access denied' in message else 400
        if is_json:
            return jsonify({'success': False, 'error': message}), status_code
        flash(message, 'danger')

    return redirect(url_for('volunteer.volunteer_dashboard'))


@volunteer_bp.route('/volunteer/assignments/<int:assignment_id>/decline', methods=['POST'])
@volunteer_required
def volunteer_decline_assignment_endpoint(assignment_id):
    """
    POST /volunteer/assignments/<id>/decline — Volunteer declines an assigned emergency incident.
    """
    user_id = session.get('user_id')
    db_path = current_app.config['DATABASE']
    is_json = request.is_json or (request.content_type and 'application/json' in request.content_type) or (request.headers.get('Accept') and 'application/json' in request.headers.get('Accept'))

    data = request.get_json(silent=True) or request.form
    reason = data.get('reason')

    from models.volunteer_assignment_model import decline_assignment
    success, message = decline_assignment(db_path, assignment_id, user_id, reason=reason)

    if success:
        if is_json:
            return jsonify({'success': True, 'message': message}), 200
        flash(message, 'info')
    else:
        status_code = 403 if 'Access denied' in message else 400
        if is_json:
            return jsonify({'success': False, 'error': message}), status_code
        flash(message, 'danger')

    return redirect(url_for('volunteer.volunteer_dashboard'))


@volunteer_bp.route('/volunteer/assignments/<int:assignment_id>/complete', methods=['POST'])
@volunteer_required
def volunteer_complete_assignment_endpoint(assignment_id):
    """
    POST /volunteer/assignments/<id>/complete — Volunteer marks emergency assistance as completed.
    Does NOT resolve the SOS incident (Admin retains authority to verify and mark resolved).
    """
    user_id = session.get('user_id')
    db_path = current_app.config['DATABASE']
    is_json = request.is_json or (request.content_type and 'application/json' in request.content_type) or (request.headers.get('Accept') and 'application/json' in request.headers.get('Accept'))

    data = request.get_json(silent=True) or request.form
    notes = data.get('notes')

    from models.volunteer_assignment_model import complete_assignment
    success, message = complete_assignment(db_path, assignment_id, user_id, notes=notes)

    if success:
        if is_json:
            return jsonify({'success': True, 'message': message}), 200
        flash(message, 'success')
    else:
        status_code = 403 if 'Access denied' in message else 400
        if is_json:
            return jsonify({'success': False, 'error': message}), status_code
        flash(message, 'danger')

    return redirect(url_for('volunteer.volunteer_dashboard'))





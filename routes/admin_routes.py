"""
Admin Routes — Flask Blueprint for the Admin Command & Control Panel.

Provides the separate Admin Dashboard foundation & real-time operational summary (Phase 21).
All admin routes are protected by the @admin_required decorator.

Routes:
    GET /admin        — Admin Dashboard Home & Operational Summary
    GET /admin/logout — Admin Logout Handler
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, jsonify
from routes.auth_routes import admin_required
from models.user_model import (
    get_all_users, get_user_by_id, get_user_account_status,
    set_user_active_status, count_active_admins
)

from models.sos_model import (
    get_all_sos_requests, get_pending_sos_requests,
    get_sos_request_by_id, resolve_sos_request,
    acknowledge_sos_request, update_sos_priority,
    update_sos_dispatch_status, assign_volunteer_to_sos,
    detect_incident_clusters
)

from models.facility_model import (
    get_all_facilities, get_facility_by_id, create_facility,
    update_facility, delete_facility
)
from models.schedule_model import get_full_schedule
from models.admin_activity_model import (
    create_admin_activity, get_all_admin_activities,
    get_filtered_admin_activities, get_activity_stats,
    get_recent_admin_activities
)
from models.volunteer_model import (
    get_all_volunteers, get_volunteer_by_id, set_volunteer_status,
    calculate_freshness, create_volunteer, find_nearby_volunteers,
    assign_volunteer_to_sos
)
from models.volunteer_request_model import (
    create_volunteer_request, get_volunteer_request_by_id,
    get_all_volunteer_requests, count_pending_volunteer_requests,
    count_volunteer_requests_by_status, approve_volunteer_request,
    reject_volunteer_request
)
from services.location_service import get_location_name









# Create the Blueprint
admin_bp = Blueprint('admin', __name__)



@admin_bp.route('/admin')
@admin_bp.route('/admin/')
@admin_required
def admin_dashboard():
    """
    GET /admin — Phase 21 Admin Dashboard Home & Operational Summary.

    Provides a comprehensive real-time command & control center overview:
    - Real metric cards (users, SOS, pending SOS, facilities, schedule)
    - SOS Operational Summary & Status Distribution
    - Real chronological Recent Activity stream (SOS alerts + Pilgrim registrations)
    - System Infrastructure Health Indicators
    - Quick Action navigation placeholders for future admin phases
    """
    db_path = current_app.config['DATABASE']

    # Retrieve real database records (no fake data)
    all_users = get_all_users(db_path)
    all_sos = get_all_sos_requests(db_path)
    all_facilities = get_all_facilities(db_path)
    all_schedule = get_full_schedule(db_path)

    # Status distribution for SOS
    pending_sos = [s for s in all_sos if s['status'] == 'pending']
    resolved_sos = [s for s in all_sos if s['status'] == 'resolved']

    # Real stats dictionary
    stats = {
        'total_users': len(all_users),
        'total_sos': len(all_sos),
        'pending_sos': len(pending_sos),
        'resolved_sos': len(resolved_sos),
        'pending_volunteer_requests': count_pending_volunteer_requests(db_path),
        'total_facilities': len(all_facilities),
        'total_schedule_days': len(all_schedule)
    }


    # Operational SOS Summary
    latest_sos = all_sos[0] if all_sos else None
    latest_sos_loc = ''
    if latest_sos:
        latest_sos_loc = get_location_name(latest_sos['latitude'], latest_sos['longitude'])

    sos_summary = {
        'total': len(all_sos),
        'pending': len(pending_sos),
        'resolved': len(resolved_sos),
        'latest_time': latest_sos['created_at'] if latest_sos else None,
        'latest_location': latest_sos_loc,
        'latest_id': latest_sos['id'] if latest_sos else None
    }

    # Build real chronological Recent Activity Stream
    activity_stream = []

    # Add SOS activities
    for s in all_sos[:8]:
        loc_name = get_location_name(s['latitude'], s['longitude'])
        caller = s['user_name'] if s['user_name'] else 'Anonymous Pilgrim'
        activity_stream.append({
            'timestamp': s['created_at'],
            'type': 'sos',
            'icon': 'bi-exclamation-triangle-fill text-danger',
            'title': f"Emergency SOS #{s['id']}",
            'description': f"Reported by {caller} at {loc_name}." + (f" Note: '{s['message']}'" if s['message'] else ""),
            'status_badge': 'bg-warning text-dark' if s['status'] == 'pending' else 'bg-success',
            'status_text': s['status'].upper()
        })

    # Add User registration activities
    for u in all_users[-8:]:
        activity_stream.append({
            'timestamp': u['created_at'],
            'type': 'user',
            'icon': 'bi-person-plus-fill text-primary',
            'title': f"New Pilgrim Registration: {u['name']}",
            'description': f"Phone: {u['phone']}" + (f" | Emergency: {u['emergency_contact']}" if u['emergency_contact'] else ""),
            'status_badge': 'bg-primary',
            'status_text': 'PILGRIM'
        })

    # Sort activity stream by timestamp descending (newest first)
    activity_stream.sort(key=lambda x: str(x['timestamp']), reverse=True)
    recent_activity = activity_stream[:10]

    # Enhanced Recent SOS list (latest 5)
    recent_sos = []
    for s in all_sos[:5]:
        recent_sos.append({
            'id': s['id'],
            'created_at': s['created_at'],
            'latitude': s['latitude'],
            'longitude': s['longitude'],
            'location_name': get_location_name(s['latitude'], s['longitude']),
            'user_name': s['user_name'] or 'Anonymous',
            'user_phone': s['user_phone'] or '—',
            'message': s['message'],
            'status': s['status']
        })

    # System Status overview
    system_status = {
        'database': 'Operational (SQLite)',
        'ai_assistant': 'Operational (Google Gemini)',
        'weather_api': 'Operational (Open-Meteo)',
        'location_service': 'Operational (Nominatim + Landmark Proximity)'
    }

    # Quick Action Navigation Placeholders & Active Links
    quick_actions = [
        {'title': 'SOS Management', 'icon': 'bi-exclamation-octagon-fill text-danger', 'phase': 'Phase 22', 'desc': 'Review & resolve emergency alerts', 'link': url_for('admin.admin_sos_list')},
        {'title': 'Volunteer Tracking', 'icon': 'bi-person-badge-fill text-primary', 'phase': 'Phase 2', 'desc': 'Monitor authorized volunteer locations and safety status', 'link': url_for('admin.admin_volunteer_list')},
        {'title': 'User Directory', 'icon': 'bi-people-fill text-info', 'phase': 'Phase 23', 'desc': 'Manage registered pilgrim profiles', 'link': url_for('admin.admin_user_list')},
        {'title': 'Ground Situation Map', 'icon': 'bi-map-fill text-warning', 'phase': 'Phase 24', 'desc': 'Live spatial tracking of halts & alerts', 'link': url_for('admin.admin_map')},
        {'title': 'Facility Registry', 'icon': 'bi-hospital-fill text-success', 'phase': 'Phase 25', 'desc': 'Update medical camps & food points', 'link': url_for('admin.admin_facility_list')},
        {'title': 'System Monitoring', 'icon': 'bi-cpu-fill text-info', 'phase': 'Phase 26', 'desc': 'Service health & operational checks', 'link': url_for('admin.admin_monitoring')},
        {'title': 'Activity History', 'icon': 'bi-clock-history text-secondary', 'phase': 'Phase 29', 'desc': 'Administrative audit trail', 'link': url_for('admin.admin_activity_list')}
    ]


    recent_admin_activities = get_recent_admin_activities(db_path, limit=5)

    return render_template(
        'admin/dashboard.html',
        stats=stats,
        sos_summary=sos_summary,
        recent_sos=recent_sos,
        recent_activity=recent_activity,
        recent_admin_activities=recent_admin_activities,
        system_status=system_status,
        quick_actions=quick_actions,
        admin_name=session.get('user_name', 'Admin')
    )


@admin_bp.route('/admin/logout')
def admin_logout():
    """
    GET /admin/logout — Admin Logout Handler.
    Clears session and redirects to login page.
    """
    admin_id = session.get('user_id')
    admin_name = session.get('user_name', 'Admin')
    if admin_id:
        try:
            db_path = current_app.config['DATABASE']
            create_admin_activity(
                db_path=db_path,
                admin_user_id=admin_id,
                action_type='ADMIN_LOGOUT',
                description=f"Administrator '{admin_name}' logged out.",
                entity_type='AUTH',
                entity_id=admin_id
            )
        except Exception as e:
            print(f"Audit log error during logout: {e}")

    session.clear()
    flash('Admin logged out successfully.', 'info')
    return redirect(url_for('auth.login'))



# ============================================================
# Phase 22 — Admin SOS Management Routes
# ============================================================

@admin_bp.route('/admin/sos')
@admin_required
def admin_sos_list():
    """
    GET /admin/sos — Phase 36 Admin Intelligent SOS Queue & Volunteer Response Coordination.

    Provides real-time emergency SOS monitoring, priority queues, nearby volunteer discovery,
    incident cluster awareness, and volunteer assignment:
    - Status filtering ('all', 'pending', 'assigned', 'resolved')
    - Priority filtering ('all', 'critical', 'high', 'normal')
    - Search query filtering (name, phone, message, location)
    - Queue metrics: Critical, High, Normal, Assigned, Oldest Unresolved, Newest Alert
    - Discovery of nearby active volunteers ranked by freshness and geographic distance
    - Spatial incident cluster detection
    - Admin manual volunteer assignment
    - Admin action to mark individual SOS as resolved
    """
    db_path = current_app.config['DATABASE']

    status_filter = request.args.get('filter', 'all').lower().strip()
    if status_filter not in ['all', 'pending', 'assigned', 'resolved']:
        status_filter = 'all'

    priority_filter = request.args.get('priority', 'ALL').upper().strip()
    if priority_filter not in ['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'NORMAL']:
        priority_filter = 'ALL'

    dispatch_filter = request.args.get('dispatch', 'ALL').upper().strip()
    if dispatch_filter not in ['ALL', 'UNASSIGNED', 'ASSIGNED', 'ACKNOWLEDGED', 'IN_PROGRESS', 'RESOLVED']:
        dispatch_filter = 'ALL'

    search_query = request.args.get('q', '').strip().lower()

    # Fetch all SOS requests with computed priority, dispatch status and age
    all_sos = get_all_sos_requests(db_path)

    # Detect incident clusters among active unresolved SOS requests
    clusters = detect_incident_clusters(all_sos, threshold_km=2.0)

    # All active registered volunteers for manual assignment dropdown
    all_vols = get_all_volunteers(db_path)
    active_volunteers = [v for v in all_vols if v['status'] == 'ACTIVE']

    # Queue Metrics
    total_count = len(all_sos)
    unresolved_list = [s for s in all_sos if s['status'] != 'resolved' and s.get('dispatch_status') != 'RESOLVED']
    pending_list = [s for s in all_sos if s['status'] == 'pending' and s.get('dispatch_status') in ('UNASSIGNED', None)]
    assigned_list = [s for s in all_sos if s.get('dispatch_status') == 'ASSIGNED' or (s['status'] == 'assigned' and s.get('assigned_volunteer_id'))]
    in_progress_list = [s for s in all_sos if s.get('dispatch_status') == 'IN_PROGRESS']
    acknowledged_list = [s for s in all_sos if s.get('dispatch_status') == 'ACKNOWLEDGED']
    resolved_list = [s for s in all_sos if s['status'] == 'resolved' or s.get('dispatch_status') == 'RESOLVED']

    critical_count = sum(1 for s in unresolved_list if s.get('priority') == 'CRITICAL')
    high_count = sum(1 for s in unresolved_list if s.get('priority') == 'HIGH')
    medium_count = sum(1 for s in unresolved_list if s.get('priority') in ('MEDIUM', 'NORMAL'))
    low_count = sum(1 for s in unresolved_list if s.get('priority') == 'LOW')

    newest_alert = all_sos[0]['created_at'] if all_sos else 'None'
    oldest_unresolved = unresolved_list[-1]['created_at'] if unresolved_list else 'None'

    # Apply filters & enhance with nearby volunteers & cluster metadata
    filtered_sos = []
    for s in all_sos:
        s_prio = s.get('priority', 'MEDIUM')
        if s_prio == 'NORMAL':
            s_prio = 'MEDIUM'
            
        s_dispatch = s.get('dispatch_status', 'UNASSIGNED')

        if status_filter == 'pending' and (s['status'] == 'resolved' or s_dispatch == 'RESOLVED'):
            continue
        if status_filter == 'assigned' and s_dispatch != 'ASSIGNED' and s['status'] != 'assigned':
            continue
        if status_filter == 'resolved' and s['status'] != 'resolved' and s_dispatch != 'RESOLVED':
            continue

        if priority_filter != 'ALL':
            if priority_filter == 'NORMAL' and s_prio not in ('NORMAL', 'MEDIUM'):
                continue
            elif priority_filter != 'NORMAL' and s_prio != priority_filter:
                continue

        if dispatch_filter != 'ALL' and s_dispatch != dispatch_filter:
            continue

        loc_name = get_location_name(s['latitude'], s['longitude'])

        # Apply search query
        if search_query:
            matched = (
                search_query in str(s['id']) or
                search_query in (s.get('user_name') or '').lower() or
                search_query in (s.get('user_phone') or '').lower() or
                search_query in (s.get('message') or '').lower() or
                search_query in (s.get('assigned_volunteer_name') or '').lower() or
                search_query in loc_name.lower()
            )
            if not matched:
                continue

        # Discover nearby volunteers for active incidents
        nearby_volunteers = []
        if s['status'] != 'resolved' and s_dispatch != 'RESOLVED' and s['latitude'] is not None and s['longitude'] is not None:
            nearby_volunteers = find_nearby_volunteers(db_path, s['latitude'], s['longitude'], max_distance_km=25.0)

        cluster_info = clusters.get(s['id'], {'in_cluster': False, 'cluster_count': 1})

        filtered_sos.append({
            'id': s['id'],
            'user_id': s['user_id'],
            'user_name': s['user_name'] or 'Anonymous Pilgrim',
            'user_phone': s['user_phone'] or '—',
            'user_emergency_contact': s.get('user_emergency_contact') or '—',
            'user_medical_info': s.get('user_medical_info') or '—',
            'assigned_volunteer_id': s.get('assigned_volunteer_id'),
            'assigned_volunteer_name': s.get('assigned_volunteer_name'),
            'assigned_volunteer_phone': s.get('assigned_volunteer_phone'),
            'assigned_volunteer_lat': s.get('assigned_volunteer_lat'),
            'assigned_volunteer_lon': s.get('assigned_volunteer_lon'),
            'latitude': s['latitude'],
            'longitude': s['longitude'],
            'location_name': loc_name,
            'message': s['message'],
            'status': s['status'],
            'priority': s_prio,
            'priority_reason': s.get('priority_reason') or 'Standard operational prioritization.',
            'dispatch_status': s_dispatch,
            'assigned_at': s.get('assigned_at'),
            'acknowledged_at': s.get('acknowledged_at'),
            'resolved_at': s.get('resolved_at'),
            'age_str': s.get('age_str') or calculate_emergency_age(s.get('created_at')),
            'is_repeated': s.get('is_repeated', False),
            'in_cluster': cluster_info['in_cluster'],
            'cluster_count': cluster_info['cluster_count'],
            'nearby_volunteers': nearby_volunteers,
            'created_at': s['created_at']
        })

    filter_stats = {
        'total': total_count,
        'unresolved': len(unresolved_list),
        'pending': len(pending_list),
        'assigned': len(assigned_list),
        'in_progress': len(in_progress_list),
        'acknowledged': len(acknowledged_list),
        'resolved': len(resolved_list),
        'critical': critical_count,
        'high': high_count,
        'medium': medium_count,
        'low': low_count,
        'newest_alert': newest_alert,
        'oldest_unresolved': oldest_unresolved,
        'current_filter': status_filter,
        'current_priority': priority_filter,
        'current_dispatch': dispatch_filter,
        'filtered_count': len(filtered_sos)
    }

    return render_template(
        'admin/sos_list.html',
        sos_list=filtered_sos,
        filter_stats=filter_stats,
        active_volunteers=active_volunteers,
        search_query=request.args.get('q', '').strip(),
        admin_name=session.get('user_name', 'Admin')
    )


@admin_bp.route('/admin/sos/<int:sos_id>/assign', methods=['POST'])
@admin_bp.route('/admin/sos/<int:sos_id>/assign-volunteer', methods=['POST'])
@admin_bp.route('/admin/sos/<int:sos_id>/assign-volunteer', methods=['POST'], endpoint='admin_assign_volunteer_to_sos')
@admin_required
def admin_assign_volunteer(sos_id):

    """
    POST /admin/sos/<sos_id>/assign & /admin/sos/<sos_id>/assign-volunteer — Assign or reassign a designated volunteer to an emergency SOS (Phase 33).
    """
    db_path = current_app.config['DATABASE']
    admin_id = session.get('user_id')
    is_json_req = request.is_json or (request.content_type and 'application/json' in request.content_type) or (request.headers.get('Accept') and 'application/json' in request.headers.get('Accept'))

    if is_json_req:
        data = request.get_json(silent=True) or {}
        volunteer_id = data.get('volunteer_id')
        notes = data.get('notes')
        if volunteer_id is not None:
            try:
                volunteer_id = int(volunteer_id)
            except Exception:
                volunteer_id = None
    else:
        volunteer_id = request.form.get('volunteer_id', type=int)
        notes = request.form.get('notes')

    if not volunteer_id:
        if is_json_req:
            return jsonify({'success': False, 'error': 'Valid volunteer_id required'}), 400
        flash('Please select a valid volunteer to assign.', 'warning')
        return redirect(url_for('admin.admin_sos_list', filter=request.args.get('filter', 'all')))

    from models.volunteer_assignment_model import create_assignment
    success, message, assignment_id = create_assignment(db_path, sos_id, volunteer_id, admin_id, notes=notes)

    if success:
        if is_json_req:
            return jsonify({'success': True, 'message': message, 'assignment_id': assignment_id}), 200
        flash(message, 'success')
    else:
        if is_json_req:
            return jsonify({'success': False, 'error': message}), 400
        flash(message, 'danger')

    return redirect(url_for('admin.admin_sos_list', filter=request.args.get('filter', 'all')))



@admin_bp.route('/admin/sos/<int:sos_id>/acknowledge', methods=['POST'])
@admin_required
def admin_acknowledge_sos(sos_id):
    """
    POST /admin/sos/<sos_id>/acknowledge — Admin acknowledges emergency SOS.
    """
    db_path = current_app.config['DATABASE']
    is_json_req = request.is_json or (request.content_type and 'application/json' in request.content_type) or (request.headers.get('Accept') and 'application/json' in request.headers.get('Accept'))

    sos = get_sos_request_by_id(db_path, sos_id)
    if not sos:
        if is_json_req:
            return jsonify({'success': False, 'error': 'SOS not found'}), 404
        flash(f'SOS request #{sos_id} not found.', 'danger')
        return redirect(url_for('admin.admin_sos_list'))

    if sos['status'] == 'resolved':
        if is_json_req:
            return jsonify({'success': False, 'error': 'SOS is already resolved'}), 400
        flash('SOS request is already resolved.', 'info')
        return redirect(url_for('admin.admin_sos_list'))

    success = acknowledge_sos_request(db_path, sos_id)
    if success:
        admin_id = session.get('user_id')
        try:
            create_admin_activity(
                db_path=db_path,
                admin_user_id=admin_id,
                action_type='SOS_ACKNOWLEDGED',
                description=f"Admin acknowledged Emergency SOS #{sos_id}.",
                entity_type='SOS',
                entity_id=sos_id
            )
        except Exception:
            pass

        if is_json_req:
            return jsonify({'success': True, 'message': f'Emergency #{sos_id} acknowledged.'}), 200
        flash(f'Emergency #{sos_id} acknowledged.', 'success')
    else:
        if is_json_req:
            return jsonify({'success': False, 'error': 'Failed to acknowledge'}), 500
        flash('Failed to acknowledge emergency.', 'danger')

    return redirect(url_for('admin.admin_sos_list'))


@admin_bp.route('/admin/sos/<int:sos_id>/priority', methods=['POST'])
@admin_required
def admin_update_priority(sos_id):
    """
    POST /admin/sos/<sos_id>/priority — Manually change priority of an emergency.
    """
    db_path = current_app.config['DATABASE']
    is_json_req = request.is_json or (request.content_type and 'application/json' in request.content_type) or (request.headers.get('Accept') and 'application/json' in request.headers.get('Accept'))

    if is_json_req:
        data = request.get_json(silent=True) or {}
        new_prio = (data.get('priority') or '').upper().strip()
        reason = data.get('reason')
    else:
        new_prio = (request.form.get('priority') or '').upper().strip()
        reason = request.form.get('reason')

    if new_prio not in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        if is_json_req:
            return jsonify({'success': False, 'error': 'Invalid priority level'}), 400
        flash('Invalid priority level selected.', 'warning')
        return redirect(url_for('admin.admin_sos_list'))

    reason = reason or f"Priority manually set to {new_prio} by Administrator."
    success = update_sos_priority(db_path, sos_id, new_prio, reason)
    if success:
        admin_id = session.get('user_id')
        try:
            create_admin_activity(
                db_path=db_path,
                admin_user_id=admin_id,
                action_type='SOS_PRIORITY_CHANGED',
                description=f"Admin updated priority for SOS #{sos_id} to '{new_prio}'.",
                entity_type='SOS',
                entity_id=sos_id
            )
        except Exception:
            pass

        if is_json_req:
            return jsonify({'success': True, 'priority': new_prio, 'reason': reason}), 200
        flash(f'Priority for SOS #{sos_id} updated to {new_prio}.', 'success')
    else:
        if is_json_req:
            return jsonify({'success': False, 'error': 'Failed to update priority'}), 500
        flash('Failed to update priority.', 'danger')

    return redirect(url_for('admin.admin_sos_list'))


@admin_bp.route('/admin/sos/<int:sos_id>/status', methods=['POST'])
@admin_required
def admin_update_dispatch_status(sos_id):
    """
    POST /admin/sos/<sos_id>/status — Update operational dispatch status.
    """
    db_path = current_app.config['DATABASE']
    is_json_req = request.is_json or (request.content_type and 'application/json' in request.content_type) or (request.headers.get('Accept') and 'application/json' in request.headers.get('Accept'))

    if is_json_req:
        data = request.get_json(silent=True) or {}
        new_status = (data.get('dispatch_status') or '').upper().strip()
    else:
        new_status = (request.form.get('dispatch_status') or '').upper().strip()

    if new_status not in ['UNASSIGNED', 'ASSIGNED', 'ACKNOWLEDGED', 'IN_PROGRESS', 'RESOLVED']:
        if is_json_req:
            return jsonify({'success': False, 'error': 'Invalid dispatch status'}), 400
        flash('Invalid dispatch status.', 'warning')
        return redirect(url_for('admin.admin_sos_list'))

    if new_status == 'RESOLVED':
        return admin_resolve_sos(sos_id)

    success = update_sos_dispatch_status(db_path, sos_id, new_status)
    if success:
        admin_id = session.get('user_id')
        try:
            create_admin_activity(
                db_path=db_path,
                admin_user_id=admin_id,
                action_type='SOS_STATUS_CHANGED',
                description=f"Admin updated dispatch status for SOS #{sos_id} to '{new_status}'.",
                entity_type='SOS',
                entity_id=sos_id
            )
        except Exception:
            pass

        if is_json_req:
            return jsonify({'success': True, 'dispatch_status': new_status}), 200
        flash(f'Dispatch status for SOS #{sos_id} set to {new_status}.', 'success')
    else:
        if is_json_req:
            return jsonify({'success': False, 'error': 'Failed to update status'}), 500
        flash('Failed to update dispatch status.', 'danger')

    return redirect(url_for('admin.admin_sos_list'))


@admin_bp.route('/admin/sos/<int:sos_id>/resolve', methods=['POST'])
@admin_required
def admin_resolve_sos(sos_id):
    """
    POST /admin/sos/<sos_id>/resolve — Mark an SOS request as resolved.
    """
    db_path = current_app.config['DATABASE']
    is_json_req = request.is_json or (request.content_type and 'application/json' in request.content_type) or (request.headers.get('Accept') and 'application/json' in request.headers.get('Accept'))

    # Validate SOS exists
    sos = get_sos_request_by_id(db_path, sos_id)
    if not sos:
        if is_json_req:
            return jsonify({'success': False, 'error': f'SOS request #{sos_id} not found'}), 404
        flash(f'SOS request #{sos_id} not found.', 'danger')
        return redirect(url_for('admin.admin_sos_list', filter=request.args.get('filter', 'all')))

    if sos['status'] == 'resolved':
        if is_json_req:
            return jsonify({'success': True, 'message': 'Already resolved'}), 200
        flash(f'SOS request #{sos_id} is already resolved.', 'info')
        return redirect(url_for('admin.admin_sos_list', filter=request.args.get('filter', 'all')))

    admin_id = session.get('user_id')
    if is_json_req:
        data = request.get_json(silent=True) or {}
        notes = data.get('notes', 'Resolved by Administrator via Control Panel.')
    else:
        notes = request.form.get('notes', 'Resolved by Administrator via Control Panel.')

    # Execute resolve update in database atomically
    success = resolve_sos_request(db_path, sos_id, resolved_by=admin_id, notes=notes)
    if success:
        try:
            create_admin_activity(
                db_path=db_path,
                admin_user_id=admin_id,
                action_type='SOS_RESOLVED',
                description=f"Admin resolved Emergency SOS request #{sos_id}.",
                entity_type='SOS',
                entity_id=sos_id
            )
        except Exception as e:
            print(f"Audit log error during SOS resolve: {e}")

        if is_json_req:
            return jsonify({'success': True, 'message': f'Emergency SOS #{sos_id} marked as RESOLVED.'}), 200

        flash(f'Emergency SOS #{sos_id} has been marked as RESOLVED.', 'success')
    else:
        if is_json_req:
            return jsonify({'success': False, 'error': f'Failed to resolve SOS #{sos_id}'}), 500
        flash(f'Failed to resolve SOS #{sos_id}. Please try again.', 'danger')

    return redirect(url_for('admin.admin_sos_list', filter=request.args.get('filter', 'all')))



@admin_bp.route('/admin/sos/<int:sos_id>/details', methods=['GET'])
@admin_required
def admin_sos_details(sos_id):
    """
    GET /admin/sos/<sos_id>/details — Returns full SOS record details for interactive panel.
    """
    db_path = current_app.config['DATABASE']
    sos = get_sos_request_by_id(db_path, sos_id)
    if not sos:
        return jsonify({'success': False, 'error': f'Emergency #{sos_id} not found'}), 404

    loc_name = get_location_name(sos['latitude'], sos['longitude'])
    sos['location_name'] = loc_name
    return jsonify({'success': True, 'sos': sos}), 200



# ============================================================
# Volunteer Request Management & Approval Workflow
# ============================================================

@admin_bp.context_processor
def inject_volunteer_request_counts():
    """Inject pending volunteer application counts into all admin templates."""
    try:
        db_path = current_app.config['DATABASE']
        pending_count = count_pending_volunteer_requests(db_path)
        return {'pending_vol_requests_count': pending_count}
    except Exception:
        return {'pending_vol_requests_count': 0}


@admin_bp.route('/admin/volunteer-requests')
@admin_required
def admin_volunteer_requests():
    """
    GET /admin/volunteer-requests — Review, search, and process field volunteer applications.
    """
    db_path = current_app.config['DATABASE']
    status_filter = request.args.get('status', 'ALL').upper().strip()
    search_query = request.args.get('q', '').strip()

    requests_list = get_all_volunteer_requests(db_path, status_filter=status_filter, search_query=search_query)
    filter_stats = count_volunteer_requests_by_status(db_path)
    filter_stats['current_filter'] = status_filter
    filter_stats['filtered_count'] = len(requests_list)

    return render_template(
        'admin/volunteer_requests.html',
        requests_list=requests_list,
        filter_stats=filter_stats,
        search_query=search_query,
        admin_name=session.get('user_name', 'Admin')
    )


@admin_bp.route('/admin/volunteer-requests/<int:request_id>/approve', methods=['POST'])
@admin_required
def admin_approve_volunteer(request_id):
    """
    POST /admin/volunteer-requests/<request_id>/approve — Admin approves volunteer application.
    """
    db_path = current_app.config['DATABASE']
    admin_id = session.get('user_id')
    is_json_req = request.is_json or (request.content_type and 'application/json' in request.content_type) or (request.headers.get('Accept') and 'application/json' in request.headers.get('Accept'))

    success, message, applicant = approve_volunteer_request(db_path, request_id, admin_id)
    if success:
        try:
            create_admin_activity(
                db_path=db_path,
                admin_user_id=admin_id,
                action_type='VOLUNTEER_APPROVED',
                description=f"Admin approved volunteer application #{request_id} for '{applicant['name']}' ({applicant['phone']}).",
                entity_type='VOLUNTEER_REQUEST',
                entity_id=request_id
            )
        except Exception as e:
            print(f"Audit log error during volunteer approval: {e}")

        if is_json_req:
            return jsonify({'success': True, 'message': message, 'applicant': applicant}), 200
        flash(message, 'success')
    else:
        if is_json_req:
            return jsonify({'success': False, 'error': message}), 400
        flash(message, 'warning')

    return redirect(url_for('admin.admin_volunteer_requests', status=request.args.get('status', 'ALL')))


@admin_bp.route('/admin/volunteer-requests/<int:request_id>/reject', methods=['POST'])
@admin_required
def admin_reject_volunteer(request_id):
    """
    POST /admin/volunteer-requests/<request_id>/reject — Admin rejects volunteer application.
    """
    db_path = current_app.config['DATABASE']
    admin_id = session.get('user_id')
    is_json_req = request.is_json or (request.content_type and 'application/json' in request.content_type) or (request.headers.get('Accept') and 'application/json' in request.headers.get('Accept'))

    if is_json_req:
        data = request.get_json(silent=True) or {}
        rejection_reason = data.get('reason')
    else:
        rejection_reason = request.form.get('reason')

    success, message, applicant = reject_volunteer_request(db_path, request_id, admin_id, rejection_reason=rejection_reason)
    if success:
        try:
            create_admin_activity(
                db_path=db_path,
                admin_user_id=admin_id,
                action_type='VOLUNTEER_REJECTED',
                description=f"Admin rejected volunteer application #{request_id}." + (f" Reason: {rejection_reason}" if rejection_reason else ""),
                entity_type='VOLUNTEER_REQUEST',
                entity_id=request_id
            )
        except Exception as e:
            print(f"Audit log error during volunteer rejection: {e}")

        if is_json_req:
            return jsonify({'success': True, 'message': message, 'applicant': applicant}), 200
        flash(message, 'info')
    else:
        if is_json_req:
            return jsonify({'success': False, 'error': message}), 400
        flash(message, 'warning')

    return redirect(url_for('admin.admin_volunteer_requests', status=request.args.get('status', 'ALL')))


@admin_bp.route('/admin/volunteer-requests/<int:request_id>/details', methods=['GET'])
@admin_required
def admin_volunteer_request_details(request_id):
    """
    GET /admin/volunteer-requests/<request_id>/details — JSON endpoint for applicant review modal.
    """
    db_path = current_app.config['DATABASE']
    req = get_volunteer_request_by_id(db_path, request_id)
    if not req:
        return jsonify({'success': False, 'error': f"Volunteer request #{request_id} not found."}), 404
    # Ensure sensitive credentials are never included
    req.pop('password_hash', None)
    return jsonify({'success': True, 'request': req}), 200





# ============================================================
# Phase 23 — Admin User Directory Routes
# ============================================================

@admin_bp.route('/admin/users')
@admin_required
def admin_user_list():
    """
    GET /admin/users — Phase 34 Admin User Management & Account Control Page.

    Provides a clean, searchable, role- and status-filtered directory of registered pilgrims, volunteers & admins:
    - Search by name or phone (query param 'q')
    - Role filtering ('all', 'admin', 'volunteer', 'regular', 'pilgrim')
    - Status filtering ('all', 'active', 'inactive')
    - Account enable/disable actions with safety rules
    - User details modal view (never exposes password_hash)
    """
    db_path = current_app.config['DATABASE']

    # Query parameters
    search_query = request.args.get('q', '').strip()
    role_filter = request.args.get('role', 'all').lower().strip()
    if role_filter not in ['all', 'admin', 'volunteer', 'regular', 'pilgrim']:
        role_filter = 'all'

    status_filter = request.args.get('status', 'all').lower().strip()
    if status_filter not in ['all', 'active', 'inactive']:
        status_filter = 'all'

    # Fetch all users (password_hash is excluded by get_all_users query)
    all_users = get_all_users(db_path)

    current_admin_id = session.get('user_id')
    processed_users = []
    admin_count = 0
    volunteer_count = 0
    pilgrim_count = 0
    active_count = 0
    inactive_count = 0

    for u_row in all_users:
        u = dict(u_row)
        is_active_val = 1 if ('is_active' not in u or u['is_active'] is None) else int(u['is_active'])
        if is_active_val == 1:
            active_count += 1
        else:
            inactive_count += 1

        is_admin = bool(u.get('is_admin'))
        is_vol = bool(u.get('is_volunteer')) or (u.get('volunteer_id') is not None and u.get('volunteer_status') == 'ACTIVE') or (u.get('volunteer_request_status') == 'APPROVED')

        if is_admin:
            role = 'ADMIN'
            admin_count += 1
        elif is_vol:
            role = 'VOLUNTEER'
            volunteer_count += 1
        else:
            role = 'PILGRIM'
            pilgrim_count += 1

        vol_approval = None
        if role == 'VOLUNTEER':
            vol_approval = 'APPROVED'
        elif u.get('volunteer_request_status') == 'PENDING':
            vol_approval = 'PENDING APPROVAL'

        processed_users.append({
            'id': u['id'],
            'name': u['name'],
            'phone': u['phone'],
            'emergency_contact': u['emergency_contact'] if u['emergency_contact'] else '—',
            'medical_info': u['medical_info'] if u['medical_info'] else '—',
            'is_admin': is_admin,
            'is_volunteer': (role == 'VOLUNTEER'),
            'role': role,
            'volunteer_approval': vol_approval,
            'is_active': is_active_val,
            'is_current_admin': (current_admin_id and u['id'] == current_admin_id),
            'created_at': u['created_at']
        })


    # Filter by role
    if role_filter == 'admin':
        filtered = [u for u in processed_users if u['role'] == 'ADMIN']
    elif role_filter == 'volunteer':
        filtered = [u for u in processed_users if u['role'] == 'VOLUNTEER']
    elif role_filter in ['regular', 'pilgrim']:
        filtered = [u for u in processed_users if u['role'] == 'PILGRIM']
    else:
        filtered = processed_users

    # Filter by status
    if status_filter == 'active':
        filtered = [u for u in filtered if u['is_active'] == 1]
    elif status_filter == 'inactive':
        filtered = [u for u in filtered if u['is_active'] == 0]

    # Filter by search query (name or phone)
    if search_query:
        q_lower = search_query.lower()
        filtered = [
            u for u in filtered
            if q_lower in u['name'].lower() or q_lower in u['phone'].lower()
        ]

    filter_stats = {
        'total': len(all_users),
        'admins': admin_count,
        'volunteers': volunteer_count,
        'regular': pilgrim_count,
        'pilgrims': pilgrim_count,
        'active': active_count,
        'inactive': inactive_count,
        'current_role': role_filter,
        'current_status': status_filter,
        'search_query': search_query
    }

    return render_template(
        'admin/user_list.html',
        users_list=filtered,
        filter_stats=filter_stats,
        admin_name=session.get('user_name', 'Admin')
    )


@admin_bp.route('/api/admin/users/<int:user_id>/details', methods=['GET'])
@admin_bp.route('/admin/users/<int:user_id>/details', methods=['GET'])
@admin_required
def api_admin_user_details(user_id):
    """
    GET /api/admin/users/<id>/details — JSON endpoint for user profile modal.
    Never exposes passwords, hashes, tokens, or session secrets.
    """
    db_path = current_app.config['DATABASE']
    user = get_user_by_id(db_path, user_id)
    if not user:
        return jsonify({'success': False, 'error': f"User #{user_id} not found."}), 404

    is_admin = bool(user['is_admin']) if ('is_admin' in user.keys() and user['is_admin']) else False
    is_vol = bool(user['is_volunteer']) if ('is_volunteer' in user.keys() and user['is_volunteer']) else False
    if not is_vol:
        from models.volunteer_model import get_volunteer_by_user_id
        v_rec = get_volunteer_by_user_id(db_path, user_id)
        if v_rec and v_rec['status'] == 'ACTIVE':
            is_vol = True

    if is_admin:
        role = 'ADMIN'
    elif is_vol:
        role = 'VOLUNTEER'
    else:
        role = 'PILGRIM'

    from models.volunteer_request_model import get_volunteer_request_by_user_id
    v_req = get_volunteer_request_by_user_id(db_path, user_id)
    vol_approval = 'APPROVED' if role == 'VOLUNTEER' else (v_req['status'] if v_req else None)

    is_active_val = 1 if ('is_active' not in user.keys() or user['is_active'] is None) else int(user['is_active'])

    data = {
        'id': user['id'],
        'name': user['name'],
        'phone': user['phone'],
        'emergency_contact': user['emergency_contact'] if user['emergency_contact'] else '—',
        'medical_info': user['medical_info'] if user['medical_info'] else '—',
        'is_admin': is_admin,
        'is_volunteer': (role == 'VOLUNTEER'),
        'role': role,
        'volunteer_approval': vol_approval,
        'is_active': is_active_val,
        'status_label': 'ACTIVE' if is_active_val == 1 else 'INACTIVE',
        'created_at': str(user['created_at']) if user['created_at'] else '—'
    }
    return jsonify({'success': True, 'user': data}), 200



@admin_bp.route('/admin/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def admin_toggle_user_status(user_id):
    """
    POST /admin/users/<user_id>/toggle-status — Enable or disable a user account.

    Safety protections:
    1. Admin cannot disable their own currently logged in account.
    2. Cannot disable the last active administrator account.
    3. Validates user exists in database.
    4. Records USER_DISABLED or USER_REACTIVATED in admin_activity_log.
    """
    db_path = current_app.config['DATABASE']
    current_admin_id = session.get('user_id')

    # Safety Rule 1: Self-disable protection
    if current_admin_id and int(user_id) == int(current_admin_id):
        flash('You cannot disable your own administrator account.', 'warning')
        return redirect(url_for('admin.admin_user_list', **request.args))

    # Validate target user exists
    user = get_user_by_id(db_path, user_id)
    if not user:
        flash(f'User #{user_id} not found.', 'danger')
        return redirect(url_for('admin.admin_user_list', **request.args))

    current_is_active = user['is_active'] if ('is_active' in user.keys() and user['is_active'] is not None) else 1
    current_is_active = int(current_is_active)
    is_target_admin = bool(user['is_admin']) if ('is_admin' in user.keys() and user['is_admin']) else False

    # Safety Rule 2: Last active admin protection
    if current_is_active == 1 and is_target_admin:
        active_admins = count_active_admins(db_path)
        if active_admins <= 1:
            flash('Cannot disable the last active administrator account.', 'danger')
            return redirect(url_for('admin.admin_user_list', **request.args))

    new_status = 0 if current_is_active == 1 else 1
    success = set_user_active_status(db_path, user_id, new_status)

    if success:
        if new_status == 0:
            flash(f'User #{user_id} ({user["name"]}) has been DISABLED.', 'warning')
            action_type = 'USER_DISABLED'
            desc = f"Admin disabled user #{user_id} ({user['name']})."
        else:
            flash(f'User #{user_id} ({user["name"]}) has been REACTIVATED.', 'success')
            action_type = 'USER_REACTIVATED'
            desc = f"Admin reactivated user #{user_id} ({user['name']})."

        # Record in admin_activity_log with fault isolation
        try:
            create_admin_activity(
                db_path=db_path,
                admin_user_id=current_admin_id,
                action_type=action_type,
                description=desc,
                entity_type='USER',
                entity_id=user_id
            )
        except Exception as e:
            print(f"Audit log error during toggle user status: {e}")
    else:
        flash(f'Failed to update status for user #{user_id}.', 'danger')

    return redirect(url_for('admin.admin_user_list', **request.args))



# ============================================================
# Phase 24 — Admin Ground Situation Map Route
# ============================================================

@admin_bp.route('/admin/map')
@admin_required
def admin_map():
    """
    GET /admin/map — Phase 24 Admin Ground Situation Map Page.

    Provides interactive spatial visualization of real-time emergency SOS alerts & route facilities:
    - Real Pending (Red/Warning) and Resolved (Green/Success) SOS markers
    - Real route facilities (Medical, Emergency, Water, Food, Shelter, Sanitation)
    - Lightweight interactive Leaflet map with custom operational popups
    - Operational summary counts bar (Pending SOS, Resolved SOS, Facilities)
    """
    db_path = current_app.config['DATABASE']

    # Fetch real records from database
    all_sos = get_all_sos_requests(db_path)
    all_facilities = get_all_facilities(db_path)
    all_volunteers = get_all_volunteers(db_path)

    # Calculate operational stats
    pending_sos = [s for s in all_sos if s['status'] == 'pending']
    resolved_sos = [s for s in all_sos if s['status'] == 'resolved']

    vol_tracking = 0
    vol_stale = 0
    vol_offline = 0
    volunteer_markers = []

    for v in all_volunteers:
        freshness, delta = calculate_freshness(v['location_updated_at'], v['status'])
        if freshness in ('LIVE', 'RECENT'):
            vol_tracking += 1
        elif freshness == 'STALE':
            vol_stale += 1
        else:
            vol_offline += 1

        if v['latitude'] is not None and v['longitude'] is not None:
            try:
                lat = float(v['latitude'])
                lon = float(v['longitude'])
                from models.volunteer_model import is_volunteer_online, format_last_seen
                online = is_volunteer_online(v)
                last_seen_str = format_last_seen(v['location_updated_at'])
                volunteer_markers.append({
                    'id': v['id'],
                    'name': v['name'],
                    'phone': v['phone'] if online else None,
                    'status': v['status'],
                    'is_online': online,
                    'can_contact': online,
                    'last_seen': last_seen_str,
                    'freshness': freshness,
                    'delta_seconds': delta,
                    'latitude': lat,
                    'longitude': lon,
                    'location_updated_at': str(v['location_updated_at']) if v['location_updated_at'] else 'Never'
                })
            except (ValueError, TypeError):
                continue


    # Detect incident clusters among unresolved SOS
    clusters = detect_incident_clusters(all_sos, threshold_km=2.0)
    clustered_incidents = sum(1 for c in clusters.values() if c.get('in_cluster'))

    map_stats = {
        'pending_count': len(pending_sos),
        'resolved_count': len(resolved_sos),
        'total_sos': len(all_sos),
        'facility_count': len(all_facilities),
        'volunteers_total': len(all_volunteers),
        'volunteers_tracking': vol_tracking,
        'volunteers_stale': vol_stale,
        'volunteers_offline': vol_offline,
        'clustered_incidents': clustered_incidents
    }

    # Format clean SOS marker payloads for Leaflet JS (safely handling missing coordinates)
    sos_markers = []
    for s in all_sos:
        if s['latitude'] is not None and s['longitude'] is not None:
            try:
                lat = float(s['latitude'])
                lon = float(s['longitude'])
                loc_name = get_location_name(lat, lon)
                cluster_info = clusters.get(s['id'], {'in_cluster': False, 'cluster_count': 1})
                sos_markers.append({
                    'id': s['id'],
                    'latitude': lat,
                    'longitude': lon,
                    'status': s['status'],
                    'priority': s.get('priority', 'NORMAL'),
                    'is_repeated': s.get('is_repeated', False),
                    'in_cluster': cluster_info['in_cluster'],
                    'cluster_count': cluster_info['cluster_count'],
                    'assigned_volunteer_name': s.get('assigned_volunteer_name'),
                    'user_name': s.get('user_name') or 'Anonymous Pilgrim',
                    'user_phone': s.get('user_phone') or '—',
                    'location_name': loc_name,
                    'message': s.get('message') or 'No message provided',
                    'created_at': str(s['created_at'])
                })
            except (ValueError, TypeError):
                continue



    # Format clean Facility marker payloads for Leaflet JS
    facility_markers = []
    for f in all_facilities:
        if f['latitude'] is not None and f['longitude'] is not None:
            try:
                facility_markers.append({
                    'id': f['id'],
                    'name': f['name'],
                    'type': f['type'],
                    'latitude': float(f['latitude']),
                    'longitude': float(f['longitude']),
                    'description': f['description'] or ''
                })
            except (ValueError, TypeError):
                continue

    return render_template(
        'admin/map.html',
        map_stats=map_stats,
        sos_markers=sos_markers,
        facility_markers=facility_markers,
        volunteer_markers=volunteer_markers,
        admin_name=session.get('user_name', 'Admin')
    )


# ============================================================
# Phase 34 — Admin Volunteer Directory & Safety Management
# ============================================================

@admin_bp.route('/admin/volunteers')
@admin_required
def admin_volunteer_list():
    """
    GET /admin/volunteers — Phase 34 Admin Volunteer Directory Page.

    Provides volunteer deployment, safety monitoring and status management:
    - Search by volunteer name or phone (query param 'q')
    - Status filtering (all / active / inactive)
    - Freshness filtering (all / live / recent / stale / offline)
    - Operational summary counts (Total, Active, Tracking/Live, Stale, Offline)
    """
    db_path = current_app.config['DATABASE']

    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', 'all').upper().strip()
    freshness_filter = request.args.get('freshness', 'all').upper().strip()

    all_vols = get_all_volunteers(db_path)

    # Process volunteers and calculate freshness
    processed_vols = []
    total_active = 0
    total_tracking = 0
    total_stale = 0
    total_offline = 0

    for v in all_vols:
        freshness, delta = calculate_freshness(v['location_updated_at'], v['status'])
        v_dict = {
            'id': v['id'],
            'user_id': v['user_id'],
            'name': v['name'],
            'phone': v['phone'],
            'status': v['status'],
            'latitude': v['latitude'],
            'longitude': v['longitude'],
            'location_updated_at': v['location_updated_at'],
            'freshness': freshness,
            'delta_seconds': delta
        }

        if v['status'] == 'ACTIVE':
            total_active += 1

        if freshness in ('LIVE', 'RECENT'):
            total_tracking += 1
        elif freshness == 'STALE':
            total_stale += 1
        else:
            total_offline += 1

        # Apply search query
        if search_query:
            q_lower = search_query.lower()
            if q_lower not in v['name'].lower() and q_lower not in v['phone'].lower():
                continue

        # Apply status filter
        if status_filter != 'ALL':
            if v['status'] != status_filter:
                continue

        # Apply freshness filter
        if freshness_filter != 'ALL':
            if freshness != freshness_filter:
                continue

        processed_vols.append(v_dict)

    summary_stats = {
        'total': len(all_vols),
        'active': total_active,
        'tracking': total_tracking,
        'stale': total_stale,
        'offline': total_offline,
        'filtered_count': len(processed_vols)
    }

    return render_template(
        'admin/volunteers.html',
        volunteers=processed_vols,
        stats=summary_stats,
        search_query=search_query,
        status_filter=status_filter,
        freshness_filter=freshness_filter,
        admin_name=session.get('user_name', 'Admin')
    )


@admin_bp.route('/admin/volunteers/<int:volunteer_id>/toggle-status', methods=['POST'])
@admin_required
def admin_toggle_volunteer_status(volunteer_id):
    """
    POST /admin/volunteers/<id>/toggle-status — Toggle volunteer active/inactive status.
    """
    db_path = current_app.config['DATABASE']
    vol = get_volunteer_by_id(db_path, volunteer_id)

    if not vol:
        flash('Volunteer not found.', 'danger')
        return redirect(url_for('admin.admin_volunteer_list'))

    new_status = 'INACTIVE' if vol['status'] == 'ACTIVE' else 'ACTIVE'
    success = set_volunteer_status(db_path, volunteer_id, new_status)

    if success:
        admin_user_id = session.get('user_id')
        try:
            create_admin_activity(
                db_path=db_path,
                admin_user_id=admin_user_id,
                action_type='VOLUNTEER_STATUS_TOGGLED',
                description=f"Admin updated status of volunteer {vol['name']} ({vol['phone']}) to {new_status}.",
                entity_type='volunteer',
                entity_id=volunteer_id
            )
        except Exception:
            pass
        flash(f"Volunteer '{vol['name']}' status updated to {new_status}.", 'success')
    else:
        flash('Failed to update volunteer status.', 'danger')

    return redirect(url_for('admin.admin_volunteer_list'))


@admin_bp.route('/admin/volunteers/<int:volunteer_id>')
@admin_required
def admin_volunteer_detail(volunteer_id):
    """
    GET /admin/volunteers/<id> — Phase 33 Detailed Volunteer Profile View.
    Displays identity, approval status, live telemetry, contact actions, and full assignment history.
    """
    db_path = current_app.config['DATABASE']
    vol = get_volunteer_by_id(db_path, volunteer_id)
    if not vol:
        flash(f"Volunteer #{volunteer_id} not found.", 'danger')
        return redirect(url_for('admin.admin_volunteer_list'))

    freshness, delta = calculate_freshness(vol['location_updated_at'], vol['status'])
    from models.volunteer_model import is_volunteer_online, format_last_seen
    online = is_volunteer_online(vol)
    last_seen_str = format_last_seen(vol['location_updated_at'])

    vol_dict = dict(vol)
    vol_dict['freshness'] = freshness
    vol_dict['delta_seconds'] = delta
    vol_dict['is_online'] = online
    vol_dict['can_contact'] = online
    vol_dict['last_seen'] = last_seen_str

    from models.volunteer_assignment_model import get_assignments_for_volunteer, get_active_assignments_for_volunteer
    assignments = get_assignments_for_volunteer(db_path, volunteer_id)
    active_assignments = get_active_assignments_for_volunteer(db_path, volunteer_id)
    current_assignment = active_assignments[0] if active_assignments else None

    # Log contact view / details access in audit log
    admin_id = session.get('user_id')
    try:
        create_admin_activity(
            db_path=db_path,
            admin_user_id=admin_id,
            action_type='VOLUNTEER_CONTACTED',
            description=f"Admin viewed detailed profile and contact actions for volunteer #{volunteer_id} ({vol['name']}).",
            entity_type='VOLUNTEER',
            entity_id=volunteer_id
        )
    except Exception:
        pass

    return render_template(
        'admin/volunteer_detail.html',
        volunteer=vol_dict,
        assignments=assignments,
        current_assignment=current_assignment
    )


@admin_bp.route('/api/admin/volunteers/<int:volunteer_id>/details', methods=['GET'])
@admin_required
def api_admin_volunteer_details(volunteer_id):
    """
    GET /api/admin/volunteers/<id>/details — JSON endpoint for volunteer modal.
    Never exposes passwords, hashes, tokens, or session secrets.
    """
    db_path = current_app.config['DATABASE']
    vol = get_volunteer_by_id(db_path, volunteer_id)
    if not vol:
        return jsonify({'success': False, 'error': f"Volunteer #{volunteer_id} not found."}), 404

    freshness, delta = calculate_freshness(vol['location_updated_at'], vol['status'])
    from models.volunteer_model import is_volunteer_online, format_last_seen
    from models.volunteer_assignment_model import get_active_assignments_for_volunteer
    active_assignments = get_active_assignments_for_volunteer(db_path, volunteer_id)

    online = is_volunteer_online(vol)
    last_seen_str = format_last_seen(vol['location_updated_at'])

    data = {
        'id': vol['id'],
        'user_id': vol['user_id'],
        'name': vol['name'],
        'phone': vol['phone'] if online else None,
        'status': vol['status'],
        'is_online': online,
        'can_contact': online,
        'last_seen': last_seen_str,
        'availability': vol['availability'] if 'availability' in vol.keys() else 'AVAILABLE',
        'is_sharing': vol['is_sharing'] if 'is_sharing' in vol.keys() else 0,
        'latitude': float(vol['latitude']) if vol['latitude'] is not None else None,
        'longitude': float(vol['longitude']) if vol['longitude'] is not None else None,
        'accuracy': float(vol['accuracy']) if ('accuracy' in vol.keys() and vol['accuracy'] is not None) else None,
        'freshness': freshness,
        'delta_seconds': delta,
        'location_updated_at': str(vol['location_updated_at']) if vol['location_updated_at'] else 'Never',
        'active_assignment': active_assignments[0] if active_assignments else None
    }
    return jsonify({'success': True, 'volunteer': data}), 200


@admin_bp.route('/api/admin/sos/<int:sos_id>/candidates', methods=['GET'])
@admin_required
def api_admin_sos_candidates(sos_id):
    """
    GET /api/admin/sos/<sos_id>/candidates — JSON candidate volunteers sorted by Haversine distance.
    """
    db_path = current_app.config['DATABASE']
    from models.volunteer_assignment_model import get_candidate_volunteers_for_sos
    candidates = get_candidate_volunteers_for_sos(db_path, sos_id)
    return jsonify({'success': True, 'sos_id': sos_id, 'candidates': candidates}), 200




@admin_bp.route('/admin/assignments/<int:assignment_id>/cancel', methods=['POST'])
@admin_required
def admin_cancel_assignment(assignment_id):
    """
    POST /admin/assignments/<id>/cancel — Admin cancels an active emergency assignment.
    """
    db_path = current_app.config['DATABASE']
    admin_id = session.get('user_id')
    is_json = request.is_json or (request.content_type and 'application/json' in request.content_type)

    data = request.get_json(silent=True) or request.form
    reason = data.get('reason')

    from models.volunteer_assignment_model import cancel_assignment
    success, message = cancel_assignment(db_path, assignment_id, admin_id, reason=reason)

    if success:
        if is_json:
            return jsonify({'success': True, 'message': message}), 200
        flash(message, 'success')
    else:
        if is_json:
            return jsonify({'success': False, 'error': message}), 400
        flash(message, 'danger')

    return redirect(url_for('admin.admin_sos_list'))


@admin_bp.route('/api/admin/volunteers/locations', methods=['GET'])
@admin_required
def api_admin_volunteer_locations():
    """
    GET /api/admin/volunteers/locations — Protected endpoint for live volunteer coordinates (Phase 33).
    Includes active assignment status and offline contact protection.
    """
    db_path = current_app.config['DATABASE']
    all_vols = get_all_volunteers(db_path)

    from models.volunteer_model import is_volunteer_online, format_last_seen
    from models.volunteer_assignment_model import get_active_assignments_for_volunteer

    locations = []
    for v in all_vols:
        freshness, delta = calculate_freshness(v['location_updated_at'], v['status'])
        active_assigns = get_active_assignments_for_volunteer(db_path, v['id'])
        current_assign = active_assigns[0] if active_assigns else None

        online = is_volunteer_online(v)
        last_seen_str = format_last_seen(v['location_updated_at'])

        avail = v['availability'] if ('availability' in v.keys() and v['availability']) else 'AVAILABLE'
        if current_assign:
            avail = 'BUSY'

        locations.append({
            'id': v['id'],
            'name': v['name'],
            'phone': v['phone'] if online else None,
            'status': v['status'],
            'availability': avail,
            'is_online': online,
            'can_contact': online,
            'last_seen': last_seen_str,
            'call_url': f"tel:{v['phone']}" if online else None,
            'whatsapp_url': f"https://wa.me/91{v['phone']}?text=Hello%20{v['name']}%2C%20this%20is%20Wari%20Mitra%20Control%20Center." if online else None,
            'is_sharing': v['is_sharing'] if 'is_sharing' in v.keys() else 0,
            'latitude': float(v['latitude']) if v['latitude'] is not None else None,
            'longitude': float(v['longitude']) if v['longitude'] is not None else None,
            'accuracy': float(v['accuracy']) if ('accuracy' in v.keys() and v['accuracy'] is not None) else None,
            'freshness': freshness,
            'delta_seconds': delta,
            'last_update': last_seen_str if not online else (str(v['location_updated_at']) if v['location_updated_at'] else 'Never'),
            'location_updated_at': str(v['location_updated_at']) if v['location_updated_at'] else 'Never',
            'active_assignment_sos_id': current_assign['sos_id'] if current_assign else None,
            'active_assignment_status': current_assign['status'] if current_assign else None
        })

    return jsonify({
        'success': True,
        'volunteers': locations
    }), 200





# ============================================================
# Phase 25 — Admin Facility Registry & Management Routes
# ============================================================


@admin_bp.route('/admin/facilities')
@admin_required
def admin_facility_list():
    """
    GET /admin/facilities — Phase 25 Admin Facility Registry Page.

    Provides full management (view, search, filter, create, edit, delete) of route facilities:
    - Search by facility name or description (query param 'q')
    - Type filtering based on real database types
    - Modal forms for creating & editing facilities
    - Safe POST-based deletion
    """
    db_path = current_app.config['DATABASE']

    search_query = request.args.get('q', '').strip()
    type_filter = request.args.get('type', 'all').lower().strip()

    all_facilities = get_all_facilities(db_path)

    # Extract unique facility types dynamically from real database
    available_types = sorted(list(set(f['type'].lower() for f in all_facilities if f['type'])))

    # Apply type filtering
    if type_filter != 'all':
        filtered = [f for f in all_facilities if f['type'].lower() == type_filter]
    else:
        filtered = all_facilities

    # Apply search filtering (name or description)
    if search_query:
        q_lower = search_query.lower()
        filtered = [
            f for f in filtered
            if q_lower in f['name'].lower() or (f['description'] and q_lower in f['description'].lower())
        ]

    facilities_list = []
    for f in filtered:
        facilities_list.append({
            'id': f['id'],
            'name': f['name'],
            'type': f['type'],
            'latitude': f['latitude'],
            'longitude': f['longitude'],
            'description': f['description'] or ''
        })

    filter_stats = {
        'total': len(all_facilities),
        'showing': len(facilities_list),
        'current_type': type_filter,
        'search_query': search_query,
        'available_types': available_types
    }

    return render_template(
        'admin/facility_list.html',
        facilities_list=facilities_list,
        filter_stats=filter_stats,
        admin_name=session.get('user_name', 'Admin')
    )


@admin_bp.route('/admin/facilities/create', methods=['POST'])
@admin_required
def admin_create_facility():
    """
    POST /admin/facilities/create — Add a new facility to the database.

    Validation rules:
    - Name must be a non-empty string
    - Facility type must be non-empty
    - Latitude must be float between -90.0 and 90.0
    - Longitude must be float between -180.0 and 180.0
    """
    db_path = current_app.config['DATABASE']

    name = request.form.get('name', '').strip()
    facility_type = request.form.get('type', '').strip()
    lat_str = request.form.get('latitude', '').strip()
    lon_str = request.form.get('longitude', '').strip()
    description = request.form.get('description', '').strip()

    if not name:
        flash('Facility name cannot be empty.', 'danger')
        return redirect(url_for('admin.admin_facility_list'))

    if not facility_type:
        flash('Facility type cannot be empty.', 'danger')
        return redirect(url_for('admin.admin_facility_list'))

    try:
        lat = float(lat_str)
        if lat < -90.0 or lat > 90.0:
            raise ValueError()
    except (ValueError, TypeError):
        flash('Latitude must be a valid number between -90.0 and 90.0.', 'danger')
        return redirect(url_for('admin.admin_facility_list'))

    try:
        lon = float(lon_str)
        if lon < -180.0 or lon > 180.0:
            raise ValueError()
    except (ValueError, TypeError):
        flash('Longitude must be a valid number between -180.0 and 180.0.', 'danger')
        return redirect(url_for('admin.admin_facility_list'))

    new_id = create_facility(db_path, name, facility_type, lat, lon, description)
    if new_id:
        flash(f'Facility "{name}" (#{new_id}) created successfully.', 'success')
        try:
            admin_id = session.get('user_id')
            create_admin_activity(
                db_path=db_path,
                admin_user_id=admin_id,
                action_type='FACILITY_CREATED',
                description=f"Admin created facility '{name}' ({facility_type}).",
                entity_type='FACILITY',
                entity_id=new_id
            )
        except Exception as e:
            print(f"Audit log error during facility creation: {e}")
    else:
        flash('Failed to create facility in database.', 'danger')

    return redirect(url_for('admin.admin_facility_list'))


@admin_bp.route('/admin/facilities/<int:facility_id>/edit', methods=['POST'])
@admin_required
def admin_edit_facility(facility_id):
    """
    POST /admin/facilities/<facility_id>/edit — Update an existing facility.

    Validation rules:
    - Facility must exist in database
    - Name, type must be valid non-empty strings
    - Latitude & longitude must be valid float coordinates
    """
    db_path = current_app.config['DATABASE']

    facility = get_facility_by_id(db_path, facility_id)
    if not facility:
        flash(f'Facility #{facility_id} not found.', 'danger')
        return redirect(url_for('admin.admin_facility_list'))

    name = request.form.get('name', '').strip()
    facility_type = request.form.get('type', '').strip()
    lat_str = request.form.get('latitude', '').strip()
    lon_str = request.form.get('longitude', '').strip()
    description = request.form.get('description', '').strip()

    if not name or not facility_type:
        flash('Facility name and type cannot be empty.', 'danger')
        return redirect(url_for('admin.admin_facility_list'))

    try:
        lat = float(lat_str)
        if lat < -90.0 or lat > 90.0:
            raise ValueError()
    except (ValueError, TypeError):
        flash('Latitude must be a valid number between -90.0 and 90.0.', 'danger')
        return redirect(url_for('admin.admin_facility_list'))

    try:
        lon = float(lon_str)
        if lon < -180.0 or lon > 180.0:
            raise ValueError()
    except (ValueError, TypeError):
        flash('Longitude must be a valid number between -180.0 and 180.0.', 'danger')
        return redirect(url_for('admin.admin_facility_list'))

    success = update_facility(db_path, facility_id, name, facility_type, lat, lon, description)
    if success:
        flash(f'Facility #{facility_id} ("{name}") updated successfully.', 'success')
        try:
            admin_id = session.get('user_id')
            create_admin_activity(
                db_path=db_path,
                admin_user_id=admin_id,
                action_type='FACILITY_UPDATED',
                description=f"Admin updated facility #{facility_id} ('{name}').",
                entity_type='FACILITY',
                entity_id=facility_id
            )
        except Exception as e:
            print(f"Audit log error during facility edit: {e}")
    else:
        flash(f'Failed to update facility #{facility_id}.', 'danger')

    return redirect(url_for('admin.admin_facility_list'))


@admin_bp.route('/admin/facilities/<int:facility_id>/delete', methods=['POST'])
@admin_required
def admin_delete_facility(facility_id):
    """
    POST /admin/facilities/<facility_id>/delete — Delete a facility from database.

    Requirements:
    - Safe POST action
    - Validates facility exists
    - Deletes record from SQLite database
    """
    db_path = current_app.config['DATABASE']

    facility = get_facility_by_id(db_path, facility_id)
    if not facility:
        flash(f'Facility #{facility_id} not found.', 'danger')
        return redirect(url_for('admin.admin_facility_list'))

    facility_name = facility['name']
    success = delete_facility(db_path, facility_id)
    if success:
        flash(f'Facility #{facility_id} ("{facility_name}") deleted successfully.', 'success')
        try:
            admin_id = session.get('user_id')
            create_admin_activity(
                db_path=db_path,
                admin_user_id=admin_id,
                action_type='FACILITY_DELETED',
                description=f"Admin deleted facility #{facility_id} ('{facility_name}').",
                entity_type='FACILITY',
                entity_id=facility_id
            )
        except Exception as e:
            print(f"Audit log error during facility delete: {e}")
    else:
        flash(f'Failed to delete facility #{facility_id}.', 'danger')

    return redirect(url_for('admin.admin_facility_list'))



# ============================================================
# Phase 26 — Admin System Monitoring & Reliability Route
# ============================================================

@admin_bp.route('/admin/monitoring')
@admin_required
def admin_monitoring():
    """
    GET /admin/monitoring — Phase 26 Admin System Monitoring & Operational Health Dashboard.

    Provides a comprehensive real-time operational reliability overview across 7 service pillars:
    1. SQLite Database Health & Query Execution
    2. Emergency SOS Subsystem Health & Request Distribution
    3. Open-Meteo Weather API Integration Health
    4. Location Geocoding & Landmark Proximity Service Health
    5. Google Gemini AI Integration Readiness
    6. Facility Data Coordinate Quality & Health
    7. Ground Situation Map Dataset Readiness

    Critical Isolation Rule:
    - Every service check is safely isolated in its own try/except block.
    - An external API failure or timeout NEVER crashes the monitoring page.
    - Zero API keys, passwords, or raw tracebacks are exposed.
    """
    import datetime
    import requests
    from config import Config

    db_path = current_app.config['DATABASE']
    last_check_time = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    health_checks = {}
    warning_count = 0
    degraded_count = 0

    # 1. Database Health Check (SQLite)
    try:
        all_users = get_all_users(db_path)
        all_sos = get_all_sos_requests(db_path)
        all_facilities = get_all_facilities(db_path)
        all_schedule = get_full_schedule(db_path)

        health_checks['database'] = {
            'name': 'SQLite Database Engine',
            'icon': 'bi-database-check text-success',
            'status': 'OPERATIONAL',
            'badge': 'bg-success',
            'details': f'Connected to wari_mitra.db successfully. Executed lightweight SQL queries.',
            'metrics': {
                'Registered Pilgrims': len(all_users),
                'Total SOS Requests': len(all_sos),
                'Facility Records': len(all_facilities),
                'Schedule Days': len(all_schedule)
            }
        }
    except Exception as e:
        degraded_count += 1
        health_checks['database'] = {
            'name': 'SQLite Database Engine',
            'icon': 'bi-database-x text-danger',
            'status': 'DEGRADED',
            'badge': 'bg-danger',
            'details': 'Database connectivity error or file access failure.',
            'metrics': {'Status': 'Unavailable'}
        }
        all_users, all_sos, all_facilities, all_schedule = [], [], [], []

    # 2. Emergency SOS Subsystem Health Check
    try:
        pending_sos = [s for s in all_sos if s['status'] == 'pending']
        resolved_sos = [s for s in all_sos if s['status'] == 'resolved']
        latest_time = all_sos[0]['created_at'] if all_sos else 'None'

        sos_status = 'OPERATIONAL'
        sos_badge = 'bg-success'
        if len(pending_sos) > 10:
            sos_status = 'WARNING'
            sos_badge = 'bg-warning text-dark'
            warning_count += 1

        health_checks['sos_service'] = {
            'name': 'Emergency SOS Subsystem',
            'icon': 'bi-shield-exclamation text-danger',
            'status': sos_status,
            'badge': sos_badge,
            'details': f'SOS dispatch pipeline accessible. Latest emergency request at {latest_time}.',
            'metrics': {
                'Total Emergency Requests': len(all_sos),
                'Active Pending Alerts': len(pending_sos),
                'Resolved Alerts': len(resolved_sos)
            }
        }
    except Exception as e:
        degraded_count += 1
        health_checks['sos_service'] = {
            'name': 'Emergency SOS Subsystem',
            'icon': 'bi-shield-x text-danger',
            'status': 'DEGRADED',
            'badge': 'bg-danger',
            'details': 'Unable to query SOS subsystem status.',
            'metrics': {'Status': 'Error'}
        }

    # 3. Weather Service Health Check (Open-Meteo API)
    try:
        # Lightweight ping to Open-Meteo with 3s timeout
        r_weather = requests.get(
            "https://api.open-meteo.com/v1/forecast?latitude=18.52&longitude=73.85&current_weather=true",
            timeout=3
        )
        if r_weather.status_code == 200:
            health_checks['weather_service'] = {
                'name': 'Open-Meteo Weather API',
                'icon': 'bi-cloud-sun-fill text-warning',
                'status': 'OPERATIONAL',
                'badge': 'bg-success',
                'details': 'Open-Meteo forecast API is online and responding (HTTP 200).',
                'metrics': {'API Endpoint': 'api.open-meteo.com', 'Latency Check': 'Passed (HTTP 200)'}
            }
        else:
            warning_count += 1
            health_checks['weather_service'] = {
                'name': 'Open-Meteo Weather API',
                'icon': 'bi-cloud-sun-fill text-warning',
                'status': 'WARNING',
                'badge': 'bg-warning text-dark',
                'details': f'Weather service returned HTTP {r_weather.status_code}. Fallback active.',
                'metrics': {'API Endpoint': 'api.open-meteo.com', 'Status': f'HTTP {r_weather.status_code}'}
            }
    except Exception as e:
        warning_count += 1
        health_checks['weather_service'] = {
            'name': 'Open-Meteo Weather API',
            'icon': 'bi-cloud-slash text-secondary',
            'status': 'WARNING',
            'badge': 'bg-warning text-dark',
            'details': 'External Open-Meteo API unreachable or timed out. Cached/offline mode active.',
            'metrics': {'API Endpoint': 'api.open-meteo.com', 'Connection': 'Offline / Fallback'}
        }

    # 4. Location / Geocoding Service Health Check
    try:
        from services.location_service import KNOWN_LOCATIONS
        health_checks['location_service'] = {
            'name': 'Location & Geocoding Service',
            'icon': 'bi-geo-alt-fill text-primary',
            'status': 'OPERATIONAL',
            'badge': 'bg-success',
            'details': 'Landmark proximity geocoder & Nominatim reverse-geocoding cache ready.',
            'metrics': {
                'Known Route Halts': len(KNOWN_LOCATIONS),
                'Geocoding Provider': 'Nominatim + Offline Proximity'
            }
        }
    except Exception as e:
        warning_count += 1
        health_checks['location_service'] = {
            'name': 'Location & Geocoding Service',
            'icon': 'bi-geo-alt text-secondary',
            'status': 'WARNING',
            'badge': 'bg-warning text-dark',
            'details': 'Location service running in raw coordinate fallback mode.',
            'metrics': {'Geocoder': 'Coordinate Fallback'}
        }

    # 5. AI / Gemini Service Health Check
    try:
        gemini_key = Config.GEMINI_API_KEY
        if gemini_key and len(gemini_key) > 5:
            health_checks['ai_service'] = {
                'name': 'Google Gemini AI Integration',
                'icon': 'bi-cpu-fill text-info',
                'status': 'OPERATIONAL',
                'badge': 'bg-success',
                'details': 'Google Gemini API key configured and ready. Wari context builder operational.',
                'metrics': {
                    'Provider': 'Google Gemini Generative AI',
                    'API Key Status': 'Configured (Secret Masked)'
                }
            }
        else:
            warning_count += 1
            health_checks['ai_service'] = {
                'name': 'Google Gemini AI Integration',
                'icon': 'bi-cpu text-warning',
                'status': 'WARNING',
                'badge': 'bg-warning text-dark',
                'details': 'Google Gemini API key not set. AI assistant running in fallback knowledge mode.',

                'metrics': {
                    'Provider': 'Built-in Knowledge Fallback',
                    'API Key Status': 'Not Set'
                }
            }
    except Exception as e:
        warning_count += 1
        health_checks['ai_service'] = {
            'name': 'Google Gemini AI Integration',
            'icon': 'bi-cpu text-secondary',
            'status': 'WARNING',
            'badge': 'bg-warning text-dark',
            'details': 'AI service check failed. Running offline fallback.',
            'metrics': {'Status': 'Fallback Mode'}
        }

    # 6. Facility Data Health Check
    try:
        valid_coords = sum(1 for f in all_facilities if f['latitude'] is not None and f['longitude'] is not None)
        invalid_coords = len(all_facilities) - valid_coords

        fac_status = 'OPERATIONAL'
        fac_badge = 'bg-success'
        if invalid_coords > 0:
            fac_status = 'WARNING'
            fac_badge = 'bg-warning text-dark'
            warning_count += 1

        health_checks['facility_health'] = {
            'name': 'Route Facility Data Quality',
            'icon': 'bi-hospital-fill text-success',
            'status': fac_status,
            'badge': fac_badge,
            'details': f'Verified {valid_coords} facilities with valid GPS coordinates.',
            'metrics': {
                'Total Facilities': len(all_facilities),
                'Mapped Facilities': valid_coords,
                'Missing Coordinates': invalid_coords
            }
        }
    except Exception as e:
        degraded_count += 1
        health_checks['facility_health'] = {
            'name': 'Route Facility Data Quality',
            'icon': 'bi-hospital text-danger',
            'status': 'DEGRADED',
            'badge': 'bg-danger',
            'details': 'Error checking facility data health.',
            'metrics': {'Status': 'Error'}
        }

    # 7. Map Data Health Check
    try:
        valid_sos_coords = sum(1 for s in all_sos if s['latitude'] is not None and s['longitude'] is not None)
        valid_fac_coords = sum(1 for f in all_facilities if f['latitude'] is not None and f['longitude'] is not None)

        health_checks['map_health'] = {
            'name': 'Ground Situation Map Dataset',
            'icon': 'bi-map-fill text-warning',
            'status': 'OPERATIONAL',
            'badge': 'bg-success',
            'details': 'Spatial coordinates ready for Leaflet map rendering.',
            'metrics': {
                'Valid SOS Markers': valid_sos_coords,
                'Valid Facility Markers': valid_fac_coords,
                'Map Rendering Engine': 'Leaflet.js + OpenStreetMap'
            }
        }
    except Exception as e:
        warning_count += 1
        health_checks['map_health'] = {
            'name': 'Ground Situation Map Dataset',
            'icon': 'bi-map text-secondary',
            'status': 'WARNING',
            'badge': 'bg-warning text-dark',
            'details': 'Map dataset verification issue.',
            'metrics': {'Status': 'Check Failed'}
        }

    # Calculate Overall System Status
    if degraded_count > 0:
        overall_status = 'DEGRADED'
        overall_badge = 'bg-danger'
        overall_desc = f'Operational with {degraded_count} degraded service(s) and {warning_count} warning(s).'
    elif warning_count > 0:
        overall_status = 'WARNING'
        overall_badge = 'bg-warning text-dark'
        overall_desc = f'All core services online with {warning_count} minor warning/fallback notice(s).'
    else:
        overall_status = 'OPERATIONAL'
        overall_badge = 'bg-success'
        overall_desc = 'All 7 major Wari Mitra services and integrations are 100% operational.'

    system_summary = {
        'overall_status': overall_status,
        'overall_badge': overall_badge,
        'overall_desc': overall_desc,
        'last_check_time': last_check_time,
        'warning_count': warning_count,
        'degraded_count': degraded_count
    }

    return render_template(
        'admin/monitoring.html',
        system_summary=system_summary,
        health_checks=health_checks,
        admin_name=session.get('user_name', 'Admin')
    )


# ============================================================
# Phase 29 — Admin Activity & Audit History Route
# ============================================================

@admin_bp.route('/admin/activity')
@admin_required
def admin_activity_list():
    """
    GET /admin/activity — Phase 29 Admin Activity & Audit History Page.

    Provides a dedicated, read-only audit log of administrative and operational actions:
    - Search by keyword (?q=...)
    - Filter by action type (?action=...)
    - Live statistics (total, today, SOS, facility, auth)
    - Full details modal for audit inspection
    """
    db_path = current_app.config['DATABASE']

    action_filter = request.args.get('action', 'all').strip()
    search_query = request.args.get('q', '').strip()

    # Fetch filtered activities
    activities = get_filtered_admin_activities(
        db_path=db_path,
        action_type=action_filter,
        search_query=search_query,
        limit=100
    )

    stats = get_activity_stats(db_path)

    activity_list = []
    for a in activities:
        activity_list.append({
            'id': a['id'],
            'admin_user_id': a['admin_user_id'],
            'admin_name': a['admin_name'] or f"Admin #{a['admin_user_id'] or 'System'}",
            'admin_phone': a['admin_phone'] or '—',
            'action_type': a['action_type'],
            'description': a['description'],
            'entity_type': a['entity_type'] or '—',
            'entity_id': a['entity_id'] or '—',
            'created_at': a['created_at']
        })

    filter_info = {
        'action': action_filter,
        'q': search_query,
        'showing': len(activity_list)
    }

    return render_template(
        'admin/activity_log.html',
        activity_list=activity_list,
        stats=stats,
        filter_info=filter_info,
        admin_name=session.get('user_name', 'Admin')
    )







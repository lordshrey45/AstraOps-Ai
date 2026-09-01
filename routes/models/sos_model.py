"""
SOS Model — Database access layer for the 'sos_requests' table (Phase 3 Multi-Emergency Queue & Dispatch Control).

Provides CRUD operations, operational priority computation, incident queue management,
volunteer assignment tracking, and spatial incident cluster detection.
Uses raw SQL via sqlite3 (no ORM) as per architecture.

Table schema:
    id                    INTEGER PK AUTOINCREMENT
    user_id               INTEGER FK -> users.id (nullable for anonymous SOS)
    latitude              REAL
    longitude             REAL
    message               TEXT (optional notes)
    status                TEXT DEFAULT 'pending' (pending / resolved)
    priority              TEXT DEFAULT 'MEDIUM' (CRITICAL / HIGH / MEDIUM / LOW)
    priority_reason       TEXT
    dispatch_status       TEXT DEFAULT 'UNASSIGNED' (UNASSIGNED / ASSIGNED / ACKNOWLEDGED / IN_PROGRESS / RESOLVED)
    assigned_volunteer_id INTEGER FK -> volunteers.id (nullable)
    assigned_at           TIMESTAMP
    acknowledged_at       TIMESTAMP
    resolved_at           TIMESTAMP
    resolved_by           INTEGER
    resolution_notes      TEXT
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
"""

import math
from datetime import datetime, timezone
from models.db import get_db_connection, close_db


def compute_sos_priority(message=None, medical_info=None, created_at=None, status='pending'):
    """
    Calculate operational priority deterministically without medical hallucination.
    Returns: (priority, reason)
    Priority levels: 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    """
    msg_lower = (message or '').strip().lower()
    med_lower = (medical_info or '').strip().lower()

    # Low priority triggers
    if any(w in msg_lower for w in ['test', 'testing', 'drill', 'info only', 'informational', 'not urgent']):
        return 'LOW', 'System-assigned: Non-urgent or test request keywords detected.'

    # Critical trigger keywords in explicit emergency message
    critical_keywords = [
        'heart attack', 'chest pain', 'cardiac', 'unconscious', 'not breathing',
        'severe bleeding', 'fracture', 'accident', 'collapsed', 'stroke',
        'snake bite', 'poison', 'dying', 'critical condition', 'asthma attack',
        'seizure', 'unresponsive', 'head injury', 'heavy bleeding', 'severe accident'
    ]
    for kw in critical_keywords:
        if kw in msg_lower:
            return 'CRITICAL', f"System-assigned: Life-threatening keywords detected ('{kw}')."

    # High trigger keywords
    high_keywords = [
        'dehydration', 'dehydrat', 'fever', 'severe pain', 'vomiting', 'vomit',
        'dizzy', 'dizziness', 'injury', 'doctor', 'medic', 'medical help',
        'wound', 'bleeding', 'blood', 'burn', 'fallen', 'cannot walk', 'asthma', 'lost'
    ]
    for kw in high_keywords:
        if kw in msg_lower:
            return 'HIGH', f"System-assigned: Urgent assistance keywords detected ('{kw}')."

    # Check medical vulnerability if profile info exists
    vulnerable_med = ['diabetes', 'cardiac', 'heart', 'asthma', 'hypertension', 'pregnant', 'elderly', 'paralysis']
    for vm in vulnerable_med:
        if vm in med_lower:
            return 'HIGH', f"System-assigned: Registered high-risk medical vulnerability ('{vm}')."

    # If pending/assigned and older than 30 minutes, bump up priority
    if status in ('pending', 'assigned') and created_at:
        try:
            if isinstance(created_at, str):
                dt = datetime.strptime(created_at.split('.')[0], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
            elif isinstance(created_at, datetime):
                dt = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
            else:
                dt = None
            if dt:
                age_minutes = (datetime.now(timezone.utc) - dt).total_seconds() / 60.0
                if age_minutes > 30:
                    return 'HIGH', f"System-assigned: Waiting time exceeds 30 minutes ({int(age_minutes)} min)."
        except Exception:
            pass

    return 'MEDIUM', 'System-assigned: Standard emergency assistance request.'


def calculate_emergency_age(created_at):
    """
    Format the waiting age of an emergency from created_at timestamp.
    Returns: string like 'Waiting 2 min', 'Waiting 45 min', 'Waiting 2h', or '< 1 min'
    """
    if not created_at:
        return 'Recent'
    try:
        if isinstance(created_at, str):
            dt = datetime.strptime(created_at.split('.')[0], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        elif isinstance(created_at, datetime):
            dt = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
        else:
            return 'Recent'

        delta_sec = max(0, int((datetime.now(timezone.utc) - dt).total_seconds()))
        if delta_sec < 60:
            return 'Waiting < 1 min'
        elif delta_sec < 3600:
            return f"Waiting {delta_sec // 60} min"
        else:
            hrs = delta_sec // 3600
            mins = (delta_sec % 3600) // 60
            return f"Waiting {hrs}h {mins}m"
    except Exception:
        return 'Recent'


def create_sos_request(db_path, latitude, longitude, message=None, user_id=None, priority=None, priority_reason=None):
    """
    Insert a new SOS emergency request atomically with a unique autoincrement ID.
    Never overwrites or merges existing records.
    """
    # If priority not specified, calculate deterministically
    if not priority:
        med_info = None
        if user_id:
            try:
                from models.user_model import get_user_by_id
                u = get_user_by_id(db_path, user_id)
                if u and 'medical_info' in u.keys():
                    med_info = u['medical_info']
            except Exception:
                pass
        priority, calc_reason = compute_sos_priority(message=message, medical_info=med_info)
        if not priority_reason:
            priority_reason = calc_reason

    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute(
            """INSERT INTO sos_requests (user_id, latitude, longitude, message, status, priority, priority_reason, dispatch_status)
               VALUES (?, ?, ?, ?, 'pending', ?, ?, 'UNASSIGNED')""",
            (user_id, latitude, longitude, message, priority, priority_reason)
        )
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        conn.rollback()
        print(f"Error creating SOS request: {e}")
        return None
    finally:
        close_db(conn)


def get_sos_request_by_id(db_path, sos_id):
    """
    Retrieve a single SOS request by its ID with all user, volunteer, and queue details.
    """
    conn = get_db_connection(db_path)
    try:
        sos = conn.execute(
            """SELECT s.*, 
                      u.name as user_name, u.phone as user_phone,
                      u.emergency_contact as user_emergency_contact, u.medical_info as user_medical_info,
                      v.name as assigned_volunteer_name, v.phone as assigned_volunteer_phone,
                      v.latitude as assigned_volunteer_lat, v.longitude as assigned_volunteer_lon,
                      v.location_updated_at as assigned_volunteer_loc_time
               FROM sos_requests s
               LEFT JOIN users u ON s.user_id = u.id
               LEFT JOIN volunteers v ON s.assigned_volunteer_id = v.id
               WHERE s.id = ?""",
            (sos_id,)
        ).fetchone()
        if not sos:
            return None
        d = dict(sos)
        d['age_str'] = calculate_emergency_age(d.get('created_at'))
        if not d.get('priority'):
            prio, rsn = compute_sos_priority(d.get('message'), d.get('user_medical_info'), d.get('created_at'), d.get('status'))
            d['priority'] = prio
            d['priority_reason'] = d.get('priority_reason') or rsn
        if not d.get('dispatch_status'):
            d['dispatch_status'] = 'ASSIGNED' if d.get('assigned_volunteer_id') else ('RESOLVED' if d.get('status') == 'resolved' else 'UNASSIGNED')
        return d
    finally:
        close_db(conn)


def get_all_sos_requests(db_path):
    """
    Retrieve all SOS requests, ordered by unresolved priority first, then oldest unresolved,
    then resolved records.
    """
    conn = get_db_connection(db_path)
    try:
        rows = conn.execute(
            """SELECT s.*, 
                      u.name as user_name, u.phone as user_phone,
                      u.emergency_contact as user_emergency_contact, u.medical_info as user_medical_info,
                      v.name as assigned_volunteer_name, v.phone as assigned_volunteer_phone,
                      v.latitude as assigned_volunteer_lat, v.longitude as assigned_volunteer_lon,
                      v.location_updated_at as assigned_volunteer_loc_time
               FROM sos_requests s
               LEFT JOIN users u ON s.user_id = u.id
               LEFT JOIN volunteers v ON s.assigned_volunteer_id = v.id
               ORDER BY s.id DESC"""
        ).fetchall()

        # Build enhanced list with computed priority, dispatch status, age, and repeated alert detection
        user_pending_counts = {}
        for r in rows:
            if r['status'] in ('pending', 'assigned', 'in_progress') and r['user_id']:
                user_pending_counts[r['user_id']] = user_pending_counts.get(r['user_id'], 0) + 1

        enhanced = []
        for r in rows:
            d = dict(r)
            med_info = d.get('user_medical_info')
            if not d.get('priority'):
                prio, rsn = compute_sos_priority(
                    message=d.get('message'),
                    medical_info=med_info,
                    created_at=d.get('created_at'),
                    status=d.get('status')
                )
                d['priority'] = prio
                d['priority_reason'] = d.get('priority_reason') or rsn

            if not d.get('dispatch_status'):
                if d.get('status') == 'resolved':
                    d['dispatch_status'] = 'RESOLVED'
                elif d.get('assigned_volunteer_id'):
                    d['dispatch_status'] = 'ASSIGNED'
                else:
                    d['dispatch_status'] = 'UNASSIGNED'

            d['age_str'] = calculate_emergency_age(d.get('created_at'))
            d['is_repeated'] = bool(d.get('user_id') and user_pending_counts.get(d['user_id'], 0) > 1)
            enhanced.append(d)

        # Sort:
        # 1. Unresolved (pending/assigned/in_progress) first (0) vs Resolved (1)
        # 2. Priority: CRITICAL (0) -> HIGH (1) -> MEDIUM (2) -> LOW (3)
        # 3. For unresolved: Oldest first (created_at ASC)
        # 4. For resolved: Newest first (created_at DESC)
        prio_weights = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}

        def sort_key(item):
            status_order = 0 if item['status'] != 'resolved' and item['dispatch_status'] != 'RESOLVED' else 1
            prio_order = prio_weights.get(item.get('priority', 'MEDIUM'), 2)
            time_val = str(item.get('created_at') or '')
            if status_order == 0:
                return (status_order, prio_order, time_val)
            else:
                return (status_order, 0, -item['id'])

        enhanced.sort(key=sort_key)
        return enhanced

    finally:
        close_db(conn)


def get_pending_sos_requests(db_path):
    """
    Retrieve only unresolved SOS requests sorted by priority and age.
    """
    all_sos = get_all_sos_requests(db_path)
    return [s for s in all_sos if s['status'] != 'resolved' and s.get('dispatch_status') != 'RESOLVED']


def get_sos_requests_by_user(db_path, user_id):
    """
    Retrieve all SOS requests made by a specific user.
    """
    conn = get_db_connection(db_path)
    try:
        requests = conn.execute(
            "SELECT * FROM sos_requests WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
        return requests
    finally:
        close_db(conn)


def get_assigned_sos_by_volunteer(db_path, volunteer_id):
    """
    Retrieve all active emergency requests currently assigned to a specific volunteer.
    """
    conn = get_db_connection(db_path)
    try:
        rows = conn.execute(
            """SELECT s.*, 
                      u.name as user_name, u.phone as user_phone,
                      u.emergency_contact as user_emergency_contact, u.medical_info as user_medical_info
               FROM sos_requests s
               LEFT JOIN users u ON s.user_id = u.id
               WHERE s.assigned_volunteer_id = ?
               ORDER BY s.created_at DESC""",
            (volunteer_id,)
        ).fetchall()
        
        enhanced = []
        for r in rows:
            d = dict(r)
            d['age_str'] = calculate_emergency_age(d.get('created_at'))
            enhanced.append(d)
        return enhanced
    finally:
        close_db(conn)


def acknowledge_sos_request(db_path, sos_id):
    """
    Mark an SOS request as acknowledged by admin or assigned volunteer.
    """
    conn = get_db_connection(db_path)
    try:
        result = conn.execute(
            """UPDATE sos_requests 
               SET dispatch_status = 'ACKNOWLEDGED', acknowledged_at = CURRENT_TIMESTAMP
               WHERE id = ? AND status != 'resolved'""",
            (sos_id,)
        )
        conn.commit()
        return result.rowcount > 0
    except Exception as e:
        conn.rollback()
        return False
    finally:
        close_db(conn)


def assign_volunteer_to_sos(db_path, sos_id, volunteer_id):
    """
    Assign or reassign a volunteer to an active emergency request.
    Verifies that emergency is still assignable (not resolved).
    """
    conn = get_db_connection(db_path)
    try:
        result = conn.execute(
            """UPDATE sos_requests 
               SET assigned_volunteer_id = ?, dispatch_status = 'ASSIGNED', assigned_at = CURRENT_TIMESTAMP
               WHERE id = ? AND status != 'resolved'""",
            (volunteer_id, sos_id)
        )
        conn.commit()
        return result.rowcount > 0
    except Exception as e:
        conn.rollback()
        return False
    finally:
        close_db(conn)


def update_sos_priority(db_path, sos_id, priority, reason=None):
    """
    Update priority and priority reason for an emergency request.
    """
    conn = get_db_connection(db_path)
    try:
        result = conn.execute(
            """UPDATE sos_requests 
               SET priority = ?, priority_reason = ?
               WHERE id = ?""",
            (priority, reason, sos_id)
        )
        conn.commit()
        return result.rowcount > 0
    except Exception as e:
        conn.rollback()
        return False
    finally:
        close_db(conn)


def update_sos_dispatch_status(db_path, sos_id, dispatch_status):
    """
    Update operational dispatch status for an emergency (e.g. IN_PROGRESS).
    """
    conn = get_db_connection(db_path)
    try:
        result = conn.execute(
            """UPDATE sos_requests 
               SET dispatch_status = ?
               WHERE id = ? AND status != 'resolved'""",
            (dispatch_status, sos_id)
        )
        conn.commit()
        return result.rowcount > 0
    except Exception as e:
        conn.rollback()
        return False
    finally:
        close_db(conn)


def resolve_sos_request(db_path, sos_id, resolved_by=None, notes=None):
    """
    Mark an SOS request as resolved atomically.
    Resolving SOS #A never affects SOS #B.
    """
    conn = get_db_connection(db_path)
    try:
        result = conn.execute(
            """UPDATE sos_requests 
               SET status = 'resolved', dispatch_status = 'RESOLVED',
                   resolved_at = CURRENT_TIMESTAMP, resolved_by = ?, resolution_notes = ?
               WHERE id = ? AND status != 'resolved'""",
            (resolved_by, notes, sos_id)
        )
        conn.commit()
        return result.rowcount > 0
    except Exception as e:
        conn.rollback()
        print(f"Error resolving SOS request: {e}")
        return False
    finally:
        close_db(conn)


def delete_sos_request(db_path, sos_id):
    """
    Delete an SOS request by its ID.
    """
    conn = get_db_connection(db_path)
    try:
        result = conn.execute(
            "DELETE FROM sos_requests WHERE id = ?", (sos_id,)
        )
        conn.commit()
        return result.rowcount > 0
    except Exception as e:
        conn.rollback()
        print(f"Error deleting SOS request: {e}")
        return False
    finally:
        close_db(conn)


def detect_incident_clusters(sos_list, threshold_km=2.0):
    """
    Detect spatial incident clusters among active unresolved SOS requests.
    Annotates each incident with:
    - in_cluster: bool
    - cluster_count: int
    - nearby_incident_ids: list[int]
    """
    active = [s for s in sos_list if s.get('status') != 'resolved' and s.get('dispatch_status') != 'RESOLVED' and s.get('latitude') is not None and s.get('longitude') is not None]

    clusters = {}
    for i, s1 in enumerate(active):
        nearby_ids = []
        lat1, lon1 = float(s1['latitude']), float(s1['longitude'])
        for j, s2 in enumerate(active):
            lat2, lon2 = float(s2['latitude']), float(s2['longitude'])
            # Haversine distance
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat / 2.0)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0)**2
            d = 6371.0 * 2.0 * math.asin(math.sqrt(a))
            if d <= threshold_km:
                nearby_ids.append(s2['id'])

        clusters[s1['id']] = {
            'in_cluster': len(nearby_ids) >= 2,
            'cluster_count': len(nearby_ids),
            'nearby_incident_ids': nearby_ids
        }

    return clusters

"""
Volunteer Assignment Model — Database access layer for emergency assignments (Phase 33).

Manages the complete lifecycle of emergency assignments:
  assigned -> accepted/declined -> completed (or cancelled)

Includes strict ownership verification to prevent IDOR, status validation,
audit logging integration, and volunteer availability synchronization.
"""

import math
from datetime import datetime, timezone
from models.db import get_db_connection, close_db
from models.volunteer_model import calculate_freshness, haversine_distance


def create_assignment(db_path, sos_id, volunteer_id, admin_id, notes=None):
    """
    Create a new emergency assignment for an approved volunteer.

    Validations:
    - SOS must exist and not be resolved.
    - Volunteer must exist, be ACTIVE, and have an active user account.
    - No existing active assignment ('assigned' or 'accepted') for this SOS.

    Returns: (success: bool, message: str, assignment_id: int or None)
    """
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()

        # 1. Verify SOS
        sos = cur.execute("SELECT id, status, dispatch_status FROM sos_requests WHERE id = ?", (sos_id,)).fetchone()
        if not sos:
            return False, f"SOS #{sos_id} does not exist.", None
        if sos['status'] == 'resolved':
            return False, f"This emergency (SOS #{sos_id}) has already been resolved.", None

        # 2. Verify Volunteer
        vol = cur.execute(
            """SELECT v.id, v.user_id, v.name, v.phone, v.status, v.availability, u.is_active, u.is_volunteer
               FROM volunteers v
               JOIN users u ON v.user_id = u.id
               WHERE v.id = ?""",
            (volunteer_id,)
        ).fetchone()

        if not vol:
            return False, f"Volunteer #{volunteer_id} does not exist.", None
        if vol['status'] != 'ACTIVE' or vol['is_active'] != 1 or vol['is_volunteer'] != 1:
            return False, f"Volunteer '{vol['name']}' is not an active, approved volunteer.", None

        # 3. Check for existing active assignment on this SOS
        active_existing = cur.execute(
            "SELECT id FROM volunteer_assignments WHERE sos_id = ? AND status IN ('assigned', 'accepted')",
            (sos_id,)
        ).fetchone()
        if active_existing:
            return False, f"SOS #{sos_id} is already assigned to a volunteer (Assignment #{active_existing['id']}).", None

        # 4. Insert assignment record
        cur.execute(
            """INSERT INTO volunteer_assignments (sos_id, volunteer_id, assigned_by_admin_id, status, notes)
               VALUES (?, ?, ?, 'assigned', ?)""",
            (sos_id, volunteer_id, admin_id, notes)
        )
        assignment_id = cur.lastrowid

        # 5. Update SOS request record
        cur.execute(
            """UPDATE sos_requests
               SET assigned_volunteer_id = ?, status = 'assigned', dispatch_status = 'ASSIGNED', assigned_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (volunteer_id, sos_id)
        )

        conn.commit()

        # 6. Record in admin audit log (fault-isolated)
        try:
            from models.admin_activity_model import create_admin_activity
            create_admin_activity(
                db_path=db_path,
                admin_user_id=admin_id,
                action_type='VOLUNTEER_ASSIGNMENT_CREATED',
                description=f"Admin assigned volunteer #{volunteer_id} ({vol['name']}) to Emergency SOS #{sos_id}.",
                entity_type='VOLUNTEER_ASSIGNMENT',
                entity_id=assignment_id
            )
        except Exception as e:
            print(f"Audit log error in create_assignment: {e}")

        return True, f"Volunteer '{vol['name']}' successfully assigned to SOS #{sos_id}.", assignment_id

    except Exception as e:
        conn.rollback()
        return False, f"Database error creating assignment: {e}", None
    finally:
        close_db(conn)


def get_assignment_by_id(db_path, assignment_id):
    """Retrieve assignment record with related SOS and volunteer details."""
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()
        query = """
            SELECT va.*,
                   v.name AS volunteer_name, v.phone AS volunteer_phone, v.user_id AS volunteer_user_id,
                   s.latitude AS sos_latitude, s.longitude AS sos_longitude, s.message AS sos_message,
                   s.status AS sos_status, s.priority AS sos_priority, s.priority_reason AS sos_priority_reason,
                   s.dispatch_status AS sos_dispatch_status, s.created_at AS sos_created_at,
                   u.name AS pilgrim_name, u.phone AS pilgrim_phone, u.emergency_contact AS pilgrim_emergency_contact,
                   adm.name AS assigned_by_name
            FROM volunteer_assignments va
            JOIN volunteers v ON va.volunteer_id = v.id
            JOIN sos_requests s ON va.sos_id = s.id
            LEFT JOIN users u ON s.user_id = u.id
            LEFT JOIN users adm ON va.assigned_by_admin_id = adm.id
            WHERE va.id = ?
        """
        row = cur.execute(query, (assignment_id,)).fetchone()
        return dict(row) if row else None
    finally:
        close_db(conn)


def get_assignments_for_volunteer(db_path, volunteer_id, status=None):
    """
    Get all emergency assignments for a specific volunteer.
    If status is specified ('assigned', 'accepted', 'completed', 'declined', 'cancelled'), filters by that status.
    """
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()
        if status:
            query = """
                SELECT va.*, s.latitude AS sos_latitude, s.longitude AS sos_longitude,
                       s.message AS sos_message, s.priority AS sos_priority, s.status AS sos_status,
                       s.created_at AS sos_created_at,
                       u.name AS pilgrim_name, u.phone AS pilgrim_phone,
                       adm.name AS assigned_by_name
                FROM volunteer_assignments va
                JOIN sos_requests s ON va.sos_id = s.id
                LEFT JOIN users u ON s.user_id = u.id
                LEFT JOIN users adm ON va.assigned_by_admin_id = adm.id
                WHERE va.volunteer_id = ? AND va.status = ?
                ORDER BY va.created_at DESC
            """
            rows = cur.execute(query, (volunteer_id, status)).fetchall()
        else:
            query = """
                SELECT va.*, s.latitude AS sos_latitude, s.longitude AS sos_longitude,
                       s.message AS sos_message, s.priority AS sos_priority, s.status AS sos_status,
                       s.created_at AS sos_created_at,
                       u.name AS pilgrim_name, u.phone AS pilgrim_phone,
                       adm.name AS assigned_by_name
                FROM volunteer_assignments va
                JOIN sos_requests s ON va.sos_id = s.id
                LEFT JOIN users u ON s.user_id = u.id
                LEFT JOIN users adm ON va.assigned_by_admin_id = adm.id
                WHERE va.volunteer_id = ?
                ORDER BY va.created_at DESC
            """
            rows = cur.execute(query, (volunteer_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_db(conn)


def get_active_assignments_for_volunteer(db_path, volunteer_id):
    """Get active assignments (assigned or accepted) for a volunteer."""
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()
        query = """
            SELECT va.*, s.latitude AS sos_latitude, s.longitude AS sos_longitude,
                   s.message AS sos_message, s.priority AS sos_priority, s.status AS sos_status,
                   s.created_at AS sos_created_at,
                   u.name AS pilgrim_name, u.phone AS pilgrim_phone,
                   adm.name AS assigned_by_name
            FROM volunteer_assignments va
            JOIN sos_requests s ON va.sos_id = s.id
            LEFT JOIN users u ON s.user_id = u.id
            LEFT JOIN users adm ON va.assigned_by_admin_id = adm.id
            WHERE va.volunteer_id = ? AND va.status IN ('assigned', 'accepted')
            ORDER BY va.created_at DESC
        """
        rows = cur.execute(query, (volunteer_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_db(conn)


def accept_assignment(db_path, assignment_id, volunteer_user_id):
    """
    Volunteer accepts an emergency assignment.

    Security validations:
    - Assignment must belong to the volunteer linked to volunteer_user_id.
    - Assignment status must be 'assigned'.
    - Linked SOS must not be resolved.

    State changes:
    - volunteer_assignments.status -> 'accepted'
    - sos_requests.dispatch_status -> 'RESPONDING'
    - sos_requests.acknowledged_at -> CURRENT_TIMESTAMP
    - volunteers.availability -> 'BUSY'
    """
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()

        # 1. Fetch assignment and verify ownership
        query = """
            SELECT va.id, va.sos_id, va.volunteer_id, va.status, v.user_id, v.name AS volunteer_name,
                   s.status AS sos_status
            FROM volunteer_assignments va
            JOIN volunteers v ON va.volunteer_id = v.id
            JOIN sos_requests s ON va.sos_id = s.id
            WHERE va.id = ?
        """
        row = cur.execute(query, (assignment_id,)).fetchone()
        if not row:
            return False, f"Assignment #{assignment_id} not found."

        if row['user_id'] != volunteer_user_id:
            return False, "Access denied: You do not have permission to modify this assignment."

        if row['status'] != 'assigned':
            return False, f"Assignment cannot be accepted from current status '{row['status']}'."

        if row['sos_status'] == 'resolved':
            return False, "This emergency incident has already been resolved by administration."

        # 2. Update assignment status
        cur.execute(
            """UPDATE volunteer_assignments
               SET status = 'accepted', updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (assignment_id,)
        )

        # 3. Update SOS dispatch status
        cur.execute(
            """UPDATE sos_requests
               SET dispatch_status = 'RESPONDING', acknowledged_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (row['sos_id'],)
        )

        # 4. Set volunteer availability to BUSY
        cur.execute(
            "UPDATE volunteers SET availability = 'BUSY' WHERE id = ?",
            (row['volunteer_id'],)
        )

        conn.commit()

        # 5. Audit Log
        try:
            from models.admin_activity_model import create_admin_activity
            create_admin_activity(
                db_path=db_path,
                admin_user_id=volunteer_user_id,
                action_type='VOLUNTEER_ASSIGNMENT_ACCEPTED',
                description=f"Volunteer '{row['volunteer_name']}' accepted assignment #{assignment_id} for Emergency SOS #{row['sos_id']}.",
                entity_type='VOLUNTEER_ASSIGNMENT',
                entity_id=assignment_id
            )
        except Exception:
            pass

        return True, f"You have accepted Emergency SOS #{row['sos_id']}."

    except Exception as e:
        conn.rollback()
        return False, f"Database error accepting assignment: {e}"
    finally:
        close_db(conn)


def decline_assignment(db_path, assignment_id, volunteer_user_id, reason=None):
    """
    Volunteer declines an emergency assignment.

    State changes:
    - volunteer_assignments.status -> 'declined'
    - sos_requests.dispatch_status -> 'DECLINED', assigned_volunteer_id -> NULL, status -> 'pending'
    - volunteers.availability -> 'AVAILABLE' (if no other active assignment)
    """
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()

        query = """
            SELECT va.id, va.sos_id, va.volunteer_id, va.status, v.user_id, v.name AS volunteer_name
            FROM volunteer_assignments va
            JOIN volunteers v ON va.volunteer_id = v.id
            WHERE va.id = ?
        """
        row = cur.execute(query, (assignment_id,)).fetchone()
        if not row:
            return False, f"Assignment #{assignment_id} not found."

        if row['user_id'] != volunteer_user_id:
            return False, "Access denied: You do not have permission to modify this assignment."

        if row['status'] != 'assigned':
            return False, f"Assignment cannot be declined from status '{row['status']}'."

        # 1. Update assignment status
        cur.execute(
            """UPDATE volunteer_assignments
               SET status = 'declined', notes = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (reason, assignment_id)
        )

        # 2. Reset SOS request to unassigned / pending
        cur.execute(
            """UPDATE sos_requests
               SET dispatch_status = 'DECLINED', assigned_volunteer_id = NULL, status = 'pending'
               WHERE id = ?""",
            (row['sos_id'],)
        )

        # 3. Check other active assignments for volunteer
        other_active = cur.execute(
            "SELECT id FROM volunteer_assignments WHERE volunteer_id = ? AND status IN ('assigned', 'accepted') AND id != ?",
            (row['volunteer_id'], assignment_id)
        ).fetchone()

        if not other_active:
            cur.execute("UPDATE volunteers SET availability = 'AVAILABLE' WHERE id = ?", (row['volunteer_id'],))

        conn.commit()

        # 4. Audit Log
        try:
            from models.admin_activity_model import create_admin_activity
            create_admin_activity(
                db_path=db_path,
                admin_user_id=volunteer_user_id,
                action_type='VOLUNTEER_ASSIGNMENT_DECLINED',
                description=f"Volunteer '{row['volunteer_name']}' declined assignment #{assignment_id} for SOS #{row['sos_id']}." + (f" Reason: {reason}" if reason else ""),
                entity_type='VOLUNTEER_ASSIGNMENT',
                entity_id=assignment_id
            )
        except Exception:
            pass

        return True, f"Assignment #{assignment_id} declined."

    except Exception as e:
        conn.rollback()
        return False, f"Database error declining assignment: {e}"
    finally:
        close_db(conn)


def complete_assignment(db_path, assignment_id, volunteer_user_id, notes=None):
    """
    Volunteer marks emergency assistance as completed.

    IMPORTANT SAFETY RULE:
    Does NOT automatically resolve the SOS. Admin remains responsible for final verification and resolution.

    State changes:
    - volunteer_assignments.status -> 'completed'
    - sos_requests.dispatch_status -> 'VOLUNTEER_COMPLETED'
    - volunteers.availability -> 'AVAILABLE' (if no other active assignment)
    """
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()

        query = """
            SELECT va.id, va.sos_id, va.volunteer_id, va.status, v.user_id, v.name AS volunteer_name
            FROM volunteer_assignments va
            JOIN volunteers v ON va.volunteer_id = v.id
            WHERE va.id = ?
        """
        row = cur.execute(query, (assignment_id,)).fetchone()
        if not row:
            return False, f"Assignment #{assignment_id} not found."

        if row['user_id'] != volunteer_user_id:
            return False, "Access denied: You do not have permission to modify this assignment."

        if row['status'] != 'accepted':
            return False, f"Assignment must be in 'accepted' status to complete (current: '{row['status']}')."

        # 1. Update assignment status
        cur.execute(
            """UPDATE volunteer_assignments
               SET status = 'completed', notes = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (notes, assignment_id)
        )

        # 2. Update SOS dispatch status
        cur.execute(
            """UPDATE sos_requests
               SET dispatch_status = 'VOLUNTEER_COMPLETED'
               WHERE id = ?""",
            (row['sos_id'],)
        )

        # 3. Restore volunteer availability if no other active assignments
        other_active = cur.execute(
            "SELECT id FROM volunteer_assignments WHERE volunteer_id = ? AND status IN ('assigned', 'accepted') AND id != ?",
            (row['volunteer_id'], assignment_id)
        ).fetchone()

        if not other_active:
            cur.execute("UPDATE volunteers SET availability = 'AVAILABLE' WHERE id = ?", (row['volunteer_id'],))

        conn.commit()

        # 4. Audit Log
        try:
            from models.admin_activity_model import create_admin_activity
            create_admin_activity(
                db_path=db_path,
                admin_user_id=volunteer_user_id,
                action_type='VOLUNTEER_ASSIGNMENT_COMPLETED',
                description=f"Volunteer '{row['volunteer_name']}' completed assistance for Emergency SOS #{row['sos_id']}.",
                entity_type='VOLUNTEER_ASSIGNMENT',
                entity_id=assignment_id
            )
        except Exception:
            pass

        return True, f"Emergency assistance for SOS #{row['sos_id']} marked as completed."

    except Exception as e:
        conn.rollback()
        return False, f"Database error completing assignment: {e}"
    finally:
        close_db(conn)


def cancel_assignment(db_path, assignment_id, admin_id, reason=None):
    """
    Administrator cancels an emergency assignment.

    State changes:
    - volunteer_assignments.status -> 'cancelled'
    - sos_requests.dispatch_status -> 'UNASSIGNED', assigned_volunteer_id -> NULL, status -> 'pending'
    - volunteers.availability -> 'AVAILABLE' (if no other active assignment)
    """
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()

        query = """
            SELECT va.id, va.sos_id, va.volunteer_id, va.status, v.name AS volunteer_name
            FROM volunteer_assignments va
            JOIN volunteers v ON va.volunteer_id = v.id
            WHERE va.id = ?
        """
        row = cur.execute(query, (assignment_id,)).fetchone()
        if not row:
            return False, f"Assignment #{assignment_id} not found."

        # 1. Update assignment record
        cur.execute(
            """UPDATE volunteer_assignments
               SET status = 'cancelled', notes = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (reason, assignment_id)
        )

        # 2. Reset SOS request
        cur.execute(
            """UPDATE sos_requests
               SET dispatch_status = 'UNASSIGNED', assigned_volunteer_id = NULL, status = 'pending'
               WHERE id = ?""",
            (row['sos_id'],)
        )

        # 3. Restore volunteer availability if no other active assignments
        other_active = cur.execute(
            "SELECT id FROM volunteer_assignments WHERE volunteer_id = ? AND status IN ('assigned', 'accepted') AND id != ?",
            (row['volunteer_id'], assignment_id)
        ).fetchone()

        if not other_active:
            cur.execute("UPDATE volunteers SET availability = 'AVAILABLE' WHERE id = ?", (row['volunteer_id'],))

        conn.commit()

        # 4. Audit Log
        try:
            from models.admin_activity_model import create_admin_activity
            create_admin_activity(
                db_path=db_path,
                admin_user_id=admin_id,
                action_type='VOLUNTEER_ASSIGNMENT_CANCELLED',
                description=f"Admin cancelled assignment #{assignment_id} for SOS #{row['sos_id']} (Volunteer: {row['volunteer_name']})." + (f" Reason: {reason}" if reason else ""),
                entity_type='VOLUNTEER_ASSIGNMENT',
                entity_id=assignment_id
            )
        except Exception:
            pass

        return True, f"Assignment #{assignment_id} has been cancelled."

    except Exception as e:
        conn.rollback()
        return False, f"Database error cancelling assignment: {e}"
    finally:
        close_db(conn)


def format_approx_distance(distance_km):
    """Format distance into user-friendly text like '800 m' or '1.4 km'."""
    if distance_km is None:
        return "Location unavailable"
    if distance_km < 1.0:
        meters = int(distance_km * 1000)
        return f"{meters} m (approx.)"
    return f"{distance_km:.1f} km (approx.)"


def get_candidate_volunteers_for_sos(db_path, sos_id):
    """
    Discover, calculate approximate distance, and sort approved active volunteers for assigning to an SOS.
    """
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()
        sos = cur.execute("SELECT id, latitude, longitude, status FROM sos_requests WHERE id = ?", (sos_id,)).fetchone()
        if not sos:
            return []

        sos_lat = sos['latitude']
        sos_lon = sos['longitude']

        vols = cur.execute(
            """SELECT v.*, u.created_at AS user_created_at, u.emergency_contact AS user_emergency_contact
               FROM volunteers v
               JOIN users u ON v.user_id = u.id
               WHERE v.status = 'ACTIVE' AND u.is_active = 1 AND u.is_volunteer = 1"""
        ).fetchall()

        candidates = []
        for v in vols:
            freshness, delta = calculate_freshness(v['location_updated_at'], v['status'])
            dist_km = None
            if sos_lat is not None and sos_lon is not None and v['latitude'] is not None and v['longitude'] is not None:
                dist_km = haversine_distance(sos_lat, sos_lon, v['latitude'], v['longitude'])

            # Check if volunteer is currently assigned to an active incident
            active_assign = cur.execute(
                """SELECT va.id, va.sos_id, va.status
                   FROM volunteer_assignments va
                   WHERE va.volunteer_id = ? AND va.status IN ('assigned', 'accepted')""",
                (v['id'],)
            ).fetchone()

            avail = v['availability'] or 'AVAILABLE'
            if active_assign:
                avail = 'BUSY'

            from models.volunteer_model import is_volunteer_online, format_last_seen
            online = is_volunteer_online(v)
            last_seen_str = format_last_seen(v['location_updated_at'])


            candidates.append({
                'id': v['id'],
                'user_id': v['user_id'],
                'name': v['name'],
                'phone': v['phone'] if online else None,
                'status': v['status'],
                'availability': avail,
                'is_online': online,
                'can_contact': online,
                'last_seen': last_seen_str,
                'call_url': f"tel:{v['phone']}" if online else None,
                'whatsapp_url': f"https://wa.me/91{v['phone']}?text=Emergency%20Alert%3A%20SOS%20%23{sos_id}." if online else None,
                'is_sharing': v['is_sharing'] or 0,
                'latitude': v['latitude'],
                'longitude': v['longitude'],
                'accuracy': v['accuracy'],
                'freshness': freshness,
                'delta_seconds': delta,
                'distance_km': dist_km,
                'distance_str': format_approx_distance(dist_km),
                'active_assignment_sos_id': active_assign['sos_id'] if active_assign else None,
                'active_assignment_status': active_assign['status'] if active_assign else None,
                'location_updated_at': str(v['location_updated_at']) if v['location_updated_at'] else 'Never'
            })

        # Sort available first, then online/live/recent, then distance
        freshness_weights = {'LIVE': 0, 'RECENT': 1, 'STALE': 2, 'OFFLINE': 3}
        candidates.sort(key=lambda x: (
            0 if x['availability'] == 'AVAILABLE' else 1,
            0 if x['is_online'] else 1,
            freshness_weights.get(x['freshness'], 3),
            x['distance_km'] if x['distance_km'] is not None else 99999
        ))


        return candidates
    finally:
        close_db(conn)

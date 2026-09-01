"""
Volunteer Request Model — Database access layer for volunteer applications and admin approval workflow.

Manages:
- Volunteer registration request submission (status: PENDING)
- Request lookup and status tracking
- Admin review & approval (grants is_volunteer privilege and creates active volunteer record)
- Admin review & rejection (records reason and denies volunteer privilege)
- Querying and filtering requests for Admin Request Center
"""

from models.db import get_db_connection, close_db


def create_volunteer_request(db_path, user_id, location_area=None, experience_notes=None):
    """
    Insert a new volunteer registration request in PENDING status.
    Returns the new request ID or None on failure.
    """
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO volunteer_requests (user_id, status, location_area, experience_notes)
               VALUES (?, 'PENDING', ?, ?)""",
            (user_id, location_area, experience_notes)
        )
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        conn.rollback()
        print(f"Error creating volunteer request: {e}")
        return None
    finally:
        close_db(conn)


def get_volunteer_request_by_id(db_path, request_id):
    """
    Retrieve a volunteer request by its ID, joined with user profile and reviewer details.
    """
    conn = get_db_connection(db_path)
    try:
        row = conn.execute(
            """SELECT vr.*, 
                      u.name as user_name, u.phone as user_phone, 
                      u.emergency_contact as user_emergency_contact, u.medical_info as user_medical_info,
                      u.is_volunteer as user_is_volunteer, u.is_active as user_is_active,
                      rev.name as reviewer_name, rev.phone as reviewer_phone
               FROM volunteer_requests vr
               JOIN users u ON vr.user_id = u.id
               LEFT JOIN users rev ON vr.reviewed_by = rev.id
               WHERE vr.id = ?""",
            (request_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        close_db(conn)


def get_volunteer_request_by_user_id(db_path, user_id):
    """
    Retrieve the most recent volunteer request for a given user ID.
    """
    conn = get_db_connection(db_path)
    try:
        row = conn.execute(
            """SELECT vr.*, 
                      u.name as user_name, u.phone as user_phone,
                      u.emergency_contact as user_emergency_contact, u.medical_info as user_medical_info,
                      u.is_volunteer as user_is_volunteer
               FROM volunteer_requests vr
               JOIN users u ON vr.user_id = u.id
               WHERE vr.user_id = ?
               ORDER BY vr.id DESC
               LIMIT 1""",
            (user_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        close_db(conn)


def get_all_volunteer_requests(db_path, status_filter='ALL', search_query=None):
    """
    Retrieve all volunteer requests, optionally filtered by status and search keyword.
    Ordered by: PENDING status first, then newest requested_at DESC.
    """
    conn = get_db_connection(db_path)
    try:
        query = """
            SELECT vr.*, 
                   u.name as user_name, u.phone as user_phone,
                   u.emergency_contact as user_emergency_contact, u.medical_info as user_medical_info,
                   u.is_volunteer as user_is_volunteer,
                   rev.name as reviewer_name
            FROM volunteer_requests vr
            JOIN users u ON vr.user_id = u.id
            LEFT JOIN users rev ON vr.reviewed_by = rev.id
            WHERE 1=1
        """
        params = []

        status_clean = status_filter.upper().strip()
        if status_clean in ('PENDING', 'APPROVED', 'REJECTED'):
            query += " AND vr.status = ?"
            params.append(status_clean)

        if search_query:
            q_clean = f"%{search_query.strip()}%"
            query += " AND (u.name LIKE ? OR u.phone LIKE ? OR vr.location_area LIKE ? OR vr.experience_notes LIKE ?)"
            params.extend([q_clean, q_clean, q_clean, q_clean])

        query += """
            ORDER BY 
                CASE WHEN vr.status = 'PENDING' THEN 0 ELSE 1 END,
                vr.requested_at DESC
        """

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        close_db(conn)


def count_pending_volunteer_requests(db_path):
    """
    Count total number of pending volunteer applications.
    """
    conn = get_db_connection(db_path)
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM volunteer_requests WHERE status = 'PENDING'"
        ).fetchone()
        return row[0] if row else 0
    finally:
        close_db(conn)


def count_volunteer_requests_by_status(db_path):
    """
    Return breakdown stats: total, pending, approved, rejected.
    """
    conn = get_db_connection(db_path)
    try:
        total = conn.execute("SELECT COUNT(*) FROM volunteer_requests").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM volunteer_requests WHERE status = 'PENDING'").fetchone()[0]
        approved = conn.execute("SELECT COUNT(*) FROM volunteer_requests WHERE status = 'APPROVED'").fetchone()[0]
        rejected = conn.execute("SELECT COUNT(*) FROM volunteer_requests WHERE status = 'REJECTED'").fetchone()[0]
        return {
            'total': total,
            'pending': pending,
            'approved': approved,
            'rejected': rejected
        }
    finally:
        close_db(conn)


def approve_volunteer_request(db_path, request_id, admin_user_id):
    """
    Atomically approve a volunteer registration request.
    
    Actions in transaction:
    1. Verify request is currently PENDING.
    2. Set request status to APPROVED, reviewed_at = CURRENT_TIMESTAMP, reviewed_by = admin_user_id.
    3. Update users table: set is_volunteer = 1 for the applicant.
    4. Insert or update record in volunteers table with status 'ACTIVE'.
    
    Returns (success: bool, message: str, applicant: dict).
    """
    conn = get_db_connection(db_path)
    try:
        # Check current status
        cur = conn.cursor()
        req = cur.execute(
            "SELECT * FROM volunteer_requests WHERE id = ?", (request_id,)
        ).fetchone()

        if not req:
            return False, f"Volunteer request #{request_id} not found.", None

        if req['status'] != 'PENDING':
            return False, f"Request #{request_id} is already {req['status']}. Only PENDING requests can be approved.", dict(req)

        user_id = req['user_id']
        user = cur.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return False, f"User associated with request #{request_id} does not exist.", None

        # 1. Update volunteer_requests table
        cur.execute(
            """UPDATE volunteer_requests 
               SET status = 'APPROVED', reviewed_at = CURRENT_TIMESTAMP, reviewed_by = ?
               WHERE id = ? AND status = 'PENDING'""",
            (admin_user_id, request_id)
        )

        if cur.rowcount == 0:
            conn.rollback()
            return False, "Concurrent modification detected. Approval aborted.", None

        # 2. Grant volunteer privilege in users table
        cur.execute(
            "UPDATE users SET is_volunteer = 1 WHERE id = ?",
            (user_id,)
        )

        # 3. Ensure record exists in volunteers registry table
        existing_vol = cur.execute("SELECT * FROM volunteers WHERE user_id = ?", (user_id,)).fetchone()
        if existing_vol:
            cur.execute(
                "UPDATE volunteers SET status = 'ACTIVE', availability = 'AVAILABLE' WHERE user_id = ?",
                (user_id,)
            )
        else:
            cur.execute(
                """INSERT INTO volunteers (name, phone, user_id, status, availability)
                   VALUES (?, ?, ?, 'ACTIVE', 'AVAILABLE')""",
                (user['name'], user['phone'], user_id)
            )

        conn.commit()
        applicant_info = {
            'id': user['id'],
            'name': user['name'],
            'phone': user['phone'],
            'request_id': request_id
        }
        return True, f"Volunteer application #{request_id} for '{user['name']}' has been approved.", applicant_info

    except Exception as e:
        conn.rollback()
        print(f"Error approving volunteer request: {e}")
        return False, f"Database error approving request: {e}", None
    finally:
        close_db(conn)


def reject_volunteer_request(db_path, request_id, admin_user_id, rejection_reason=None):
    """
    Atomically reject a volunteer registration request.
    
    Actions in transaction:
    1. Verify request is currently PENDING.
    2. Set request status to REJECTED, reviewed_at = CURRENT_TIMESTAMP, reviewed_by = admin_user_id, rejection_reason.
    3. Ensure user is_volunteer remains 0.
    
    Returns (success: bool, message: str, applicant: dict).
    """
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()
        req = cur.execute(
            "SELECT * FROM volunteer_requests WHERE id = ?", (request_id,)
        ).fetchone()

        if not req:
            return False, f"Volunteer request #{request_id} not found.", None

        if req['status'] != 'PENDING':
            return False, f"Request #{request_id} is already {req['status']}. Only PENDING requests can be rejected.", dict(req)

        user_id = req['user_id']
        user = cur.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

        # Update volunteer_requests table
        cur.execute(
            """UPDATE volunteer_requests 
               SET status = 'REJECTED', reviewed_at = CURRENT_TIMESTAMP, reviewed_by = ?, rejection_reason = ?
               WHERE id = ? AND status = 'PENDING'""",
            (admin_user_id, rejection_reason or 'Application declined by administrator.', request_id)
        )

        if cur.rowcount == 0:
            conn.rollback()
            return False, "Concurrent modification detected. Rejection aborted.", None

        # If an unapproved record existed in volunteers table, set it inactive
        cur.execute("UPDATE volunteers SET status = 'INACTIVE' WHERE user_id = ?", (user_id,))

        conn.commit()
        applicant_info = {
            'id': user['id'] if user else user_id,
            'name': user['name'] if user else 'Applicant',
            'phone': user['phone'] if user else '—',
            'request_id': request_id
        }
        return True, f"Volunteer application #{request_id} has been rejected.", applicant_info

    except Exception as e:
        conn.rollback()
        print(f"Error rejecting volunteer request: {e}")
        return False, f"Database error rejecting request: {e}", None
    finally:
        close_db(conn)

"""
Admin Activity Model — Database access layer for the 'admin_activity_log' table.

Provides audit logging and retrieval functions for administrative and operational actions.
Uses raw SQL via sqlite3 with parameterization (no ORM).

Table schema:
    id              INTEGER PRIMARY KEY AUTOINCREMENT
    admin_user_id   INTEGER FK → users.id
    action_type     TEXT NOT NULL (e.g. ADMIN_LOGIN, ADMIN_LOGOUT, SOS_RESOLVED, FACILITY_CREATED, FACILITY_UPDATED, FACILITY_DELETED)
    description     TEXT NOT NULL
    entity_type     TEXT (e.g. SOS, FACILITY, AUTH)
    entity_id       INTEGER
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
"""

from models.db import get_db_connection, close_db


def _ensure_table_exists(conn):
    """Ensure the admin_activity_log table exists in the connected database."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS admin_activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_user_id INTEGER,
            action_type TEXT NOT NULL,
            description TEXT NOT NULL,
            entity_type TEXT,
            entity_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (admin_user_id) REFERENCES users(id)
        )
    """)
    conn.commit()


def create_admin_activity(db_path, admin_user_id, action_type, description, entity_type=None, entity_id=None):
    """
    Safely insert a new administrative activity log record.
    Failure in audit logging does not raise an exception to the caller.

    Args:
        db_path: Path to the SQLite database file.
        admin_user_id: ID of the performing admin user (or None for system).
        action_type: Action code (ADMIN_LOGIN, SOS_RESOLVED, etc.).
        description: Plain-text non-sensitive description.
        entity_type: Entity category (SOS, FACILITY, AUTH).
        entity_id: Primary key of affected entity.

    Returns:
        The ID of the inserted record, or None on failure.
    """
    conn = None
    try:
        conn = get_db_connection(db_path)
        _ensure_table_exists(conn)
        cursor = conn.execute(
            """INSERT INTO admin_activity_log (admin_user_id, action_type, description, entity_type, entity_id)
               VALUES (?, ?, ?, ?, ?)""",
            (admin_user_id, action_type, description, entity_type, entity_id)
        )
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error recording admin activity: {e}")
        return None
    finally:
        if conn:
            close_db(conn)


def get_all_admin_activities(db_path, limit=100):
    """
    Retrieve all audit records, newest first, joining admin user details.

    Args:
        db_path: Path to the SQLite database.
        limit: Maximum number of records to return.

    Returns:
        List of sqlite3.Row objects.
    """
    conn = None
    try:
        conn = get_db_connection(db_path)
        _ensure_table_exists(conn)
        records = conn.execute(
            """SELECT a.*, u.name as admin_name, u.phone as admin_phone
               FROM admin_activity_log a
               LEFT JOIN users u ON a.admin_user_id = u.id
               ORDER BY a.created_at DESC, a.id DESC
               LIMIT ?""",
            (limit,)
        ).fetchall()
        return records
    except Exception as e:
        print(f"Error fetching admin activities: {e}")
        return []
    finally:
        if conn:
            close_db(conn)


def get_admin_activity_by_id(db_path, activity_id):
    """
    Retrieve a single audit activity record by its ID.

    Args:
        db_path: Path to the SQLite database.
        activity_id: Primary key ID of the audit log record.

    Returns:
        sqlite3.Row object or None.
    """
    conn = None
    try:
        conn = get_db_connection(db_path)
        _ensure_table_exists(conn)
        record = conn.execute(
            """SELECT a.*, u.name as admin_name, u.phone as admin_phone
               FROM admin_activity_log a
               LEFT JOIN users u ON a.admin_user_id = u.id
               WHERE a.id = ?""",
            (activity_id,)
        ).fetchone()
        return record
    except Exception as e:
        print(f"Error fetching admin activity #{activity_id}: {e}")
        return None
    finally:
        if conn:
            close_db(conn)


def get_filtered_admin_activities(db_path, action_type=None, search_query=None, limit=100):
    """
    Retrieve audit records with optional action type and keyword search filters.

    Args:
        db_path: Path to the SQLite database.
        action_type: Action type string (e.g. 'SOS_RESOLVED', 'FACILITY_CREATED', or 'all').
        search_query: Search term for description, admin name, or entity type.
        limit: Maximum number of records.

    Returns:
        List of sqlite3.Row objects.
    """
    conn = None
    try:
        conn = get_db_connection(db_path)
        _ensure_table_exists(conn)

        query = """
            SELECT a.*, u.name as admin_name, u.phone as admin_phone
            FROM admin_activity_log a
            LEFT JOIN users u ON a.admin_user_id = u.id
            WHERE 1=1
        """
        params = []

        if action_type and action_type.strip().lower() not in ('all', ''):
            query += " AND UPPER(a.action_type) = UPPER(?)"
            params.append(action_type.strip())

        if search_query and search_query.strip():
            term = f"%{search_query.strip()}%"
            query += " AND (a.description LIKE ? OR a.action_type LIKE ? OR a.entity_type LIKE ? OR u.name LIKE ?)"
            params.extend([term, term, term, term])

        query += " ORDER BY a.created_at DESC, a.id DESC LIMIT ?"
        params.append(limit)

        records = conn.execute(query, params).fetchall()
        return records
    except Exception as e:
        print(f"Error searching admin activities: {e}")
        return []
    finally:
        if conn:
            close_db(conn)


def get_activity_stats(db_path):
    """
    Calculate summary statistics for the audit log dashboard.

    Returns:
        dict with total, today_count, sos_count, facility_count, auth_count.
    """
    conn = None
    try:
        conn = get_db_connection(db_path)
        _ensure_table_exists(conn)

        total = conn.execute("SELECT COUNT(*) FROM admin_activity_log").fetchone()[0]
        today_count = conn.execute(
            "SELECT COUNT(*) FROM admin_activity_log WHERE date(created_at) = date('now')"
        ).fetchone()[0]
        sos_count = conn.execute(
            "SELECT COUNT(*) FROM admin_activity_log WHERE action_type LIKE 'SOS_%' OR entity_type = 'SOS'"
        ).fetchone()[0]
        facility_count = conn.execute(
            "SELECT COUNT(*) FROM admin_activity_log WHERE action_type LIKE 'FACILITY_%' OR entity_type = 'FACILITY'"
        ).fetchone()[0]
        auth_count = conn.execute(
            "SELECT COUNT(*) FROM admin_activity_log WHERE action_type LIKE 'ADMIN_%' OR entity_type = 'AUTH'"
        ).fetchone()[0]

        return {
            'total': total,
            'today': today_count,
            'sos': sos_count,
            'facility': facility_count,
            'auth': auth_count
        }
    except Exception as e:
        print(f"Error computing activity stats: {e}")
        return {'total': 0, 'today': 0, 'sos': 0, 'facility': 0, 'auth': 0}
    finally:
        if conn:
            close_db(conn)


def get_recent_admin_activities(db_path, limit=5):
    """
    Retrieve the most recent audit activity records for the Admin Dashboard overview.

    Args:
        db_path: Path to the SQLite database.
        limit: Number of records (default 5).

    Returns:
        List of sqlite3.Row objects.
    """
    return get_all_admin_activities(db_path, limit=limit)

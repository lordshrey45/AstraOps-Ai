"""
User Model — Database access layer for the 'users' table.

Provides CRUD operations for pilgrim user accounts.
Uses raw SQL via sqlite3 (no ORM) as per architecture.

Table schema:
    id              INTEGER PK AUTOINCREMENT
    name            TEXT NOT NULL
    phone           TEXT UNIQUE NOT NULL
    password_hash   TEXT NOT NULL
    emergency_contact TEXT
    medical_info    TEXT
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
"""

from models.db import get_db_connection, close_db


def create_user(db_path, name, phone, password_hash, emergency_contact=None, medical_info=None, is_admin=0, is_volunteer=0):
    """
    Insert a new user into the users table.

    Args:
        db_path: Path to the SQLite database file.
        name: Pilgrim's full name.
        phone: Phone number (unique, used as login identifier).
        password_hash: Hashed password (via werkzeug.security).
        emergency_contact: Optional emergency contact info.
        medical_info: Optional medical information (e.g., allergies).
        is_admin: Admin status (0=user, 1=admin).
        is_volunteer: Volunteer status (0=user, 1=volunteer).

    Returns:
        The ID of the newly created user, or None on failure.
    """
    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute(
            """INSERT INTO users (name, phone, password_hash, emergency_contact, medical_info, is_admin, is_volunteer)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, phone, password_hash, emergency_contact, medical_info, int(is_admin), int(is_volunteer))
        )
        conn.commit()
        return cursor.lastrowid


    except Exception as e:
        conn.rollback()
        print(f"Error creating user: {e}")
        return None
    finally:
        close_db(conn)


def get_user_by_id(db_path, user_id):
    """
    Retrieve a user by their ID.

    Args:
        db_path: Path to the SQLite database file.
        user_id: The user's primary key ID.

    Returns:
        A sqlite3.Row object (dict-like) with user data, or None if not found.
    """
    conn = get_db_connection(db_path)
    try:
        user = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return user
    finally:
        close_db(conn)


def get_user_by_phone(db_path, phone):
    """
    Retrieve a user by their phone number (login identifier).

    Args:
        db_path: Path to the SQLite database file.
        phone: The user's phone number.

    Returns:
        A sqlite3.Row object with user data, or None if not found.
    """
    conn = get_db_connection(db_path)
    try:
        user = conn.execute(
            "SELECT * FROM users WHERE phone = ?", (phone,)
        ).fetchone()
        return user
    finally:
        close_db(conn)


def update_user(db_path, user_id, name=None, emergency_contact=None, medical_info=None):
    """
    Update a user's profile information.

    Only updates fields that are provided (not None).

    Args:
        db_path: Path to the SQLite database file.
        user_id: The user's primary key ID.
        name: Updated name (optional).
        emergency_contact: Updated emergency contact (optional).
        medical_info: Updated medical info (optional).

    Returns:
        True if the update was successful, False otherwise.
    """
    # Build dynamic UPDATE query based on provided fields
    fields = []
    values = []

    if name is not None:
        fields.append("name = ?")
        values.append(name)
    if emergency_contact is not None:
        fields.append("emergency_contact = ?")
        values.append(emergency_contact)
    if medical_info is not None:
        fields.append("medical_info = ?")
        values.append(medical_info)

    if not fields:
        return False  # Nothing to update

    values.append(user_id)

    conn = get_db_connection(db_path)
    try:
        conn.execute(
            f"UPDATE users SET {', '.join(fields)} WHERE id = ?",
            tuple(values)
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error updating user: {e}")
        return False
    finally:
        close_db(conn)


def update_password(db_path, user_id, new_password_hash):
    """
    Update a user's password hash.

    Args:
        db_path: Path to the SQLite database file.
        user_id: The user's primary key ID.
        new_password_hash: The new hashed password.

    Returns:
        True if successful, False otherwise.
    """
    conn = get_db_connection(db_path)
    try:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_password_hash, user_id)
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error updating password: {e}")
        return False
    finally:
        close_db(conn)


def delete_user(db_path, user_id):
    """
    Delete a user by their ID.

    Args:
        db_path: Path to the SQLite database file.
        user_id: The user's primary key ID.

    Returns:
        True if the user was deleted, False otherwise.
    """
    conn = get_db_connection(db_path)
    try:
        result = conn.execute(
            "DELETE FROM users WHERE id = ?", (user_id,)
        )
        conn.commit()
        return result.rowcount > 0
    except Exception as e:
        conn.rollback()
        print(f"Error deleting user: {e}")
        return False
    finally:
        close_db(conn)


def get_all_users(db_path):
    """
    Retrieve all users from the database with integrated role and volunteer status.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        A list of sqlite3.Row objects.
    """
    conn = get_db_connection(db_path)
    try:
        users = conn.execute(
            """SELECT u.id, u.name, u.phone, u.emergency_contact, u.medical_info, 
                      u.is_admin, u.is_active, u.is_volunteer, u.created_at,
                      v.id AS volunteer_id, v.status AS volunteer_status,
                      vr.status AS volunteer_request_status
               FROM users u
               LEFT JOIN volunteers v ON u.id = v.user_id
               LEFT JOIN (
                   SELECT vr1.user_id, vr1.status 
                   FROM volunteer_requests vr1
                   INNER JOIN (
                       SELECT user_id, MAX(id) as max_id 
                       FROM volunteer_requests 
                       GROUP BY user_id
                   ) vr2 ON vr1.id = vr2.max_id
               ) vr ON u.id = vr.user_id
               ORDER BY u.id ASC"""
        ).fetchall()
        return users
    finally:
        close_db(conn)



def is_user_admin(db_path, user_id):
    """
    Check if a user has admin privileges.

    Args:
        db_path: Path to the SQLite database file.
        user_id: User's primary key ID.

    Returns:
        True if the user is an admin, False otherwise.
    """
    if not user_id:
        return False
    user = get_user_by_id(db_path, user_id)
    if not user:
        return False
    try:
        return bool(user['is_admin'])
    except (KeyError, IndexError):
        return False


def get_user_account_status(db_path, user_id):
    """
    Get the active status (1 for active, 0 for inactive) of a user account.

    Args:
        db_path: Path to the SQLite database file.
        user_id: User's primary key ID.

    Returns:
        Integer (1 or 0), or None if user not found.
    """
    user = get_user_by_id(db_path, user_id)
    if not user:
        return None
    try:
        return int(user['is_active']) if user['is_active'] is not None else 1
    except (KeyError, IndexError):
        return 1


def set_user_active_status(db_path, user_id, is_active):
    """
    Set the active status (1 for active, 0 for inactive) of a user account.

    Args:
        db_path: Path to SQLite database file.
        user_id: User's primary key ID.
        is_active: Status integer (1 for active, 0 for disabled).

    Returns:
        True if successfully updated, False otherwise.
    """
    conn = get_db_connection(db_path)
    try:
        conn.execute(
            "UPDATE users SET is_active = ? WHERE id = ?",
            (int(is_active), user_id)
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error setting user active status: {e}")
        return False
    finally:
        close_db(conn)


def count_active_admins(db_path):
    """
    Count total number of active administrator accounts in the database.

    Args:
        db_path: Path to SQLite database file.

    Returns:
        Integer count of active administrators.
    """
    conn = get_db_connection(db_path)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM users WHERE is_admin = 1 AND (is_active = 1 OR is_active IS NULL)"
        ).fetchone()[0]
        return count
    except Exception as e:
        print(f"Error counting active admins: {e}")
        return 0
    finally:
        close_db(conn)


def is_user_volunteer(db_path, user_id):
    """
    Check if a given user has active volunteer privileges.
    Returns True if user has is_volunteer=1 or exists in volunteers table, False otherwise.
    """
    if user_id is None:
        return False
    conn = get_db_connection(db_path)
    try:
        user = conn.execute(
            "SELECT is_volunteer, is_active FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not user:
            return False
        is_active = user['is_active'] if ('is_active' in user.keys() and user['is_active'] is not None) else 1
        if int(is_active) == 0:
            return False
        if 'is_volunteer' in user.keys() and user['is_volunteer']:
            return True
        # Check linked volunteers table
        vol = conn.execute(
            "SELECT id, status FROM volunteers WHERE user_id = ?", (user_id,)
        ).fetchone()
        if vol and vol['status'] == 'ACTIVE':
            return True
        return False
    finally:
        close_db(conn)


def set_user_volunteer(db_path, user_id, is_volunteer=1):
    """
    Set or unset volunteer role for a user.
    """
    conn = get_db_connection(db_path)
    try:
        conn.execute(
            "UPDATE users SET is_volunteer = ? WHERE id = ?",
            (int(is_volunteer), user_id)
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return False
    finally:
        close_db(conn)




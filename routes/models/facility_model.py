"""
Facility Model — Database access layer for the 'facilities' table.

Provides CRUD operations for nearby facilities (medical camps,
food stalls, water points, toilets, rest shelters).
Uses raw SQL via sqlite3 (no ORM) as per architecture.

Table schema:
    id          INTEGER PK AUTOINCREMENT
    name        TEXT NOT NULL
    type        TEXT NOT NULL (medical, food, water, toilet, shelter)
    latitude    REAL NOT NULL
    longitude   REAL NOT NULL
    description TEXT
"""

from models.db import get_db_connection, close_db


def create_facility(db_path, name, facility_type, latitude, longitude, description=None):
    """
    Insert a new facility into the facilities table.

    Args:
        db_path: Path to the SQLite database file.
        name: Name of the facility.
        facility_type: Type — one of: medical, food, water, toilet, shelter.
        latitude: GPS latitude.
        longitude: GPS longitude.
        description: Optional description text.

    Returns:
        The ID of the newly created facility, or None on failure.
    """
    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute(
            """INSERT INTO facilities (name, type, latitude, longitude, description)
               VALUES (?, ?, ?, ?, ?)""",
            (name, facility_type, latitude, longitude, description)
        )
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        conn.rollback()
        print(f"Error creating facility: {e}")
        return None
    finally:
        close_db(conn)


def get_facility_by_id(db_path, facility_id):
    """
    Retrieve a single facility by its ID.

    Args:
        db_path: Path to the SQLite database file.
        facility_id: The facility's primary key ID.

    Returns:
        A sqlite3.Row object with facility data, or None if not found.
    """
    conn = get_db_connection(db_path)
    try:
        facility = conn.execute(
            "SELECT * FROM facilities WHERE id = ?", (facility_id,)
        ).fetchone()
        return facility
    finally:
        close_db(conn)


def get_all_facilities(db_path):
    """
    Retrieve all facilities.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        A list of sqlite3.Row objects.
    """
    conn = get_db_connection(db_path)
    try:
        facilities = conn.execute(
            "SELECT * FROM facilities ORDER BY type, name"
        ).fetchall()
        return facilities
    finally:
        close_db(conn)


def get_facilities_by_type(db_path, facility_type):
    """
    Retrieve all facilities of a specific type.

    Args:
        db_path: Path to the SQLite database file.
        facility_type: The type to filter by (medical, food, water, toilet, shelter).

    Returns:
        A list of sqlite3.Row objects matching the type.
    """
    conn = get_db_connection(db_path)
    try:
        facilities = conn.execute(
            "SELECT * FROM facilities WHERE type = ? ORDER BY name",
            (facility_type,)
        ).fetchall()
        return facilities
    finally:
        close_db(conn)


def update_facility(db_path, facility_id, name=None, facility_type=None,
                    latitude=None, longitude=None, description=None):
    """
    Update a facility's information.

    Only updates fields that are provided (not None).

    Args:
        db_path: Path to the SQLite database file.
        facility_id: The facility's primary key ID.
        name: Updated name (optional).
        facility_type: Updated type (optional).
        latitude: Updated latitude (optional).
        longitude: Updated longitude (optional).
        description: Updated description (optional).

    Returns:
        True if the update was successful, False otherwise.
    """
    fields = []
    values = []

    if name is not None:
        fields.append("name = ?")
        values.append(name)
    if facility_type is not None:
        fields.append("type = ?")
        values.append(facility_type)
    if latitude is not None:
        fields.append("latitude = ?")
        values.append(latitude)
    if longitude is not None:
        fields.append("longitude = ?")
        values.append(longitude)
    if description is not None:
        fields.append("description = ?")
        values.append(description)

    if not fields:
        return False  # Nothing to update

    values.append(facility_id)

    conn = get_db_connection(db_path)
    try:
        conn.execute(
            f"UPDATE facilities SET {', '.join(fields)} WHERE id = ?",
            tuple(values)
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error updating facility: {e}")
        return False
    finally:
        close_db(conn)


def delete_facility(db_path, facility_id):
    """
    Delete a facility by its ID.

    Args:
        db_path: Path to the SQLite database file.
        facility_id: The facility's primary key ID.

    Returns:
        True if deleted, False otherwise.
    """
    conn = get_db_connection(db_path)
    try:
        result = conn.execute(
            "DELETE FROM facilities WHERE id = ?", (facility_id,)
        )
        conn.commit()
        return result.rowcount > 0
    except Exception as e:
        conn.rollback()
        print(f"Error deleting facility: {e}")
        return False
    finally:
        close_db(conn)

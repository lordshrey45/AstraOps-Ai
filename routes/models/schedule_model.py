"""
Schedule Model — Database access layer for 'daily_schedule' and 'route_points' tables.

Provides CRUD operations for the day-wise Wari itinerary and
ordered route polyline points for the Dindi procession.
Uses raw SQL via sqlite3 (no ORM) as per architecture.

daily_schedule schema:
    id          INTEGER PK AUTOINCREMENT
    day_number  INTEGER NOT NULL
    date        DATE
    halt_village TEXT NOT NULL
    distance_km REAL
    start_time  TEXT
    end_time    TEXT
    notes       TEXT

route_points schema:
    id          INTEGER PK AUTOINCREMENT
    day_number  INTEGER NOT NULL
    latitude    REAL NOT NULL
    longitude   REAL NOT NULL
    sequence    INTEGER NOT NULL (order along the route)

Relationship: daily_schedule 1—N route_points (via day_number)
"""

from models.db import get_db_connection, close_db


# ============================================================
# Daily Schedule CRUD
# ============================================================

def create_schedule_entry(db_path, day_number, halt_village, date=None,
                          distance_km=None, start_time=None, end_time=None, notes=None):
    """
    Insert a new daily schedule entry.

    Args:
        db_path: Path to the SQLite database file.
        day_number: Day number in the Wari (Day 1, Day 2, ...).
        halt_village: Name of the overnight halt village.
        date: Date for this day (optional).
        distance_km: Distance covered in km (optional).
        start_time: Start time string (optional).
        end_time: End time string (optional).
        notes: Additional notes (optional).

    Returns:
        The ID of the newly created entry, or None on failure.
    """
    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute(
            """INSERT INTO daily_schedule
               (day_number, date, halt_village, distance_km, start_time, end_time, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (day_number, date, halt_village, distance_km, start_time, end_time, notes)
        )
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        conn.rollback()
        print(f"Error creating schedule entry: {e}")
        return None
    finally:
        close_db(conn)


def get_full_schedule(db_path):
    """
    Retrieve the complete daily schedule, ordered by day number.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        A list of sqlite3.Row objects representing each day.
    """
    conn = get_db_connection(db_path)
    try:
        schedule = conn.execute(
            "SELECT * FROM daily_schedule ORDER BY day_number"
        ).fetchall()
        return schedule
    finally:
        close_db(conn)


def get_schedule_by_day(db_path, day_number):
    """
    Retrieve schedule details for a specific day.

    Args:
        db_path: Path to the SQLite database file.
        day_number: The day number to query.

    Returns:
        A sqlite3.Row object for that day, or None if not found.
    """
    conn = get_db_connection(db_path)
    try:
        entry = conn.execute(
            "SELECT * FROM daily_schedule WHERE day_number = ?", (day_number,)
        ).fetchone()
        return entry
    finally:
        close_db(conn)


def get_schedule_by_date(db_path, date):
    """
    Retrieve schedule entry for a specific date.

    Args:
        db_path: Path to the SQLite database file.
        date: The date string (YYYY-MM-DD format).

    Returns:
        A sqlite3.Row object for that date, or None if not found.
    """
    conn = get_db_connection(db_path)
    try:
        entry = conn.execute(
            "SELECT * FROM daily_schedule WHERE date = ?", (date,)
        ).fetchone()
        return entry
    finally:
        close_db(conn)


def update_schedule_entry(db_path, day_number, halt_village=None, date=None,
                          distance_km=None, start_time=None, end_time=None, notes=None):
    """
    Update a daily schedule entry by day number.

    Only updates fields that are provided (not None).

    Args:
        db_path: Path to the SQLite database file.
        day_number: The day number to update.
        halt_village: Updated halt village (optional).
        date: Updated date (optional).
        distance_km: Updated distance (optional).
        start_time: Updated start time (optional).
        end_time: Updated end time (optional).
        notes: Updated notes (optional).

    Returns:
        True if successful, False otherwise.
    """
    fields = []
    values = []

    if halt_village is not None:
        fields.append("halt_village = ?")
        values.append(halt_village)
    if date is not None:
        fields.append("date = ?")
        values.append(date)
    if distance_km is not None:
        fields.append("distance_km = ?")
        values.append(distance_km)
    if start_time is not None:
        fields.append("start_time = ?")
        values.append(start_time)
    if end_time is not None:
        fields.append("end_time = ?")
        values.append(end_time)
    if notes is not None:
        fields.append("notes = ?")
        values.append(notes)

    if not fields:
        return False  # Nothing to update

    values.append(day_number)

    conn = get_db_connection(db_path)
    try:
        conn.execute(
            f"UPDATE daily_schedule SET {', '.join(fields)} WHERE day_number = ?",
            tuple(values)
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error updating schedule: {e}")
        return False
    finally:
        close_db(conn)


def delete_schedule_entry(db_path, day_number):
    """
    Delete a schedule entry by day number.

    Args:
        db_path: Path to the SQLite database file.
        day_number: The day number to delete.

    Returns:
        True if deleted, False otherwise.
    """
    conn = get_db_connection(db_path)
    try:
        result = conn.execute(
            "DELETE FROM daily_schedule WHERE day_number = ?", (day_number,)
        )
        conn.commit()
        return result.rowcount > 0
    except Exception as e:
        conn.rollback()
        print(f"Error deleting schedule entry: {e}")
        return False
    finally:
        close_db(conn)


# ============================================================
# Route Points CRUD
# ============================================================

def create_route_point(db_path, day_number, latitude, longitude, sequence):
    """
    Insert a single route point for the Dindi procession path.

    Args:
        db_path: Path to the SQLite database file.
        day_number: The day this point belongs to.
        latitude: GPS latitude.
        longitude: GPS longitude.
        sequence: Order along the route (for polyline rendering).

    Returns:
        The ID of the newly created point, or None on failure.
    """
    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute(
            """INSERT INTO route_points (day_number, latitude, longitude, sequence)
               VALUES (?, ?, ?, ?)""",
            (day_number, latitude, longitude, sequence)
        )
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        conn.rollback()
        print(f"Error creating route point: {e}")
        return None
    finally:
        close_db(conn)


def create_route_points_bulk(db_path, points):
    """
    Insert multiple route points in a single transaction.
    Useful for seeding route data efficiently.

    Args:
        db_path: Path to the SQLite database file.
        points: A list of tuples (day_number, latitude, longitude, sequence).

    Returns:
        True if all points were inserted, False on failure.
    """
    conn = get_db_connection(db_path)
    try:
        conn.executemany(
            """INSERT INTO route_points (day_number, latitude, longitude, sequence)
               VALUES (?, ?, ?, ?)""",
            points
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error bulk-inserting route points: {e}")
        return False
    finally:
        close_db(conn)


def get_all_route_points(db_path):
    """
    Retrieve all route points, ordered by day number and sequence.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        A list of sqlite3.Row objects.
    """
    conn = get_db_connection(db_path)
    try:
        points = conn.execute(
            "SELECT * FROM route_points ORDER BY day_number, sequence"
        ).fetchall()
        return points
    finally:
        close_db(conn)


def get_route_points_by_day(db_path, day_number):
    """
    Retrieve route points for a specific day, ordered by sequence.
    Used by map.js to draw the polyline for a single day.

    Args:
        db_path: Path to the SQLite database file.
        day_number: The day number to query.

    Returns:
        A list of sqlite3.Row objects for that day's route.
    """
    conn = get_db_connection(db_path)
    try:
        points = conn.execute(
            "SELECT * FROM route_points WHERE day_number = ? ORDER BY sequence",
            (day_number,)
        ).fetchall()
        return points
    finally:
        close_db(conn)


def delete_route_points_by_day(db_path, day_number):
    """
    Delete all route points for a specific day.
    Useful when re-seeding route data for a day.

    Args:
        db_path: Path to the SQLite database file.
        day_number: The day number whose points to delete.

    Returns:
        The number of rows deleted.
    """
    conn = get_db_connection(db_path)
    try:
        result = conn.execute(
            "DELETE FROM route_points WHERE day_number = ?", (day_number,)
        )
        conn.commit()
        return result.rowcount
    except Exception as e:
        conn.rollback()
        print(f"Error deleting route points: {e}")
        return 0
    finally:
        close_db(conn)

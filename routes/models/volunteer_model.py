"""
Volunteer Model — Database helper functions for Volunteer tracking, discovery, availability, and safety management (Phases 33, 34, 36).

Supports:
- Volunteer CRUD operations
- Volunteer location updating & location history recording
- Volunteer availability toggling (AVAILABLE / OFF DUTY)
- Explicit location sharing toggling (START / STOP sharing)
- Great-circle geographic distance calculations (Haversine formula)
- Location freshness calculations (LIVE <=60s, RECENT 61-300s, STALE >300s, OFFLINE)
- Nearby volunteer discovery & ranked operational recommendations
- Volunteer incident assignment
"""

import math
from datetime import datetime, timezone
from models.db import get_db_connection, close_db


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance in kilometers between two points
    on the earth (specified in decimal degrees).
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return float('inf')
    try:
        lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2.0) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2)
        c = 2.0 * math.asin(math.sqrt(a))
        r = 6371.0  # Radius of earth in kilometers
        return round(c * r, 2)
    except Exception:
        return float('inf')


def create_volunteer(db_path, name, phone, user_id=None, status='ACTIVE', availability='AVAILABLE', is_sharing=0, latitude=None, longitude=None, accuracy=None):
    """
    Create a new volunteer record in the database.
    Returns the ID of the created volunteer, or None on error.
    """
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO volunteers (name, phone, user_id, status, availability, is_sharing, latitude, longitude, accuracy, location_updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CASE WHEN ? IS NOT NULL THEN CURRENT_TIMESTAMP ELSE NULL END)""",
            (name, phone, user_id, status, availability, int(is_sharing), latitude, longitude, accuracy, latitude)
        )
        conn.commit()
        vol_id = cur.lastrowid
        return vol_id
    except Exception as e:
        conn.rollback()
        return None
    finally:
        close_db(conn)


def get_volunteer_by_id(db_path, volunteer_id):
    """Retrieve a single volunteer by ID."""
    conn = get_db_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM volunteers WHERE id = ?",
            (volunteer_id,)
        ).fetchone()
        return row
    finally:
        close_db(conn)


def get_volunteer_by_user_id(db_path, user_id):
    """Retrieve a volunteer by the linked user_id."""
    if user_id is None:
        return None
    conn = get_db_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM volunteers WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        return row
    finally:
        close_db(conn)


def get_volunteer_by_phone(db_path, phone):
    """Retrieve a volunteer by their unique phone number."""
    conn = get_db_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM volunteers WHERE phone = ?",
            (phone,)
        ).fetchone()
        return row
    finally:
        close_db(conn)


def get_all_volunteers(db_path):
    """Retrieve all volunteers ordered by id."""
    conn = get_db_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM volunteers ORDER BY id ASC"
        ).fetchall()
        return rows
    finally:
        close_db(conn)


def update_volunteer_location(db_path, user_id, latitude, longitude, accuracy=None, is_sharing=1):
    """
    Update the latitude, longitude, accuracy, and location_updated_at for a volunteer linked to user_id.
    Also records the update in the volunteer_locations history table.
    Returns True on success, False otherwise.
    """
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE volunteers 
               SET latitude = ?, longitude = ?, accuracy = ?, is_sharing = ?, location_updated_at = CURRENT_TIMESTAMP
               WHERE user_id = ? AND status = 'ACTIVE'""",
            (latitude, longitude, accuracy, int(is_sharing), user_id)
        )
        if cur.rowcount > 0:
            # Record location history
            try:
                cur.execute(
                    """INSERT INTO volunteer_locations (volunteer_user_id, latitude, longitude, accuracy)
                       VALUES (?, ?, ?, ?)""",
                    (user_id, latitude, longitude, accuracy)
                )
            except Exception:
                pass
            conn.commit()
            return True
        conn.rollback()
        return False
    except Exception as e:
        conn.rollback()
        return False
    finally:
        close_db(conn)



def set_volunteer_status(db_path, volunteer_id, status):
    """
    Set volunteer operational status ('ACTIVE' or 'INACTIVE').
    Returns True on success, False otherwise.
    """
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE volunteers SET status = ? WHERE id = ?",
            (status, volunteer_id)
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        conn.rollback()
        return False
    finally:
        close_db(conn)


def set_volunteer_availability(db_path, user_id, availability):
    """
    Set volunteer availability ('AVAILABLE', 'BUSY', or 'OFF DUTY').
    When set to AVAILABLE, enables sharing and updates presence timestamp.
    When set to OFF DUTY, disables sharing.
    """
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()
        if availability == 'AVAILABLE':
            cur.execute(
                "UPDATE volunteers SET availability = ?, is_sharing = 1, location_updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (availability, user_id)
            )
        elif availability == 'OFF DUTY':
            cur.execute(
                "UPDATE volunteers SET availability = ?, is_sharing = 0 WHERE user_id = ?",
                (availability, user_id)
            )
        else:
            cur.execute(
                "UPDATE volunteers SET availability = ? WHERE user_id = ?",
                (availability, user_id)
            )
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        conn.rollback()
        return False
    finally:
        close_db(conn)


def set_volunteer_sharing(db_path, user_id, is_sharing=1):
    """
    Update explicit location sharing state (1 for sharing, 0 for stopped).
    Returns True on success, False otherwise.
    """
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE volunteers SET is_sharing = ? WHERE user_id = ?",
            (int(is_sharing), user_id)
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        conn.rollback()
        return False
    finally:
        close_db(conn)


def format_last_seen(location_updated_at):
    """
    Format a human-readable 'Last seen' or 'Last update' string for offline and online presence.
    e.g., '5 seconds ago', '8 minutes ago', '2 hours ago', 'Never'.
    """
    if not location_updated_at:
        return 'Never'
    try:
        if isinstance(location_updated_at, str):
            updated_dt = datetime.strptime(location_updated_at.split('.')[0], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        elif isinstance(location_updated_at, datetime):
            updated_dt = location_updated_at if location_updated_at.tzinfo else location_updated_at.replace(tzinfo=timezone.utc)
        else:
            return str(location_updated_at)

        now_utc = datetime.now(timezone.utc)
        delta_sec = int((now_utc - updated_dt).total_seconds())
        if delta_sec < 0:
            delta_sec = 0

        if delta_sec < 60:
            return f"{delta_sec} seconds ago" if delta_sec > 1 else "just now"
        elif delta_sec < 3600:
            mins = delta_sec // 60
            return f"{mins} minute ago" if mins == 1 else f"{mins} minutes ago"
        elif delta_sec < 86400:
            hrs = delta_sec // 3600
            return f"{hrs} hour ago" if hrs == 1 else f"{hrs} hours ago"
        else:
            days = delta_sec // 86400
            return f"{days} day ago" if days == 1 else f"{days} days ago"
    except Exception:
        return str(location_updated_at)


def is_volunteer_online(vol_dict_or_row):
    """
    Determine if a volunteer is currently ONLINE and contactable.
    Rules:
    - status must be 'ACTIVE'
    - is_sharing must be 1 (enabled)
    - availability must not be 'OFF DUTY'
    - location_updated_at must exist and delta <= 300 seconds (5 min stale threshold)
    """
    if not vol_dict_or_row:
        return False
    
    d = dict(vol_dict_or_row)
    if d.get('status') != 'ACTIVE':
        return False
    
    if d.get('is_sharing', 1) == 0:
        return False
    
    if d.get('availability') == 'OFF DUTY':
        return False
    
    loc_time = d.get('location_updated_at')
    if not loc_time:
        return False
    
    freshness, delta = calculate_freshness(loc_time, d.get('status', 'ACTIVE'))
    # Stale (> 300s) or OFFLINE means offline
    return bool(freshness in ('LIVE', 'RECENT'))


def calculate_freshness(location_updated_at, status='ACTIVE'):
    """
    Calculate location freshness given a timestamp and status:
    - If status == 'INACTIVE' or location_updated_at is None: ('OFFLINE', None)
    - If delta <= 60 seconds: ('LIVE', delta_seconds)
    - If 61 <= delta <= 300 seconds: ('RECENT', delta_seconds)
    - If delta > 300 seconds: ('STALE', delta_seconds)
    """
    if status != 'ACTIVE' or not location_updated_at:
        return 'OFFLINE', None

    try:
        if isinstance(location_updated_at, str):
            updated_dt = datetime.strptime(location_updated_at.split('.')[0], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        elif isinstance(location_updated_at, datetime):
            updated_dt = location_updated_at if location_updated_at.tzinfo else location_updated_at.replace(tzinfo=timezone.utc)
        else:
            return 'OFFLINE', None

        now_utc = datetime.now(timezone.utc)
        delta_seconds = int((now_utc - updated_dt).total_seconds())

        if delta_seconds < 0:
            delta_seconds = 0

        if delta_seconds <= 60:
            return 'LIVE', delta_seconds
        elif delta_seconds <= 300:
            return 'RECENT', delta_seconds
        else:
            return 'STALE', delta_seconds
    except Exception:
        return 'OFFLINE', None



def find_nearby_volunteers(db_path, sos_lat, sos_lon, max_distance_km=25.0):
    """
    Discover and rank nearby active volunteers for an emergency SOS incident.

    Ranking Strategy:
    1. Operational availability / freshness: LIVE (1) -> RECENT (2) -> STALE (3)
    2. Approximate geographic distance (ascending in km)
    3. Active status check (INACTIVE and OFFLINE volunteers excluded from top recommendation)

    Returns a list of dictionaries with volunteer details, distance_km, freshness, and is_recommended.
    """
    if sos_lat is None or sos_lon is None:
        return []

    all_vols = get_all_volunteers(db_path)
    ranked = []

    freshness_rank = {'LIVE': 1, 'RECENT': 2, 'STALE': 3, 'OFFLINE': 4}

    for v in all_vols:
        if v['status'] != 'ACTIVE' or v['latitude'] is None or v['longitude'] is None:
            continue

        freshness, delta = calculate_freshness(v['location_updated_at'], v['status'])
        dist = haversine_distance(sos_lat, sos_lon, v['latitude'], v['longitude'])

        if dist > max_distance_km:
            continue

        is_recommended = bool(freshness in ('LIVE', 'RECENT'))
        avail = v['availability'] if ('availability' in v.keys() and v['availability']) else 'AVAILABLE'

        ranked.append({
            'id': v['id'],
            'name': v['name'],
            'phone': v['phone'],
            'status': v['status'],
            'availability': avail,
            'is_sharing': v['is_sharing'] if 'is_sharing' in v.keys() else 0,
            'latitude': float(v['latitude']),
            'longitude': float(v['longitude']),
            'distance_km': dist,
            'freshness': freshness,
            'delta_seconds': delta,
            'is_recommended': is_recommended,
            'location_updated_at': str(v['location_updated_at']) if v['location_updated_at'] else 'Never'
        })

    # Sort: freshness rank first, then distance
    ranked.sort(key=lambda x: (freshness_rank.get(x['freshness'], 4), x['distance_km']))
    return ranked


def assign_volunteer_to_sos(db_path, sos_id, volunteer_id):
    """
    Assign a designated volunteer to assist with an SOS emergency incident.
    Updates status to 'assigned', dispatch_status to 'ASSIGNED', and sets assigned_at.
    """
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE sos_requests 
               SET assigned_volunteer_id = ?, status = 'assigned', dispatch_status = 'ASSIGNED', assigned_at = CURRENT_TIMESTAMP
               WHERE id = ? AND status != 'resolved'""",
            (volunteer_id, sos_id)
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        conn.rollback()
        return False
    finally:
        close_db(conn)

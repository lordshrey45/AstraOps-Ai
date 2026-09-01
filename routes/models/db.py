"""
Database connection helper for Wari Mitra.
Provides functions to get a database connection and initialize the schema.
"""

import sqlite3
import os


def get_db_connection(db_path):
    """
    Create and return a database connection with row factory set to sqlite3.Row
    for dictionary-like access to columns.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key support
    return conn


def init_db(db_path):
    """
    Initialize the database by executing the schema.sql script.
    Creates the database file and all tables if they don't exist.
    """
    # Ensure the database directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)

    conn = get_db_connection(db_path)
    
    # Read and execute the schema file
    schema_path = os.path.join(os.path.dirname(db_path), 'schema.sql')
    # Ensure is_admin column exists for users table
    try:
        conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass

    # Ensure is_active column exists for users table
    try:
        conn.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
        conn.commit()
    except Exception:
        pass


    # Ensure is_volunteer column exists for users table
    try:
        conn.execute("ALTER TABLE users ADD COLUMN is_volunteer INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass

    # Ensure admin_activity_log table exists
    try:
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
    except Exception:
        pass

    # Ensure volunteers table exists (Phase 34 & 36)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS volunteers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                name TEXT NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'ACTIVE',
                availability TEXT DEFAULT 'AVAILABLE',
                is_sharing INTEGER DEFAULT 0,
                latitude REAL,
                longitude REAL,
                location_updated_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.commit()
    except Exception:
        pass

    try:
        conn.execute("ALTER TABLE volunteers ADD COLUMN availability TEXT DEFAULT 'AVAILABLE'")
        conn.commit()
    except Exception:
        pass

    try:
        conn.execute("ALTER TABLE volunteers ADD COLUMN is_sharing INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass

    try:
        conn.execute("ALTER TABLE volunteers ADD COLUMN accuracy REAL")
        conn.commit()
    except Exception:
        pass

    # Ensure volunteer_locations table exists (Phase 33 & Phase 2)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS volunteer_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                volunteer_user_id INTEGER NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                accuracy REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (volunteer_user_id) REFERENCES users(id)
            )
        """)
        conn.commit()
    except Exception:
        pass

    try:
        conn.execute("ALTER TABLE volunteer_locations ADD COLUMN accuracy REAL")
        conn.commit()
    except Exception:
        pass


    # Ensure assigned_volunteer_id column exists for sos_requests table (Phase 36)
    try:
        conn.execute("ALTER TABLE sos_requests ADD COLUMN assigned_volunteer_id INTEGER REFERENCES volunteers(id)")
        conn.commit()
    except Exception:
        pass

    # Ensure Phase 3 SOS Queue & Dispatch columns exist
    for col_def in [
        "ALTER TABLE sos_requests ADD COLUMN priority TEXT DEFAULT 'MEDIUM'",
        "ALTER TABLE sos_requests ADD COLUMN priority_reason TEXT",
        "ALTER TABLE sos_requests ADD COLUMN dispatch_status TEXT DEFAULT 'UNASSIGNED'",
        "ALTER TABLE sos_requests ADD COLUMN assigned_at TIMESTAMP",
        "ALTER TABLE sos_requests ADD COLUMN acknowledged_at TIMESTAMP",
        "ALTER TABLE sos_requests ADD COLUMN resolved_at TIMESTAMP",
        "ALTER TABLE sos_requests ADD COLUMN resolved_by INTEGER",
        "ALTER TABLE sos_requests ADD COLUMN resolution_notes TEXT"
    ]:
        try:
            conn.execute(col_def)
            conn.commit()
        except Exception:
            pass


    # Ensure volunteer_requests table exists
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS volunteer_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                status TEXT DEFAULT 'PENDING',
                location_area TEXT,
                experience_notes TEXT,
                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                reviewed_by INTEGER,
                rejection_reason TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (reviewed_by) REFERENCES users(id)
            )
        """)
        conn.commit()
    except Exception:
        pass

    # Ensure volunteer_assignments table exists (Phase 33)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS volunteer_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sos_id INTEGER NOT NULL,
                volunteer_id INTEGER NOT NULL,
                assigned_by_admin_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'assigned',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sos_id) REFERENCES sos_requests(id),
                FOREIGN KEY (volunteer_id) REFERENCES volunteers(id),
                FOREIGN KEY (assigned_by_admin_id) REFERENCES users(id)
            )
        """)
        conn.commit()
    except Exception:
        pass

    conn.close()

    print(f"Database initialized at {db_path}")


def close_db(conn):
    """Close the database connection if it exists."""
    if conn is not None:
        conn.close()


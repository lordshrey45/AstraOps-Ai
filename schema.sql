-- Wari Mitra Database Schema
-- SQLite database for the Wari pilgrimage assistance platform

-- Users table: registered pilgrims, volunteers, and admins
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    emergency_contact TEXT,
    medical_info TEXT,
    is_admin INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    is_volunteer INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Volunteers table (Phase 34 & 36): field volunteer registry and location tracking
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
    accuracy REAL,
    location_updated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Volunteer Locations table (Phase 33): location history and tracking records
CREATE TABLE IF NOT EXISTS volunteer_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    volunteer_user_id INTEGER NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    accuracy REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (volunteer_user_id) REFERENCES users(id)
);


-- Volunteer Requests table: volunteer registration applications and admin approval workflow
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
);


-- SOS Requests table: emergency requests from pilgrims (Phase 3 Multi-Emergency Queue & Dispatch)
CREATE TABLE IF NOT EXISTS sos_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    latitude REAL,
    longitude REAL,
    message TEXT,
    status TEXT DEFAULT 'pending',
    priority TEXT DEFAULT 'MEDIUM',
    priority_reason TEXT,
    dispatch_status TEXT DEFAULT 'UNASSIGNED',
    assigned_volunteer_id INTEGER,
    assigned_at TIMESTAMP,
    acknowledged_at TIMESTAMP,
    resolved_at TIMESTAMP,
    resolved_by INTEGER,
    resolution_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (assigned_volunteer_id) REFERENCES volunteers(id)
);

-- Volunteer Assignments table (Phase 33): emergency dispatch and response tracking
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
);

CREATE TABLE IF NOT EXISTS facilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    description TEXT
);

-- Route Points table: ordered polyline points for the Dindi route
CREATE TABLE IF NOT EXISTS route_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day_number INTEGER NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    sequence INTEGER NOT NULL
);

-- Daily Schedule table: day-wise itinerary of the Wari
CREATE TABLE IF NOT EXISTS daily_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day_number INTEGER NOT NULL,
    date DATE,
    halt_village TEXT NOT NULL,
    distance_km REAL,
    start_time TEXT,
    end_time TEXT,
    notes TEXT
);

-- Chat History table: stores user-AI conversation logs
CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    message TEXT NOT NULL,
    response TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Admin Activity Log table: stores audit history of administrative operations
CREATE TABLE IF NOT EXISTS admin_activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_user_id INTEGER,
    action_type TEXT NOT NULL,
    description TEXT NOT NULL,
    entity_type TEXT,
    entity_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_user_id) REFERENCES users(id)
);

-- Volunteers table: stores volunteer tracking and safety information (Phase 34)
CREATE TABLE IF NOT EXISTS volunteers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,
    name TEXT NOT NULL,
    phone TEXT UNIQUE NOT NULL,
    status TEXT DEFAULT 'ACTIVE',
    latitude REAL,
    longitude REAL,
    location_updated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);






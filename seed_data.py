"""
Seed Demo Data — Populates route_points and daily_schedule tables
with PLACEHOLDER data for the Wari route map demo.

IMPORTANT: These coordinates are APPROXIMATE demo data only.
They are NOT official Wari route coordinates.
Replace with verified GPS data when available.

Usage:
    python seed_data.py

This script is idempotent — it clears existing demo data before inserting.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.db import get_db_connection, close_db, init_db
from config import Config

# ============================================================
# DEMO ROUTE POINTS — Approximate path from Dehu to Pandharpur
# These are PLACEHOLDER coordinates for demo/development.
# Replace with verified GPS waypoints when available.
# ============================================================

DEMO_ROUTE_POINTS = [
    # (day_number, latitude, longitude, sequence)
    # Day 1: Dehu -> Loni Kalbhor
    (1, 18.7167, 73.7669, 1),   # Dehu (Start)
    (1, 18.6850, 73.8200, 2),   # Loni Kalbhor (Day 1 halt)

    # Day 2: Loni Kalbhor -> Jejuri
    (2, 18.6500, 73.8600, 3),   # En route
    (2, 18.2800, 74.1600, 4),   # Jejuri

    # Day 3: Jejuri -> Walhe
    (3, 18.2200, 74.1800, 5),   # En route
    (3, 18.1500, 74.2500, 6),   # Walhe

    # Day 4: Walhe -> Lonand
    (4, 18.1000, 74.3200, 7),   # En route
    (4, 18.0400, 74.4600, 8),   # Lonand

    # Day 5: Lonand -> Taradgaon
    (5, 17.9800, 74.4900, 9),   # En route
    (5, 17.9200, 74.5500, 10),  # Taradgaon

    # Day 6: Taradgaon -> Phaltan
    (6, 17.8800, 74.5800, 11),  # En route
    (6, 17.9900, 74.4300, 12),  # Phaltan

    # Day 7: Phaltan -> Baramati Road
    (7, 17.9500, 74.5000, 13),  # En route
    (7, 17.8800, 74.6500, 14),  # Baramati Road area

    # Day 8: -> Natepute
    (8, 17.8200, 74.7200, 15),  # En route
    (8, 17.7500, 74.8500, 16),  # Natepute

    # Day 9: -> Malshiras
    (9, 17.7000, 74.9000, 17),  # En route
    (9, 17.6300, 75.0200, 18),  # Malshiras

    # Day 10: -> Velapur
    (10, 17.6000, 75.0800, 19), # En route
    (10, 17.5500, 75.1500, 20), # Velapur

    # Day 11: -> Bhandishegaon
    (11, 17.5000, 75.2000, 21), # En route
    (11, 17.4500, 75.2600, 22), # Bhandishegaon

    # Day 12: -> Wakhari
    (12, 17.4200, 75.2900, 23), # En route
    (12, 17.4000, 75.3200, 24), # Wakhari

    # Day 13: -> Pandharpur (Destination)
    (13, 17.3800, 75.3400, 25), # En route
    (13, 17.6800, 75.3300, 26), # Pandharpur (Destination)
]

# ============================================================
# DEMO DAILY SCHEDULE
# ============================================================

DEMO_SCHEDULE = [
    # (day_number, date, halt_village, distance_km, start_time, end_time, notes)
    (1,  '2026-06-20', 'Loni Kalbhor',  22.0, '05:00', '18:00', 'Departure from Dehu. Sant Tukaram Palkhi starts.'),
    (2,  '2026-06-21', 'Jejuri',         35.0, '05:00', '17:00', 'Famous Khandoba temple en route.'),
    (3,  '2026-06-22', 'Walhe',          18.0, '05:30', '16:00', 'Scenic village halt.'),
    (4,  '2026-06-23', 'Lonand',         25.0, '05:00', '17:00', 'Cross into Satara district.'),
    (5,  '2026-06-24', 'Taradgaon',      20.0, '05:00', '16:30', 'Rest day preparations.'),
    (6,  '2026-06-25', 'Phaltan',        28.0, '05:00', '17:30', 'Historic town with markets.'),
    (7,  '2026-06-26', 'Baramati Road',  24.0, '05:30', '17:00', 'Major road junction area.'),
    (8,  '2026-06-27', 'Natepute',       22.0, '05:00', '16:00', 'Small village halt.'),
    (9,  '2026-06-28', 'Malshiras',      30.0, '05:00', '18:00', 'Enter Solapur district.'),
    (10, '2026-06-29', 'Velapur',        18.0, '05:30', '16:00', 'Approaching Pandharpur.'),
    (11, '2026-06-30', 'Bhandishegaon',  15.0, '05:00', '15:00', 'Short walk day.'),
    (12, '2026-07-01', 'Wakhari',        12.0, '05:00', '14:00', 'Penultimate halt.'),
    (13, '2026-07-02', 'Pandharpur',     20.0, '04:00', '12:00', 'Arrival at Lord Vitthal Temple! Ashadi Ekadashi.'),
]

# ============================================================
# DEMO FACILITIES — Approximate locations near Wari route
# All facilities are DEMO/PLACEHOLDER data.
# DO NOT claim these are real facilities.
# ============================================================

DEMO_FACILITIES = [
    # (name, type, latitude, longitude, description)
    # Medical
    ('Demo Medical Camp - Dehu',        'medical',   18.7200, 73.7700, 'DEMO: 24-hour medical camp near starting point.'),
    ('Demo Hospital - Jejuri',          'medical',   18.2850, 74.1650, 'DEMO: Primary health center with first aid.'),
    ('Demo Medical Camp - Pandharpur',  'medical',   17.6850, 75.3350, 'DEMO: Main medical facility at destination.'),

    # Water
    ('Demo Water Point - Loni Kalbhor', 'water',     18.6880, 73.8250, 'DEMO: Clean drinking water station.'),
    ('Demo Water Point - Lonand',       'water',     18.0450, 74.4650, 'DEMO: Bore-well water point.'),
    ('Demo Water Point - Velapur',      'water',     17.5550, 75.1550, 'DEMO: Water tanker station.'),

    # Toilet
    ('Demo Toilet Block - Walhe',       'toilet',    18.1550, 74.2550, 'DEMO: Portable toilet facility.'),
    ('Demo Toilet Block - Phaltan',     'toilet',    17.9950, 74.4350, 'DEMO: Permanent toilet block.'),
    ('Demo Toilet Block - Malshiras',   'toilet',    17.6350, 75.0250, 'DEMO: Sanitation facility.'),

    # Food
    ('Demo Anna Chhatra - Dehu',        'food',      18.7150, 73.7650, 'DEMO: Free food distribution (Anna Chhatra).'),
    ('Demo Food Stall - Taradgaon',     'food',      17.9250, 74.5550, 'DEMO: Veg meals and snacks available.'),
    ('Demo Anna Chhatra - Pandharpur',  'food',      17.6800, 75.3280, 'DEMO: Large free food camp near temple.'),

    # Shelter
    ('Demo Rest Shelter - Jejuri',      'shelter',   18.2780, 74.1600, 'DEMO: Covered rest area for pilgrims.'),
    ('Demo Dharamshala - Natepute',     'shelter',   17.7550, 74.8550, 'DEMO: Overnight shelter with basic amenities.'),
    ('Demo Rest Area - Wakhari',        'shelter',   17.4050, 75.3250, 'DEMO: Community hall for pilgrim rest.'),

    # Emergency
    ('Demo Emergency Camp - Lonand',    'emergency', 18.0380, 74.4580, 'DEMO: Emergency medical response team.'),
    ('Demo Ambulance Point - Phaltan',  'emergency', 17.9880, 74.4280, 'DEMO: Ambulance service point.'),
    ('Demo Emergency Camp - Pandharpur','emergency', 17.6780, 75.3250, 'DEMO: Central emergency response center.'),
]


def seed_data():
    """Seed the database with demo route, schedule, and facility data."""
    db_path = Config.DATABASE

    # Ensure DB is initialized
    init_db(db_path)

    conn = get_db_connection(db_path)

    try:
        # Clear existing demo data
        conn.execute("DELETE FROM route_points")
        conn.execute("DELETE FROM daily_schedule")
        conn.execute("DELETE FROM facilities")
        print("[*] Cleared existing route_points, daily_schedule, and facilities data.")

        # Insert route points
        conn.executemany(
            """INSERT INTO route_points (day_number, latitude, longitude, sequence)
               VALUES (?, ?, ?, ?)""",
            DEMO_ROUTE_POINTS
        )
        print(f"[+] Inserted {len(DEMO_ROUTE_POINTS)} demo route points.")

        # Insert daily schedule
        conn.executemany(
            """INSERT INTO daily_schedule
               (day_number, date, halt_village, distance_km, start_time, end_time, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            DEMO_SCHEDULE
        )
        print(f"[+] Inserted {len(DEMO_SCHEDULE)} daily schedule entries.")

        # Insert facilities
        conn.executemany(
            """INSERT INTO facilities (name, type, latitude, longitude, description)
               VALUES (?, ?, ?, ?, ?)""",
            DEMO_FACILITIES
        )
        print(f"[+] Inserted {len(DEMO_FACILITIES)} demo facilities.")

        # Seed demo Admin user if not exists
        from werkzeug.security import generate_password_hash
        admin_phone = '5555555555'
        admin_user = conn.execute("SELECT id FROM users WHERE phone = ?", (admin_phone,)).fetchone()
        if not admin_user:
            conn.execute(
                """INSERT INTO users (name, phone, password_hash, emergency_contact, medical_info, is_admin, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, 1)""",
                ('Wari Admin', admin_phone, generate_password_hash('shreyash0745'), '5555555555', 'Admin Account', 1)
            )
            print("[+] Seeded demo Admin user (phone: 5555555555).")

        conn.commit()




        print("\n[OK] Demo data seeded successfully!")
        print("[!] NOTE: All data is APPROXIMATE DEMO DATA.")
        print("    Replace with verified data when available.")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Failed to seed data: {e}")
    finally:
        close_db(conn)


if __name__ == '__main__':
    seed_data()


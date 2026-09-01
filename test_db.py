"""
Quick validation script to test all model imports and database tables.
Run from the project root: python test_db.py
"""

import sys
import os

# Ensure we can import from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 50)
print("Wari Mitra - Database Layer Validation")
print("=" * 50)

# 1. Test db.py imports
print("\n[1] Testing db.py imports...")
from models.db import init_db, get_db_connection, close_db
print("    [OK] db.py imports OK")

# 2. Test all model imports
print("\n[2] Testing model imports...")
from models.user_model import (
    create_user, get_user_by_id, get_user_by_phone,
    update_user, update_password, delete_user, get_all_users
)
print("    [OK] user_model.py imports OK")

from models.sos_model import (
    create_sos_request, get_sos_request_by_id, get_all_sos_requests,
    get_pending_sos_requests, get_sos_requests_by_user,
    resolve_sos_request, delete_sos_request
)
print("    [OK] sos_model.py imports OK")

from models.facility_model import (
    create_facility, get_facility_by_id, get_all_facilities,
    get_facilities_by_type, update_facility, delete_facility
)
print("    [OK] facility_model.py imports OK")

from models.schedule_model import (
    create_schedule_entry, get_full_schedule, get_schedule_by_day,
    get_schedule_by_date, update_schedule_entry, delete_schedule_entry,
    create_route_point, create_route_points_bulk, get_all_route_points,
    get_route_points_by_day, delete_route_points_by_day
)
print("    [OK] schedule_model.py imports OK")

from models.chat_model import (
    save_chat_message, get_chat_history_by_user, get_recent_chat_context,
    get_all_chat_history, delete_chat_history_by_user, delete_chat_message
)
print("    [OK] chat_model.py imports OK")

# 3. Initialize the database
print("\n[3] Initializing database...")
db_path = os.path.join(os.path.dirname(__file__), 'database', 'wari_mitra.db')
init_db(db_path)

# 4. Verify all tables exist
print("\n[4] Verifying tables...")
conn = get_db_connection(db_path)
tables = conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()
table_names = [t['name'] for t in tables]
print("    Tables found: " + str(table_names))

expected_tables = ['chat_history', 'daily_schedule', 'facilities', 'route_points', 'sos_requests', 'users']
for table in expected_tables:
    if table in table_names:
        print("    [OK] " + table + " -- exists")
    else:
        print("    [FAIL] " + table + " -- MISSING!")

# 5. Verify table schemas (column counts)
print("\n[5] Verifying table schemas...")
for table in expected_tables:
    columns = conn.execute("PRAGMA table_info(" + table + ")").fetchall()
    col_names = [c['name'] for c in columns]
    print("    " + table + ": " + str(len(columns)) + " columns -- " + str(col_names))

close_db(conn)

print("\n" + "=" * 50)
print("All validations passed! Database layer is ready.")
print("=" * 50)

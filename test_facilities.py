"""Phase 7 — Facilities Verification Script."""
import requests
import json

BASE = "http://127.0.0.1:5000"

print("=" * 55)
print("Wari Mitra - Facilities Module Verification")
print("=" * 55)

passed = 0
failed = 0

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}")
    if detail:
        print(f"         {detail}")

# ============================================================
# 1. Facilities page loads
# ============================================================
print("\n[1] Facilities Page")
r = requests.get(f"{BASE}/facilities")
check("GET /facilities returns 200", r.status_code == 200)
check("Contains page heading", "Nearby Facilities" in r.text)
check("Contains search box", 'facilitySearch' in r.text)
check("Contains Near Me button", 'nearMeBtn' in r.text)
check("Contains category filters", 'categoryFilters' in r.text)
check("Contains All filter", 'data-type="all"' in r.text)
check("Contains Medical filter", 'data-type="medical"' in r.text)
check("Contains Water filter", 'data-type="water"' in r.text)
check("Contains Toilet filter", 'data-type="toilet"' in r.text)
check("Contains Food filter", 'data-type="food"' in r.text)
check("Contains Shelter filter", 'data-type="shelter"' in r.text)
check("Contains Emergency filter", 'data-type="emergency"' in r.text)
check("Contains mini map", 'facilityMap' in r.text)
check("Contains facility grid", 'facilityGrid' in r.text)
check("Contains empty state", 'emptyState' in r.text)
check("Contains facilities.js", 'facilities.js' in r.text)

# ============================================================
# 2. API /api/facilities — all
# ============================================================
print("\n[2] API /api/facilities (all)")
r = requests.get(f"{BASE}/api/facilities")
check("GET /api/facilities returns 200", r.status_code == 200)
data = r.json()
check("Returns JSON array", isinstance(data, list))
check("Has 18 facilities", len(data) == 18, f"count={len(data)}")
check("Has id field", 'id' in data[0] if data else False)
check("Has name field", 'name' in data[0] if data else False)
check("Has type field", 'type' in data[0] if data else False)
check("Has latitude field", 'latitude' in data[0] if data else False)
check("Has longitude field", 'longitude' in data[0] if data else False)
check("Has description field", 'description' in data[0] if data else False)

# ============================================================
# 3. Category filtering
# ============================================================
categories = ['medical', 'water', 'toilet', 'food', 'shelter', 'emergency']
print("\n[3] Category Filtering")
for cat in categories:
    r = requests.get(f"{BASE}/api/facilities?type={cat}")
    cat_data = r.json()
    all_match = all(f['type'] == cat for f in cat_data)
    check(f"?type={cat}: {len(cat_data)} results, all match", all_match and len(cat_data) > 0, f"count={len(cat_data)}")

# Test all filter
r = requests.get(f"{BASE}/api/facilities?type=all")
check("?type=all returns all 18", len(r.json()) == 18)

# ============================================================
# 4. Empty results for non-existent type
# ============================================================
print("\n[4] Empty Results")
r = requests.get(f"{BASE}/api/facilities?type=nonexistent")
check("Non-existent type returns empty", len(r.json()) == 0)

# ============================================================
# 5. Existing modules still work
# ============================================================
print("\n[5] Existing Modules")
r = requests.get(f"{BASE}/")
check("Home page still loads", r.status_code == 200 and "AstraOps AI" in r.text)


r = requests.get(f"{BASE}/login")
check("Login page still loads", r.status_code == 200 and "loginForm" in r.text)

r = requests.get(f"{BASE}/register")
check("Register page still loads", r.status_code == 200 and "registerForm" in r.text)

r = requests.get(f"{BASE}/map")
check("Map page still loads", r.status_code == 200 and 'id="map"' in r.text)

r = requests.get(f"{BASE}/api/route")
route_data = r.json()
check("Route API still returns data", len(route_data) == 26, f"route_points={len(route_data)}")

r = requests.get(f"{BASE}/api/schedule")
sched_data = r.json()
check("Schedule API still returns data", len(sched_data) == 13, f"schedule={len(sched_data)}")

# ============================================================
# 6. Demo data markers
# ============================================================
print("\n[6] Demo Data Verification")
all_demo = all("DEMO" in f['name'] or "DEMO" in (f['description'] or '') for f in data)
check("All facilities marked as DEMO", all_demo)

types_found = set(f['type'] for f in data)
check("All 6 categories present", types_found == set(categories), f"types={types_found}")

# ============================================================
# 7. No schema changes
# ============================================================
print("\n[7] Schema Integrity")
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from models.db import get_db_connection
from config import Config
conn = get_db_connection(Config.DATABASE)
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
table_names = [t['name'] for t in tables]
expected = ['chat_history', 'daily_schedule', 'facilities', 'route_points', 'sos_requests', 'users']
check("All original tables exist", all(t in table_names for t in expected))
check("No extra tables created", set(table_names) - set(expected + ['sqlite_sequence']) == set(), f"tables={table_names}")

# Verify facilities schema unchanged
cols = conn.execute("PRAGMA table_info(facilities)").fetchall()
col_names = [c['name'] for c in cols]
check("Facilities schema unchanged", col_names == ['id', 'name', 'type', 'latitude', 'longitude', 'description'], f"columns={col_names}")
conn.close()

# ============================================================
# Summary
# ============================================================
print(f"\n{'=' * 55}")
print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
print(f"{'=' * 55}")

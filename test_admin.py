"""
Phase 34 Verification Test Suite — Volunteer Location Tracking, Safety System & Platform Integrity.

Tests:
1. Access Control on Admin Endpoints (Unauthenticated redirected, Normal pilgrim blocked, Admin 200 OK)
2. Login Selection Portal (GET /login) loads with separate Pilgrim & Admin options with AstraOps AI branding
3. Dedicated Pilgrim Login Portal (GET /login/pilgrim, POST /login/pilgrim)
4. Dedicated Admin Login Portal (GET /login/admin)
5. Admin Login with Updated Credentials (5555555555 / shreyash0745) through /login/admin -> 200 OK & Redirect to /admin
6. Wrong Admin Password is rejected
7. Admin credentials (5555555555) rejected on Pilgrim Login portal (/login/pilgrim)
8. Regular pilgrim rejected on Admin Login portal (/login/admin)
9. Database integrity: Admin account is_admin=1, is_active=1, securely hashed (not plaintext)
10. Inactive Account login enforcement
11. Audit Logging: ADMIN_LOGIN & ADMIN_LOGOUT
12. Sensitive Credential Exclusion (0% password / hash exposure)
13. Full Pilgrim Route Regression
14. Global Branding Verification: AstraOps AI across all core and admin endpoints
15. Phase 34 Volunteer Tracking & Safety:
    - POST /api/volunteer/location authentication & role validation (401 for unauth, 403 for pilgrim)
    - Coordinate validation (-90..90, -180..180, missing/invalid payload -> 400)
    - Valid location update for active volunteer (200 OK)
    - Freshness calculation (LIVE, RECENT, STALE, OFFLINE)
    - Volunteer markers and summary metrics in GET /admin/map
    - Admin Volunteer Directory (GET /admin/volunteers) rendering & filters
    - Volunteer status toggle (POST /admin/volunteers/<id>/toggle-status) with audit log
    - Inactive volunteer location update rejection
    - Cross-volunteer security (identity derived strictly from session)
"""

import sys
import os
import requests
import time

BASE_URL = "http://127.0.0.1:5000"

def run_tests():
    print("============================================================")
    print("  AstraOps AI — Phase 34 Volunteer Tracking & Safety Tests")
    print("============================================================\n")

    passed = 0
    failed = 0

    def check(name, condition, extra_info=""):
        nonlocal passed, failed
        if condition:
            print(f"  [PASS] {name}")
            passed += 1
        else:
            print(f"  [FAIL] {name} {extra_info}")
            failed += 1

    session_anon = requests.Session()
    session_user = requests.Session()
    session_admin = requests.Session()
    session_volunteer = requests.Session()

    # ------------------------------------------------------------
    # Test 1: Access Control on Admin Endpoints
    # ------------------------------------------------------------
    print("--- Test 1: Access Control ---")
    admin_endpoints = [
        "/admin", "/admin/sos", "/admin/users", "/admin/map",
        "/admin/facilities", "/admin/monitoring", "/admin/activity",
        "/admin/volunteers"
    ]
    for ep in admin_endpoints:
        r_unauth = session_anon.get(f"{BASE_URL}{ep}", allow_redirects=False)
        check(f"Unauthenticated GET {ep} is redirected", r_unauth.status_code in (301, 302, 303, 307, 308))

    # Register Normal Pilgrim User
    user_phone = "9876543210"
    user_pass = "userpass123"
    session_user.post(f"{BASE_URL}/register", data={
        "name": "Normal Pilgrim",
        "phone": user_phone,
        "password": user_pass,
        "confirm_password": user_pass
    })

    # ------------------------------------------------------------
    # Test 2: Login Selection Portal (GET /login)
    # ------------------------------------------------------------
    print("\n--- Test 2: Login Selection Portal ---")
    r_login_select = session_anon.get(f"{BASE_URL}/login")
    check("GET /login returns 200 OK", r_login_select.status_code == 200)
    check("Login selection contains Pilgrim option", "/login/pilgrim" in r_login_select.text)
    check("Login selection contains Admin option", "/login/admin" in r_login_select.text)
    check("Login selection header has AstraOps AI", "ASTRAOPS AI" in r_login_select.text or "AstraOps AI" in r_login_select.text)

    # ------------------------------------------------------------
    # Test 3: Dedicated Pilgrim Login Portal
    # ------------------------------------------------------------
    print("\n--- Test 3: Dedicated Pilgrim Login Portal ---")
    r_pilgrim_page = session_anon.get(f"{BASE_URL}/login/pilgrim")
    check("GET /login/pilgrim returns 200 OK", r_pilgrim_page.status_code == 200)

    # Pilgrim authentication via /login/pilgrim
    r_pilgrim_auth = session_user.post(f"{BASE_URL}/login/pilgrim", data={
        "phone": user_phone,
        "password": user_pass
    }, allow_redirects=True)
    check("POST /login/pilgrim succeeds for normal pilgrim", r_pilgrim_auth.status_code == 200)

    # Verify regular pilgrim is blocked from admin routes
    for ep in admin_endpoints:
        r_user_block = session_user.get(f"{BASE_URL}{ep}", allow_redirects=False)
        check(f"Authenticated pilgrim GET {ep} is blocked", r_user_block.status_code in (301, 302, 303, 307, 308))

    # ------------------------------------------------------------
    # Test 4: Phase 32 Admin Login with Updated Credentials
    # ------------------------------------------------------------
    print("\n--- Test 4: Updated Admin Credentials Authentication ---")
    admin_phone = "5555555555"
    admin_pass = "shreyash0745"

    r_admin_page = session_anon.get(f"{BASE_URL}/login/admin")
    check("GET /login/admin returns 200 OK", r_admin_page.status_code == 200)

    # 4a: Wrong password for Admin must be rejected
    session_wrong_admin = requests.Session()
    r_wrong_pass = session_wrong_admin.post(f"{BASE_URL}/login/admin", data={
        "phone": admin_phone,
        "password": "wrongpassword123"
    }, allow_redirects=True)
    check("Wrong Admin password is rejected", "invalid phone number or password" in r_wrong_pass.text.lower())

    # 4b: Admin credentials (5555555555) must NOT authenticate as regular pilgrim on /login/pilgrim
    session_admin_as_pilgrim = requests.Session()
    r_admin_pilgrim = session_admin_as_pilgrim.post(f"{BASE_URL}/login/pilgrim", data={
        "phone": admin_phone,
        "password": admin_pass
    }, allow_redirects=True)
    check("Admin credentials rejected on /login/pilgrim", "this login is for pilgrims" in r_admin_pilgrim.text.lower())

    # 4c: Regular pilgrim attempting Admin login MUST BE REJECTED
    session_fake_admin = requests.Session()
    r_fake_admin = session_fake_admin.post(f"{BASE_URL}/login/admin", data={
        "phone": user_phone,
        "password": user_pass
    }, allow_redirects=True)
    check("Regular pilgrim rejected on /login/admin", "administrator privileges are required" in r_fake_admin.text.lower())

    # 4d: Successful Admin Login with 5555555555 / shreyash0745
    r_admin_auth = session_admin.post(f"{BASE_URL}/login/admin", data={
        "phone": admin_phone,
        "password": admin_pass
    }, allow_redirects=True)
    check("POST /login/admin succeeds with updated credentials", r_admin_auth.status_code == 200)
    check("Admin redirected to /admin dashboard", r_admin_auth.url.endswith("/admin") or "/admin" in r_admin_auth.text)

    # Verify admin can access all admin endpoints
    for ep in admin_endpoints:
        check(f"Admin GET {ep} returns 200 OK", session_admin.get(f"{BASE_URL}{ep}").status_code == 200)

    # ------------------------------------------------------------
    # Test 5: Database Checks on Admin Account
    # ------------------------------------------------------------
    print("\n--- Test 5: Database Checks on Admin Account ---")
    from models.user_model import get_user_by_phone
    from config import Config
    admin_db_user = get_user_by_phone(Config.DATABASE, admin_phone)
    check("Admin user exists in database with phone 5555555555", admin_db_user is not None)
    check("Admin user has is_admin = 1", bool(admin_db_user['is_admin']) == True)
    check("Admin user has is_active = 1", int(admin_db_user['is_active']) == 1)
    check("Admin password is securely hashed (not plaintext)", not admin_db_user['password_hash'].startswith("shreyash") and len(admin_db_user['password_hash']) > 20)

    # ------------------------------------------------------------
    # Test 6: Inactive Account Login Enforcement
    # ------------------------------------------------------------
    print("\n--- Test 6: Inactive Account Enforcement ---")
    test_phone = f"92{int(time.time() * 1000) % 100000000:08d}"
    test_pass = "secret123"
    requests.post(f"{BASE_URL}/register", data={
        "name": "Inactive Pilgrim",
        "phone": test_phone,
        "password": test_pass,
        "confirm_password": test_pass
    })

    test_user = get_user_by_phone(Config.DATABASE, test_phone)
    target_id = test_user['id']

    # Disable user via admin management
    session_admin.post(f"{BASE_URL}/admin/users/{target_id}/toggle-status", allow_redirects=True)

    # Inactive user login attempt via /login/pilgrim
    session_disabled = requests.Session()
    r_dis_login = session_disabled.post(f"{BASE_URL}/login/pilgrim", data={
        "phone": test_phone,
        "password": test_pass
    }, allow_redirects=True)
    check("Disabled user login via /login/pilgrim is rejected", "account is currently inactive" in r_dis_login.text.lower())

    # Reactivate user
    session_admin.post(f"{BASE_URL}/admin/users/{target_id}/toggle-status", allow_redirects=True)
    r_re_login = session_disabled.post(f"{BASE_URL}/login/pilgrim", data={
        "phone": test_phone,
        "password": test_pass
    }, allow_redirects=True)
    check("Reactivated user login via /login/pilgrim succeeds", r_re_login.status_code == 200)

    # ------------------------------------------------------------
    # Test 7: Audit Logging for Admin Login & Logout
    # ------------------------------------------------------------
    print("\n--- Test 7: Audit Logging ---")
    r_activity = session_admin.get(f"{BASE_URL}/admin/activity?action=ADMIN_LOGIN")
    check("Audit log contains ADMIN_LOGIN", "ADMIN_LOGIN" in r_activity.text)

    # Admin Logout
    r_logout = session_admin.get(f"{BASE_URL}/admin/logout", allow_redirects=True)
    check("Admin logout succeeds", r_logout.status_code == 200)

    # Re-login to check ADMIN_LOGOUT entry
    session_admin.post(f"{BASE_URL}/login/admin", data={"phone": admin_phone, "password": admin_pass})
    r_activity_logout = session_admin.get(f"{BASE_URL}/admin/activity?action=ADMIN_LOGOUT")
    check("Audit log contains ADMIN_LOGOUT", "ADMIN_LOGOUT" in r_activity_logout.text)

    # ------------------------------------------------------------
    # Test 8: Sensitive Credential Exclusion
    # ------------------------------------------------------------
    print("\n--- Test 8: Sensitive Credential Exclusion ---")
    for page in ["/login", "/login/pilgrim", "/login/admin", "/admin/users", "/admin/activity", "/admin/volunteers"]:
        r_page = session_admin.get(f"{BASE_URL}{page}")
        check(f"No password_hash exposed in {page}", "password_hash" not in r_page.text)
        check(f"No secret API key exposed in {page}", "AIzaSy" not in r_page.text and (not Config.GEMINI_API_KEY or Config.GEMINI_API_KEY not in r_page.text))
        check(f"Plaintext password not in {page}", "shreyash0745" not in r_page.text)

    # ------------------------------------------------------------
    # Test 9: Full Pilgrim Route Regression
    # ------------------------------------------------------------
    print("\n--- Test 9: Full Pilgrim Route Regression ---")
    for endpoint in ["/", "/map", "/facilities", "/weather", "/chat", "/sos", "/schedule", "/profile"]:
        r = session_user.get(f"{BASE_URL}{endpoint}")
        check(f"Pilgrim GET {endpoint} returns 200 OK", r.status_code == 200)

    # ------------------------------------------------------------
    # Test 10: Phase 33 Global Branding Verification (AstraOps AI)
    # ------------------------------------------------------------
    print("\n--- Test 10: Phase 33 Global Branding Verification ---")
    branding_pages_anon = ["/", "/login", "/login/admin", "/login/pilgrim", "/chat", "/about", "/facilities", "/weather", "/schedule", "/sos"]
    for p in branding_pages_anon:
        r_b = session_anon.get(f"{BASE_URL}{p}")
        check(f"Page {p} contains 'AstraOps AI' branding", "AstraOps AI" in r_b.text)

    for ap in admin_endpoints:
        r_ab = session_admin.get(f"{BASE_URL}{ap}")
        check(f"Admin page {ap} contains 'AstraOps AI' branding", "AstraOps AI" in r_ab.text)

    # ------------------------------------------------------------
    # Test 11: Phase 34 Volunteer Tracking & Safety System
    # ------------------------------------------------------------
    print("\n--- Test 11: Phase 34 Volunteer Location Tracking & Safety ---")
    from models.volunteer_model import (
        create_volunteer, get_volunteer_by_id, get_volunteer_by_user_id,
        calculate_freshness, set_volunteer_status
    )

    # 11a: Unauthenticated location update must return 401
    r_unauth_loc = session_anon.post(f"{BASE_URL}/api/volunteer/location", json={"latitude": 18.5, "longitude": 73.8})
    check("Unauthenticated POST /api/volunteer/location returns 401", r_unauth_loc.status_code == 401)

    # 11b: Regular pilgrim location update must return 403
    r_pilgrim_loc = session_user.post(f"{BASE_URL}/api/volunteer/location", json={"latitude": 18.5, "longitude": 73.8})
    check("Pilgrim POST /api/volunteer/location returns 403 Forbidden", r_pilgrim_loc.status_code == 403)

    # 11c: Register and link a designated volunteer user
    vol_phone = f"88{int(time.time() * 1000) % 100000000:08d}"
    vol_pass = "volunteer123"
    session_volunteer.post(f"{BASE_URL}/register", data={
        "name": "Live Field Volunteer",
        "phone": vol_phone,
        "password": vol_pass,
        "confirm_password": vol_pass
    })
    session_volunteer.post(f"{BASE_URL}/login/pilgrim", data={"phone": vol_phone, "password": vol_pass})

    vol_user = get_user_by_phone(Config.DATABASE, vol_phone)
    vol_id = create_volunteer(Config.DATABASE, "Live Field Volunteer", vol_phone, user_id=vol_user['id'], status='ACTIVE')
    from models.user_model import set_user_volunteer
    set_user_volunteer(Config.DATABASE, vol_user['id'], 1)
    check("Volunteer created in database", vol_id is not None)


    # 11d: Coordinate validation on POST /api/volunteer/location
    r_no_body = session_volunteer.post(f"{BASE_URL}/api/volunteer/location", data="invalid", headers={"Content-Type": "application/json"})
    check("Invalid JSON body returns 400", r_no_body.status_code == 400)

    r_missing_coords = session_volunteer.post(f"{BASE_URL}/api/volunteer/location", json={"latitude": 18.5})
    check("Missing longitude returns 400", r_missing_coords.status_code == 400)

    r_invalid_range = session_volunteer.post(f"{BASE_URL}/api/volunteer/location", json={"latitude": 105.0, "longitude": 73.8})
    check("Out-of-range latitude returns 400", r_invalid_range.status_code == 400)

    # 11e: Valid location submission updates volunteer location
    r_valid_loc = session_volunteer.post(f"{BASE_URL}/api/volunteer/location", json={"latitude": 18.7195, "longitude": 73.7695})
    check("Valid POST /api/volunteer/location returns 200 OK", r_valid_loc.status_code == 200)
    check("Location response contains success=true", r_valid_loc.json().get('success') == True)

    # Check status endpoint
    r_status = session_volunteer.get(f"{BASE_URL}/api/volunteer/status")
    check("GET /api/volunteer/status returns 200 OK", r_status.status_code == 200)
    check("Volunteer status shows LIVE freshness", r_status.json().get('volunteer', {}).get('freshness') == 'LIVE')

    # 11f: Freshness calculation unit checks
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    t_live = (now - timedelta(seconds=20)).strftime('%Y-%m-%d %H:%M:%S')
    t_recent = (now - timedelta(seconds=120)).strftime('%Y-%m-%d %H:%M:%S')
    t_stale = (now - timedelta(seconds=600)).strftime('%Y-%m-%d %H:%M:%S')

    check("Freshness within 60s is LIVE", calculate_freshness(t_live)[0] == 'LIVE')
    check("Freshness 61-300s is RECENT", calculate_freshness(t_recent)[0] == 'RECENT')
    check("Freshness >300s is STALE", calculate_freshness(t_stale)[0] == 'STALE')
    check("Inactive volunteer freshness is OFFLINE", calculate_freshness(t_live, status='INACTIVE')[0] == 'OFFLINE')
    check("None timestamp freshness is OFFLINE", calculate_freshness(None)[0] == 'OFFLINE')

    # 11g: Admin Ground Situation Map contains Volunteer markers and stats
    r_map = session_admin.get(f"{BASE_URL}/admin/map")
    check("Admin GET /admin/map returns 200", r_map.status_code == 200)
    check("Admin map contains volunteerMarkersData", "volunteerMarkersData" in r_map.text or "volunteer_markers" in r_map.text)
    check("Admin map contains Live Field Volunteer", "Live Field Volunteer" in r_map.text)
    check("Admin map displays Volunteers stat badge", "Volunteers:" in r_map.text)

    # 11h: Admin Volunteer Directory (GET /admin/volunteers)
    r_vol_dir = session_admin.get(f"{BASE_URL}/admin/volunteers")
    check("Admin GET /admin/volunteers returns 200 OK", r_vol_dir.status_code == 200)
    check("Volunteer directory displays volunteer name", "Live Field Volunteer" in r_vol_dir.text)
    check("Volunteer directory contains search input", 'name="q"' in r_vol_dir.text)

    # Search filter test
    r_vol_search = session_admin.get(f"{BASE_URL}/admin/volunteers?q=Field")
    check("Volunteer directory search finds matching volunteer", "Live Field Volunteer" in r_vol_search.text)

    # 11i: Admin Toggle Volunteer Status & Audit Logging
    r_toggle = session_admin.post(f"{BASE_URL}/admin/volunteers/{vol_id}/toggle-status", allow_redirects=True)
    check("POST /admin/volunteers/<id>/toggle-status returns 200", r_toggle.status_code == 200)
    vol_after = get_volunteer_by_id(Config.DATABASE, vol_id)
    check("Volunteer status changed to INACTIVE", vol_after['status'] == 'INACTIVE')

    # Inactive volunteer cannot post location
    r_inactive_post = session_volunteer.post(f"{BASE_URL}/api/volunteer/location", json={"latitude": 18.5, "longitude": 73.8})
    check("Inactive volunteer POST location returns 403", r_inactive_post.status_code == 403)

    # Audit log check for volunteer toggle
    r_vol_act = session_admin.get(f"{BASE_URL}/admin/activity?action=VOLUNTEER_STATUS_TOGGLED")
    check("Audit log records VOLUNTEER_STATUS_TOGGLED", "VOLUNTEER_STATUS_TOGGLED" in r_vol_act.text)

    # Reactivate volunteer
    session_admin.post(f"{BASE_URL}/admin/volunteers/{vol_id}/toggle-status", allow_redirects=True)

    # ------------------------------------------------------------
    # Test 12: Phase 34 Admin User Directory Volunteer Role Integration
    # ------------------------------------------------------------
    print("\n--- Test 12: Phase 34 Admin User Directory Volunteer Role Integration ---")
    # 12a: Directory page access
    r_users_page = session_admin.get(f"{BASE_URL}/admin/users")
    check("Admin GET /admin/users returns 200 OK", r_users_page.status_code == 200)

    # 12b: Admin badge verification
    check("Admin user directory displays ADMIN badge", "ADMIN" in r_users_page.text)

    # 12c: Approved volunteer displays VOLUNTEER badge
    check("Approved volunteer displays VOLUNTEER badge", "VOLUNTEER" in r_users_page.text)

    # 12d: Regular pilgrim displays PILGRIM badge
    check("Regular pilgrim displays PILGRIM badge", "PILGRIM" in r_users_page.text)

    # 12e: Role filter ?role=volunteer works
    r_filter_vol = session_admin.get(f"{BASE_URL}/admin/users?role=volunteer")
    check("GET /admin/users?role=volunteer returns 200 OK", r_filter_vol.status_code == 200)
    check("Volunteer filter shows volunteer account", vol_phone in r_filter_vol.text or "Live Field Volunteer" in r_filter_vol.text)
    check("Volunteer filter excludes normal pilgrim", "Normal Pilgrim" not in r_filter_vol.text)

    # 12f: Role filter ?role=admin works
    r_filter_adm = session_admin.get(f"{BASE_URL}/admin/users?role=admin")
    check("GET /admin/users?role=admin returns 200 OK", r_filter_adm.status_code == 200)
    check("Admin filter shows admin account", admin_phone in r_filter_adm.text)
    check("Admin filter excludes volunteer", "Live Field Volunteer" not in r_filter_adm.text)

    # 12g: Role filter ?role=regular (pilgrims) works and EXCLUDES volunteers
    r_filter_reg = session_admin.get(f"{BASE_URL}/admin/users?role=regular")
    check("GET /admin/users?role=regular returns 200 OK", r_filter_reg.status_code == 200)
    check("Pilgrim filter shows normal pilgrim", "Normal Pilgrim" in r_filter_reg.text)
    check("Pilgrim filter excludes volunteer (not classified as pilgrim)", "Live Field Volunteer" not in r_filter_reg.text)

    # 12h: Role filter ?role=all works
    r_filter_all = session_admin.get(f"{BASE_URL}/admin/users?role=all")
    check("GET /admin/users?role=all returns 200 OK", r_filter_all.status_code == 200)
    check("All filter contains admin", admin_phone in r_filter_all.text)
    check("All filter contains volunteer", vol_phone in r_filter_all.text or "Live Field Volunteer" in r_filter_all.text)

    # 12i: Search by volunteer name
    r_search_name = session_admin.get(f"{BASE_URL}/admin/users?q=Field+Volunteer")
    check("Search by name finds volunteer", "Live Field Volunteer" in r_search_name.text)

    # 12j: Search by volunteer phone
    r_search_phone = session_admin.get(f"{BASE_URL}/admin/users?q={vol_phone}")
    check("Search by phone finds volunteer", vol_phone in r_search_phone.text)

    # 12k: User details modal and JSON API for volunteer
    r_vol_json = session_admin.get(f"{BASE_URL}/api/admin/users/{vol_user['id']}/details")
    check("GET /api/admin/users/<id>/details returns 200 OK", r_vol_json.status_code == 200)
    check("Volunteer details JSON reports role=VOLUNTEER", r_vol_json.json().get('user', {}).get('role') == 'VOLUNTEER')
    check("Volunteer details JSON reports is_volunteer=True", r_vol_json.json().get('user', {}).get('is_volunteer') == True)
    check("Volunteer details JSON excludes password/hash", 'password' not in r_vol_json.json().get('user', {}) and 'password_hash' not in r_vol_json.json().get('user', {}))

    # 12l: User details JSON API for admin
    admin_user_db = get_user_by_phone(Config.DATABASE, admin_phone)
    r_adm_json = session_admin.get(f"{BASE_URL}/api/admin/users/{admin_user_db['id']}/details")
    check("Admin details JSON reports role=ADMIN", r_adm_json.json().get('user', {}).get('role') == 'ADMIN')

    # 12m: User details JSON API for pilgrim
    pilgrim_user_db = get_user_by_phone(Config.DATABASE, user_phone)
    r_pil_json = session_admin.get(f"{BASE_URL}/api/admin/users/{pilgrim_user_db['id']}/details")
    check("Pilgrim details JSON reports role=PILGRIM", r_pil_json.json().get('user', {}).get('role') == 'PILGRIM')

    # 12n: Active/Inactive controls on volunteer user account
    session_admin.post(f"{BASE_URL}/admin/users/{vol_user['id']}/toggle-status", allow_redirects=True)
    r_vol_inactive = session_admin.get(f"{BASE_URL}/api/admin/users/{vol_user['id']}/details")
    check("Disabled volunteer reports INACTIVE", r_vol_inactive.json().get('user', {}).get('status_label') == 'INACTIVE')
    # Reactivate volunteer user account
    session_admin.post(f"{BASE_URL}/admin/users/{vol_user['id']}/toggle-status", allow_redirects=True)
    r_vol_active = session_admin.get(f"{BASE_URL}/api/admin/users/{vol_user['id']}/details")
    check("Reactivated volunteer reports ACTIVE", r_vol_active.json().get('user', {}).get('status_label') == 'ACTIVE')

    # 12o: Unauthorized access protection
    r_unauth_users = session_anon.get(f"{BASE_URL}/admin/users", allow_redirects=False)
    check("Anonymous user redirected from /admin/users", r_unauth_users.status_code in (301, 302, 303, 307, 308))
    r_pilgrim_users = session_user.get(f"{BASE_URL}/admin/users", allow_redirects=False)
    check("Pilgrim user blocked from /admin/users", r_pilgrim_users.status_code in (301, 302, 303, 307, 308))

    # 12p: Volunteer login via /login/volunteer remains functional
    session_vol_login = requests.Session()
    r_vol_login = session_vol_login.post(f"{BASE_URL}/login/volunteer", data={"phone": vol_phone, "password": vol_pass}, allow_redirects=True)
    check("Volunteer login via /login/volunteer succeeds", r_vol_login.status_code == 200)

    # 12q: Volunteer dashboard remains functional
    r_vol_dash = session_vol_login.get(f"{BASE_URL}/volunteer/dashboard")
    check("Volunteer dashboard GET returns 200 OK", r_vol_dash.status_code == 200)

    # Teardown / cleanup created test accounts to maintain pristine database
    from models.db import get_db_connection
    conn = get_db_connection(Config.DATABASE)
    try:
        conn.execute("DELETE FROM volunteer_locations WHERE volunteer_user_id IN (?, ?)", (vol_user['id'], pilgrim_user_db['id']))
        conn.execute("DELETE FROM volunteer_assignments WHERE volunteer_id = ?", (vol_id,))
        conn.execute("DELETE FROM volunteers WHERE id = ?", (vol_id,))
        conn.execute("DELETE FROM volunteer_requests WHERE user_id IN (?, ?, ?)", (vol_user['id'], target_id, pilgrim_user_db['id']))
        conn.execute("DELETE FROM admin_activity_log WHERE admin_user_id IN (?, ?, ?) OR (entity_type = 'USER' AND entity_id IN (?, ?, ?))", (vol_user['id'], target_id, pilgrim_user_db['id'], vol_user['id'], target_id, pilgrim_user_db['id']))
        conn.execute("DELETE FROM chat_history WHERE user_id IN (?, ?, ?)", (vol_user['id'], target_id, pilgrim_user_db['id']))
        conn.execute("DELETE FROM users WHERE id IN (?, ?, ?)", (vol_user['id'], target_id, pilgrim_user_db['id']))
        conn.commit()
    except Exception as e:
        print(f"Teardown error: {e}")
    finally:
        conn.close()


    print("\n============================================================")
    print(f"  PHASE 34 VERIFICATION RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
    print("============================================================")

    if failed > 0:
        sys.exit(1)

if __name__ == '__main__':
    run_tests()


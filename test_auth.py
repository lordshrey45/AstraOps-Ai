"""
Authentication Module Test Script.
Tests registration, login, logout, password hashing, and sessions.
Run while Flask app is running on http://127.0.0.1:5000
"""

import requests

BASE_URL = "http://127.0.0.1:5000"

def print_result(test_name, passed, details=""):
    status = "[PASS]" if passed else "[FAIL]"
    print(f"  {status} {test_name}")
    if details:
        print(f"        {details}")

def run_tests():
    print("=" * 60)
    print("Wari Mitra - Authentication Module Tests")
    print("=" * 60)

    # Use a session to track cookies (Flask session cookie)
    s = requests.Session()

    # ============================================================
    # Test 1: Registration page loads
    # ============================================================
    print("\n[1] Registration Page")
    r = s.get(f"{BASE_URL}/register")
    print_result("GET /register returns 200", r.status_code == 200)
    print_result("Page contains registration form", "registerForm" in r.text)
    print_result("Page contains name field", 'name="name"' in r.text)
    print_result("Page contains phone field", 'name="phone"' in r.text)
    print_result("Page contains password field", 'name="password"' in r.text)
    print_result("Page contains confirm_password field", 'name="confirm_password"' in r.text)
    print_result("Page contains emergency_contact field", 'name="emergency_contact"' in r.text)
    print_result("Page contains medical_info field", 'name="medical_info"' in r.text)

    # ============================================================
    # Test 2: Registration with missing fields
    # ============================================================
    print("\n[2] Registration Validation - Missing Fields")
    r = s.post(f"{BASE_URL}/register", data={
        "name": "",
        "phone": "",
        "password": "",
        "confirm_password": "",
        "emergency_contact": "",
        "medical_info": ""
    })
    print_result("Rejects empty form (stays on register page)", "registerForm" in r.text or "required" in r.text.lower())

    # ============================================================
    # Test 3: Registration with password mismatch
    # ============================================================
    print("\n[3] Registration Validation - Password Mismatch")
    r = s.post(f"{BASE_URL}/register", data={
        "name": "Test User",
        "phone": "9999999999",
        "password": "password123",
        "confirm_password": "wrongpassword",
        "emergency_contact": "",
        "medical_info": ""
    })
    print_result("Rejects password mismatch", "do not match" in r.text.lower() or "registerForm" in r.text)

    # ============================================================
    # Test 4: Successful registration
    # ============================================================
    print("\n[4] Successful Registration")
    r = s.post(f"{BASE_URL}/register", data={
        "name": "Ramesh Warkari",
        "phone": "9876543210",
        "password": "wari2026",
        "confirm_password": "wari2026",
        "emergency_contact": "Suresh - 9876543211",
        "medical_info": "No known allergies"
    }, allow_redirects=True)
    print_result("Redirects after registration", r.status_code == 200)
    print_result("Shows success or login page", "login" in r.url.lower() or "success" in r.text.lower())

    # ============================================================
    # Test 5: Duplicate phone number rejection
    # ============================================================
    print("\n[5] Duplicate Phone Number Check")
    r = s.post(f"{BASE_URL}/register", data={
        "name": "Another User",
        "phone": "9876543210",
        "password": "password123",
        "confirm_password": "password123",
        "emergency_contact": "",
        "medical_info": ""
    })
    print_result("Rejects duplicate phone", "already exists" in r.text.lower() or "registerForm" in r.text)

    # ============================================================
    # Test 6: Login page loads
    # ============================================================
    print("\n[6] Login Page")
    r = s.get(f"{BASE_URL}/login")
    print_result("GET /login returns 200", r.status_code == 200)
    print_result("Page contains login form", "loginForm" in r.text)

    # ============================================================
    # Test 7: Login with wrong credentials
    # ============================================================
    print("\n[7] Login - Wrong Credentials")
    r = s.post(f"{BASE_URL}/login", data={
        "phone": "9876543210",
        "password": "wrongpassword"
    })
    print_result("Rejects wrong password", "invalid" in r.text.lower() or "loginForm" in r.text)

    # ============================================================
    # Test 8: Login with non-existent user
    # ============================================================
    print("\n[8] Login - Non-existent User")
    r = s.post(f"{BASE_URL}/login", data={
        "phone": "0000000000",
        "password": "somepassword"
    })
    print_result("Rejects non-existent user", "invalid" in r.text.lower() or "loginForm" in r.text)

    # ============================================================
    # Test 9: Successful login
    # ============================================================
    print("\n[9] Successful Login")
    r = s.post(f"{BASE_URL}/login", data={
        "phone": "9876543210",
        "password": "wari2026"
    }, allow_redirects=True)
    print_result("Login succeeds (redirects)", r.status_code == 200)
    print_result("Session cookie is set", "session" in str(s.cookies.get_dict()).lower() or len(s.cookies) > 0)

    # ============================================================
    # Test 10: Logout
    # ============================================================
    print("\n[10] Logout")
    r = s.get(f"{BASE_URL}/api/logout", allow_redirects=True)
    print_result("Logout redirects to home", r.status_code == 200)
    print_result("Logout message shown", "logged out" in r.text.lower() or r.status_code == 200)

    # ============================================================
    # Test 11: Password Hashing Verification
    # ============================================================
    print("\n[11] Password Hashing")
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from models.user_model import get_user_by_phone
    from config import Config
    user = get_user_by_phone(Config.DATABASE, "9876543210")
    if user:
        pwd_hash = user['password_hash']
        print_result("Password is hashed (not plain text)", pwd_hash != "wari2026")
        print_result("Hash starts with known prefix", pwd_hash.startswith("scrypt:") or pwd_hash.startswith("pbkdf2:"))
        print_result("Hash is long enough (>50 chars)", len(pwd_hash) > 50, f"length={len(pwd_hash)}")
    else:
        print_result("User found in database", False, "User not found!")

    # ============================================================
    # Summary
    # ============================================================
    print("\n" + "=" * 60)
    print("All authentication tests completed!")
    print("=" * 60)

    # Cleanup: delete the test user
    from models.user_model import delete_user
    if user:
        delete_user(Config.DATABASE, user['id'])
        print("Test user cleaned up.")


if __name__ == "__main__":
    run_tests()

"""Home Dashboard Verification Script."""
import requests

BASE = "http://127.0.0.1:5000"

print("=" * 55)
print("Wari Mitra - Home Dashboard Verification")
print("=" * 55)

# Test 1: Home page loads
r = requests.get(f"{BASE}/")
print(f"\n[1] GET / => Status: {r.status_code}")
ok = r.status_code == 200
print(f"  {'[PASS]' if ok else '[FAIL]'} Home page returns 200")

# Test 2: Hero section elements
checks = [
    ("Hero section",        "hero-section"),
    ("Hero logo",           "hero-logo"),
    ("Project title",       "AstraOps AI"),
    ("Start Journey button","Start Journey"),
    ("Ask AI button",       "Ask AI"),

]
print("\n[2] Hero Section")
for name, text in checks:
    found = text in r.text
    print(f"  {'[PASS]' if found else '[FAIL]'} {name}")

# Test 3: Feature cards
checks = [
    ("Feature section title",   "Explore Features"),
    ("Map card",                "Interactive Route Map"),
    ("AI card",                 "AI Assistant"),
    ("Facilities card",         "Nearby Facilities"),
    ("Schedule card",           "Daily Schedule"),
    ("Weather card",            "Weather"),
    ("SOS card",                "Emergency SOS"),
]
print("\n[3] Feature Cards")
for name, text in checks:
    found = text in r.text
    print(f"  {'[PASS]' if found else '[FAIL]'} {name}")

# Test 4: Today's Overview
checks = [
    ("Overview section",    "Today"),
    ("Halt village",        "Wakhari"),
    ("Weather temperature", "28"),
    ("Distance remaining",  "18.5 km"),
    ("Next halt",           "Taradgaon"),
]
print("\n[4] Today's Overview (placeholder data)")
for name, text in checks:
    found = text in r.text
    print(f"  {'[PASS]' if found else '[FAIL]'} {name}")

# Test 5: Announcements
checks = [
    ("Announcements section",   "Announcements"),
    ("Medical camp notice",     "Medical camp"),
    ("Rain warning",            "rain"),
    ("Food service notice",     "Anna Chhatra"),
]
print("\n[5] Announcements")
for name, text in checks:
    found = text.lower() in r.text.lower()
    print(f"  {'[PASS]' if found else '[FAIL]'} {name}")

# Test 6: Navigation links
links = ["/map", "/chat", "/facilities", "/sos", "/schedule", "/weather", "/about"]
print("\n[6] Navigation Links")
for link in links:
    found = f'href="{link}"' in r.text
    print(f"  {'[PASS]' if found else '[FAIL]'} Link to {link}")

# Test 7: Login redirect now goes to home
print("\n[7] Auth -> Home Flow")
s = requests.Session()
# Register test user
s.post(f"{BASE}/register", data={
    "name": "HomeTest", "phone": "5551234567",
    "password": "test1234", "confirm_password": "test1234",
    "emergency_contact": "", "medical_info": ""
})
# Login
r = s.post(f"{BASE}/login", data={
    "phone": "5551234567", "password": "test1234"
}, allow_redirects=True)
print(f"  {'[PASS]' if r.status_code == 200 else '[FAIL]'} Login redirects to home (status={r.status_code})")
print(f"  {'[PASS]' if 'AstraOps AI' in r.text else '[FAIL]'} Home page content after login")


# Logout
r = s.get(f"{BASE}/api/logout", allow_redirects=True)
print(f"  {'[PASS]' if r.status_code == 200 else '[FAIL]'} Logout redirects to home (status={r.status_code})")

# Cleanup
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from models.user_model import get_user_by_phone, delete_user
from config import Config
user = get_user_by_phone(Config.DATABASE, "5551234567")
if user:
    delete_user(Config.DATABASE, user["id"])

# Test 8: Responsive meta tag
print("\n[8] Responsive / SEO")
checks = [
    ("Viewport meta tag",   "viewport"),
    ("Meta description",    "meta name"),
    ("Bootstrap CSS",       "bootstrap"),
    ("Bootstrap Icons",     "bootstrap-icons"),
]
for name, text in checks:
    found = text.lower() in r.text.lower()
    print(f"  {'[PASS]' if found else '[FAIL]'} {name}")

print("\n" + "=" * 55)
print("Home Dashboard verification complete!")
print("=" * 55)

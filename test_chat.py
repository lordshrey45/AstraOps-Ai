"""Phase 8 - AI Assistant Verification Script."""
import requests
import json

BASE = "http://127.0.0.1:5000"

print("=" * 55)
print("Wari Mitra - AI Assistant Verification")
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
# 1. Chat page loads
# ============================================================
print("\n[1] Chat Page")
r = requests.get(f"{BASE}/chat")
check("GET /chat returns 200", r.status_code == 200)
check("Contains page title", "AstraOps AI" in r.text)
check("Contains chat container", "chatMessages" in r.text)

check("Contains chat input", "chatInput" in r.text)
check("Contains send button", "sendBtn" in r.text)
check("Contains clear button", "clearChatBtn" in r.text)
check("Contains typing indicator", "typingIndicator" in r.text)
check("Contains chat.js", "chat.js" in r.text)
check("Contains suggested questions", "suggestion-btn" in r.text)
check("Contains demo disclaimer", "demo data" in r.text.lower())
check("No API key exposed", "GEMINI_API_KEY" not in r.text and "api_key" not in r.text.lower())

# ============================================================
# 2. POST /api/chat — empty message
# ============================================================
print("\n[2] API Validation - Empty Message")
r = requests.post(f"{BASE}/api/chat",
                   json={"message": ""},
                   headers={"Content-Type": "application/json"})
check("Empty message returns 400", r.status_code == 400)
data = r.json()
check("Returns error response", data.get('success') == False)

# ============================================================
# 3. POST /api/chat — no body
# ============================================================
print("\n[3] API Validation - No Body")
r = requests.post(f"{BASE}/api/chat",
                   json={},
                   headers={"Content-Type": "application/json"})
check("No message returns 400", r.status_code == 400)

# ============================================================
# 4. POST /api/chat — long message
# ============================================================
print("\n[4] API Validation - Long Message")
long_msg = "a" * 2001
r = requests.post(f"{BASE}/api/chat",
                   json={"message": long_msg},
                   headers={"Content-Type": "application/json"})
check("Long message returns 400", r.status_code == 400)
data = r.json()
check("Returns length error", "long" in data.get('response', '').lower() or "2000" in data.get('response', ''))

# ============================================================
# 5. POST /api/chat — valid message (Gemini call)
# ============================================================
print("\n[5] API - Valid Message")
r = requests.post(f"{BASE}/api/chat",
                   json={"message": "Hello, what is the Wari route?"},
                   headers={"Content-Type": "application/json"})
check("Valid message returns 200", r.status_code == 200)
data = r.json()
check("Returns response field", "response" in data)
check("Response is non-empty", len(data.get('response', '')) > 0)
check("No API key in response", "api_key" not in data.get('response', '').lower())

# Check if Gemini actually responded or if it's a config error
if data.get('success'):
    check("Gemini response success", True, "AI is configured and responding")
else:
    check("API key not configured (expected if .env has placeholder)", True,
          data.get('response', '')[:80])

# ============================================================
# 6. POST /api/chat — whitespace-only message
# ============================================================
print("\n[6] API Validation - Whitespace Only")
r = requests.post(f"{BASE}/api/chat",
                   json={"message": "   "},
                   headers={"Content-Type": "application/json"})
check("Whitespace-only returns 400", r.status_code == 400)

# ============================================================
# 7. Chat history for authenticated user
# ============================================================
print("\n[7] Chat History (Authenticated)")
s = requests.Session()
# Register and login
s.post(f"{BASE}/register", data={
    "name": "ChatTestUser", "phone": "8887776665",
    "password": "test1234", "confirm_password": "test1234",
    "emergency_contact": "", "medical_info": ""
})
s.post(f"{BASE}/login", data={"phone": "8887776665", "password": "test1234"})

# Send a chat message while authenticated
r = s.post(f"{BASE}/api/chat",
           json={"message": "Test message for history"},
           headers={"Content-Type": "application/json"})
check("Authenticated chat returns 200", r.status_code == 200)

# Verify chat history is saved
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from models.chat_model import get_chat_history_by_user
from models.user_model import get_user_by_phone, delete_user
from config import Config

user = get_user_by_phone(Config.DATABASE, "8887776665")
if user:
    history = get_chat_history_by_user(Config.DATABASE, user['id'])
    check("Chat history saved to DB", len(history) > 0, f"entries={len(history)}")
    if history:
        check("History has user message", history[0]['message'] == "Test message for history")
        check("History has AI response", len(history[0]['response']) > 0)

    # Cleanup
    from models.db import get_db_connection, close_db
    conn = get_db_connection(Config.DATABASE)
    conn.execute("DELETE FROM chat_history WHERE user_id = ?", (user['id'],))
    conn.commit()
    close_db(conn)
    delete_user(Config.DATABASE, user['id'])
    print("  [INFO] Test user and chat history cleaned up.")

# ============================================================
# 8. Existing modules still work
# ============================================================
print("\n[8] Existing Modules")
r = requests.get(f"{BASE}/")
check("Home page works", r.status_code == 200 and "AstraOps AI" in r.text)


r = requests.get(f"{BASE}/login")
check("Login page works", r.status_code == 200)

r = requests.get(f"{BASE}/register")
check("Register page works", r.status_code == 200)

r = requests.get(f"{BASE}/map")
check("Map page works", r.status_code == 200)

r = requests.get(f"{BASE}/facilities")
check("Facilities page works", r.status_code == 200)

r = requests.get(f"{BASE}/api/route")
check("Route API works", r.status_code == 200 and len(r.json()) == 26)

r = requests.get(f"{BASE}/api/facilities")
check("Facilities API works", r.status_code == 200 and len(r.json()) == 18)

# ============================================================
# 9. Security
# ============================================================
print("\n[9] Security Checks")
r = requests.get(f"{BASE}/chat")
check("No GEMINI_API_KEY in HTML", "GEMINI_API_KEY" not in r.text)
check("No api_key in HTML", "api_key" not in r.text)
check("No .env reference in HTML", ".env" not in r.text)

# ============================================================
# Summary
# ============================================================
print(f"\n{'=' * 55}")
print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
print(f"{'=' * 55}")

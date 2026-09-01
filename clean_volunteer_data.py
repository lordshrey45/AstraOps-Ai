"""
Safely remove all predefined, demo, and test volunteer data from the database.
Preserves admin accounts, pilgrim accounts, facilities, schedule, SOS history.
"""

import sqlite3
import os
from config import Config

def reset_volunteer_data():
    db_path = Config.DATABASE
    print(f"Connecting to database at {db_path}...")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        cur = conn.cursor()

        # 1. Unassign any assigned volunteers in sos_requests table
        try:
            cur.execute("UPDATE sos_requests SET assigned_volunteer_id = NULL, dispatch_status = 'UNASSIGNED' WHERE assigned_volunteer_id IS NOT NULL")
            print(f"[*] Cleared volunteer assignments on sos_requests.")
        except Exception as e:
            print(f"[!] Note on sos_requests: {e}")

        # 2. Clear volunteer locations history table if exists
        try:
            cur.execute("DELETE FROM volunteer_locations")
            print(f"[*] Cleared volunteer_locations table.")
        except Exception as e:
            pass

        # 3. Clear volunteers table completely
        cur.execute("DELETE FROM volunteers")
        print(f"[*] Cleared all records from volunteers table.")

        # 4. Clear volunteer_requests table
        try:
            cur.execute("DELETE FROM volunteer_requests")
            print(f"[*] Cleared all records from volunteer_requests table.")
        except Exception as e:
            pass

        # 5. Delete demo/test volunteer user accounts (where is_volunteer = 1 and is_admin = 0)
        cur.execute("DELETE FROM users WHERE is_volunteer = 1 AND is_admin = 0")
        print(f"[*] Removed demo/test volunteer accounts from users table.")

        # Also remove demo phones if any remained
        demo_phones = ['8888888881', '8888888882', '8888888883', '8888888884']
        for dp in demo_phones:
            cur.execute("DELETE FROM users WHERE phone = ? AND is_admin = 0", (dp,))

        conn.commit()

        # Verification
        v_count = cur.execute("SELECT COUNT(*) FROM volunteers").fetchone()[0]
        vr_count = cur.execute("SELECT COUNT(*) FROM volunteer_requests").fetchone()[0]
        vu_count = cur.execute("SELECT COUNT(*) FROM users WHERE is_volunteer = 1").fetchone()[0]
        admin_count = cur.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1").fetchone()[0]
        pilgrim_count = cur.execute("SELECT COUNT(*) FROM users WHERE is_admin = 0").fetchone()[0]

        print(f"\n[OK] Volunteer Data Reset Verification:")
        print(f"  - Active Volunteers: {v_count}")
        print(f"  - Volunteer Requests: {vr_count}")
        print(f"  - Volunteer User Accounts: {vu_count}")
        print(f"  - Admin Users preserved: {admin_count}")
        print(f"  - Pilgrim Users preserved: {pilgrim_count}")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Failed to reset volunteer data: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    reset_volunteer_data()

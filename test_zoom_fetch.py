import os
from zoom_integration import zoom_mgr
from datetime import date
from supabase_client import supabase_mgr

def test_zoom():
    meeting_id = "89732348121"
    target_date = date(2026, 4, 11)
    
    print(f"--- Testing Zoom Attendance for {meeting_id} on {target_date} ---")
    
    participants = zoom_mgr.get_meeting_participants(meeting_id, target_date=target_date)
    print(f"Fetched {len(participants)} participants from Zoom.")
    
    for p in participants:
        name = p.get('name') or p.get('user_name')
        join_time = p.get('join_time')
        print(f"  - {name} (Joined: {join_time})")

    if not participants:
        print("⚠️ No participants found. Possible reasons:")
        print("  1. Meeting ID is incorrect.")
        print("  2. Class was not held on this meeting ID.")
        print("  3. API Token or Permissions issue.")

if __name__ == "__main__":
    test_zoom()

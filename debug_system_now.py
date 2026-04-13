import os
import pandas as pd
from supabase_client import supabase_mgr
from zoom_integration import zoom_mgr
from datetime import date, datetime, timedelta, timezone

# KST timezone
KST = timezone(timedelta(hours=9))

def debug_today():
    today = date(2026, 4, 11)
    target_date_str = today.isoformat()
    
    print(f"--- Debugging for {target_date_str} ---")
    
    # 1. Fetch schedules from Supabase
    try:
        schedules = supabase_mgr.get_schedule_for_date(target_date_str)
        print(f"Found {len(schedules)} schedules in Supabase for today.")
        
        for s in schedules:
            print(f"ID: {s['id']}")
            print(f"  Class: {s['class_name']}")
            print(f"  Teacher: {s['teacher_name']}")
            print(f"  Time: {s['start_time']} ~ {s['end_time']}")
            print(f"  Zoom ID: {s.get('zoom_meeting_id')}")
            
            # 2. Test Zoom if meeting ID exists
            z_id = s.get('zoom_meeting_id')
            if z_id:
                print(f"  Testing Zoom API for ID {z_id}...")
                try:
                    participants = zoom_mgr.get_meeting_participants(z_id, target_date=today)
                    print(f"  Zoom Participants found: {len(participants)}")
                    for p in participants[:3]: # show first 3
                        print(f"    - {p.get('name') or p.get('user_name')}")
                except Exception as ze:
                    print(f"  Zoom API Error: {ze}")
            else:
                print("  ⚠️ No Zoom Meeting ID for this schedule.")
            print("-" * 30)
            
    except Exception as e:
        print(f"Error fetching schedules: {e}")

    # 3. Check CSV contents for encoding issues
    print("\n--- CSV Encoding Check ---")
    files = ["class_groups.csv", "teacher_groups.csv", "users.csv"]
    for f in files:
        if os.path.exists(f):
            try:
                df = pd.read_csv(f, encoding='utf-8-sig')
                print(f"{f} loaded successfully (utf-8-sig). Rows: {len(df)}")
                if f == "users.csv":
                    teachers = df[df['role'] == 'teacher']
                    print(f"Teachers in CSV: {teachers['name'].tolist()}")
            except Exception as e:
                print(f"Error loading {f}: {e}")

if __name__ == "__main__":
    debug_today()

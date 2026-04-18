import sys, os
from datetime import date
sys.stdout.reconfigure(encoding='utf-8')
os.environ['PYTHONIOENCODING'] = 'utf-8'

from supabase_client import supabase_mgr
from zoom_integration import zoom_mgr

print("--- Checking Schedule C-4 ---")
resp = supabase_mgr.client.table('schedule').select('*').ilike('class_name', '%C-4%').execute()

c4_schedules = resp.data
if not c4_schedules:
    print("C-4 class not found in schedule")
    sys.exit()

for s in c4_schedules:
    print(f"Schedule: {s['class_name']} (ID: {s['id']})")
    print(f"  Zoom ID: {s.get('zoom_meeting_id')}")
    
    zoom_id = s.get('zoom_meeting_id')
    if zoom_id:
        print(f"\n--- Fetching Zoom Participants for {zoom_id} ---")
        try:
            # First, fetch without date filter to see everything
            print("1. All participants (no filter):")
            all_parts = zoom_mgr.get_meeting_participants(zoom_id, target_date="2000-01-01") # Trick to bypass the new filter somewhat, wait, the new filter drops if != filter_date.
            
            # Let's bypass the get_meeting_participants method and call API directly to debug
            token = zoom_mgr.get_access_token()
            headers = {"Authorization": f"Bearer {token}"}
            meeting_id_clean = str(zoom_id).replace(" ", "")
            
            import requests
            raw_parts = []
            
            # Metrics
            url_live = f"https://api.zoom.us/v2/metrics/meetings/{meeting_id_clean}/participants?type=live"
            resp_live = requests.get(url_live, headers=headers)
            if resp_live.status_code == 200:
                print("  Live API success")
                raw_parts.extend(resp_live.json().get('participants', []))
            else:
                print(f"  Live API error: {resp_live.status_code}")
                
            # Report
            url_past = f"https://api.zoom.us/v2/report/meetings/{meeting_id_clean}/participants"
            resp_past = requests.get(url_past, headers=headers)
            if resp_past.status_code == 200:
                print("  Report API success")
                raw_parts.extend(resp_past.json().get('participants', []))
            
            print(f"\nTotal raw participants from Zoom API: {len(raw_parts)}")
            for p in raw_parts:
                print(f"  - {p.get('name') or p.get('user_name')}: join_time={p.get('join_time')}")
                
            print("\n2. Filtered participants (today):")
from utils import get_today_kst
            filtered = zoom_mgr.get_meeting_participants(zoom_id, target_date=get_today_kst())
            for p in filtered:
                print(f"  - {p.get('name') or p.get('user_name')}: join_time={p.get('join_time')}")
                
        except Exception as e:
            print(f"Error fetching Zoom data: {e}")

    print("\n--- Current Attendance for C-4 ---")
    att = supabase_mgr.client.table('attendance') \
        .select('*, students!student_id(student_name)') \
        .eq('schedule_id', s['id']).execute()
    for a in att.data:
        sn = a.get('students', {}).get('student_name', '?')
        print(f"  {sn}: status={a['status']}, check_in={a['check_in_time']}")


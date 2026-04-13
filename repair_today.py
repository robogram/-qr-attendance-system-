import os
import pandas as pd
from supabase_client import supabase_mgr
from datetime import date, datetime, timedelta, timezone

def repair():
    target_date_str = "2026-04-11"
    print(f"--- Repairing schedules for {target_date_str} ---")
    
    # 1. Fetch current schedules for today
    try:
        res = supabase_mgr.get_schedule_for_date(target_date_str)
        print(f"Found {len(res)} existing schedules.")
        if res:
            print(f"Available columns: {list(res[0].keys())}")
        
        for s in res:
            supabase_mgr.client.table('schedule').delete().eq('id', s['id']).execute()
            print(f"  Deleted ID: {s['id']} ({s.get('class_name')})")
            
        # 2. Add fresh schedules A, B, C
        st_dt_str = f"{target_date_str}T09:30:00+09:00"
        en_dt_str = f"{target_date_str}T11:30:00+09:00"
        zoom_id = 89732348121
        
        schedules_to_add = [
            {"name": "A반 1회차", "teacher": "지진선"},
            {"name": "B반 1회차", "teacher": "전윤애"},
            {"name": "C반 1회차", "teacher": "임상희"},
        ]
        
        for item in schedules_to_add:
            record = {
                "class_name": item["name"],
                "teacher_name": item["teacher"],
                "start_time": st_dt_str,
                "end_time": en_dt_str,
                "zoom_meeting_id": str(zoom_id)
            }
            res_ins = supabase_mgr.client.table('schedule').insert(record).execute()
            if res_ins.data:
                print(f"  [SUCCESS] Created: {item['name']} for {item['teacher']}")
            else:
                print(f"  [FAILED] Creating: {item['name']}")

    except Exception as e:
        print(f"Error during repair: {e}")

if __name__ == "__main__":
    repair()

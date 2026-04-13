import os
import pandas as pd
from supabase_client import supabase_mgr
from datetime import datetime

def check_current_logic():
    print("--- Checking current logic for active schedules ---")
    
    # 1. Get today's schedules
    res = supabase_mgr.client.table('schedule').select('*').execute()
    # Filter for those starting around 16:00 KST (07:00 UTC)
    schedules = [s for s in res.data if "07:00:00" in s['start_time']]
    
    df_classes = pd.read_csv("class_groups.csv", encoding='utf-8-sig')
    df_std_groups = pd.read_csv("student_groups.csv", encoding='utf-8-sig')
    all_db_students = supabase_mgr.get_all_students()
    
    for s in schedules:
        print(f"\nSchedule: {s['class_name']} (Teacher: {s['teacher_name']})")
        session_name = s['class_name']
        
        matched_group_id = None
        for _, grp in df_classes.iterrows():
            g_name = str(grp['group_name']).strip()
            if g_name and g_name in session_name:
                matched_group_id = grp['group_id']
                print(f"  Matched to Group ID: {matched_group_id} ({g_name})")
                break
        
        if matched_group_id:
            valid_student_names = set(df_std_groups[df_std_groups['group_id'] == matched_group_id]['student_name'].tolist())
            matches = [st for st in all_db_students if st['student_name'] in valid_student_names]
            print(f"  Students for this class: {len(matches)}")
        else:
            print("  ⚠️ NO GROUP MATCHED for this session name!")

if __name__ == "__main__":
    check_current_logic()

import os
from supabase_client import supabase_mgr
from datetime import datetime
import json

def get_records():
    # 1. Find student ID for "김윤건"
    student = supabase_mgr.client.table('students').select('*').eq('student_name', '김윤건').execute()
    if not student.data:
        print("Student '김윤건' not found in database.")
        return
    
    student_id = student.data[0]['id']
    student_name = student.data[0]['student_name']
    print(f"--- Student: {student_name} ({student_id}) ---")

    # 2. Fetch all attendance records
    attendance = supabase_mgr.client.table('attendance') \
        .select('*, schedule(*)') \
        .eq('student_id', student_id) \
        .order('check_in_time', desc=False) \
        .execute()
    
    if not attendance.data:
        print("No attendance records found.")
    else:
        print(f"Total attendance records found: {len(attendance.data)}")
        for rec in attendance.data:
            check_in = rec.get('check_in_time', 'N/A')
            status = rec.get('status', 'N/A')
            type_val = rec.get('type', 'N/A')
            schedule = rec.get('schedule')
            sched_info = "No scheduled class"
            if schedule:
                sched_name = schedule.get('class_name', 'Unnamed Class')
                sched_start = schedule.get('start_time', 'N/A')
                sched_info = f"{sched_name} ({sched_start})"
            
            print(f"- Date: {check_in} | Status: {status} | Type: {type_val} | Class: {sched_info}")

    # 3. Check for specific dates if missing (optional, but good for context)
    # Based on Conversation history, check 4/4 and 4/11
    print("\n--- Summary ---")
    # If we want to be more thorough, we could fetch all schedules and check presence
    schedules = supabase_mgr.client.table('schedule').select('*').order('start_time').execute()
    att_schedule_ids = {r['schedule_id'] for r in attendance.data if r.get('schedule_id')}
    
    for s in schedules.data:
        if s['id'] not in att_schedule_ids:
            # Check if this schedule was relevant for this student's group
            # (Assuming we might filter by group if we knew it)
            pass

if __name__ == "__main__":
    get_records()

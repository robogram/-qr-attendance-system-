from supabase_client import supabase_mgr
from datetime import datetime, timezone, timedelta
import pandas as pd

def get_kim_yungeon_report():
    kst = timezone(timedelta(hours=9))
    
    # 1. Student info
    student = supabase_mgr.client.table('students').select('*').eq('student_name', '김윤건').execute()
    if not student.data:
        print("Student 김윤건 not found.")
        return
    
    s = student.data[0]
    sid = s['id']
    print(f"=== Report for {s['student_name']} (ID: {sid}) ===")
    
    # 2. Attendance records
    att_res = supabase_mgr.client.table('attendance').select('*, schedule(*)').eq('student_id', sid).execute()
    att_data = att_res.data
    
    # 3. All relevant schedules (4/4, 4/11, and others if any)
    sched_res = supabase_mgr.client.table('schedule').select('*').order('start_time').execute()
    sched_data = sched_res.data
    
    # 4. Process Attendance
    records = []
    for a in att_data:
        check_in = datetime.fromisoformat(a['check_in_time']).astimezone(kst)
        status = a['status']
        stype = a['type']
        sname = a['schedule']['class_name'] if a['schedule'] else "Unknown Class"
        records.append({
            'Date': check_in.strftime('%Y-%m-%d %H:%M'),
            'Status': status,
            'Type': stype,
            'Class': sname
        })
    
    print("\n--- Attendance History ---")
    if not records:
        print("No attendance records found.")
    else:
        df_att = pd.DataFrame(records)
        print(df_att.to_string(index=False))
    
    # 5. Check missing
    # We need to know which class this student belongs to.
    # Looking at the attendance, he attended "C반" on both 4/4 and 4/11.
    # Let's verify if there were other "C반" classes he missed.
    
    c_classes = [s for s in sched_data if 'C반' in s['class_name']]
    print("\n--- 'C반' Schedule Presence Check ---")
    att_sched_ids = {a['schedule_id'] for a in att_data if a['schedule_id']}
    
    for c in c_classes:
        start = datetime.fromisoformat(c['start_time']).astimezone(kst)
        present = "YES" if c['id'] in att_sched_ids else "NO (Absent)"
        print(f"Class: {c['class_name']} | Time: {start.strftime('%Y-%m-%d %H:%M')} | Attended: {present}")

if __name__ == "__main__":
    get_kim_yungeon_report()

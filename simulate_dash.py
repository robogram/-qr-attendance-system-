
from supabase_client import supabase_mgr
import pandas as pd
from datetime import datetime, date

def get_schedule_df():
    schedules = supabase_mgr.get_all_schedules()
    if not schedules:
        return pd.DataFrame(columns=['date', 'start', 'end', 'session'])
    data = []
    for s in schedules:
        st_dt = pd.to_datetime(s['start_time'])
        en_dt = pd.to_datetime(s['end_time'])
        data.append({
            'date': st_dt.strftime('%Y-%m-%d'),
            'start': st_dt.strftime('%H:%M'),
            'end': en_dt.strftime('%H:%M'),
            'session': s['class_name'],
            'id': s['id']
        })
    return pd.DataFrame(data)

def simulate_student_dash(student_name, group_id):
    print(f"Simulating dashboard for {student_name}, group_id={group_id}")
    
    # 1. Get Group Info (Simulate class_groups.csv load)
    # Since we can't easily read CSV here without more code, we'll assume group_id 4 is "C반"
    group_name = "C반" 
    
    # 2. Get Schedule
    df_schedule = get_schedule_df()
    print(f"Total schedules fetched: {len(df_schedule)}")
    if not df_schedule.empty:
        print(f"Unique sessions in schedule: {df_schedule['session'].unique().tolist()}")
        
        # Filtering logic from student_app.py
        df_schedule['date_obj'] = pd.to_datetime(df_schedule['date'], errors='coerce').dt.date
        group_schedule = df_schedule[df_schedule['session'].str.contains(group_name, na=False)].copy()
        print(f"Group schedule count for '{group_name}': {len(group_schedule)}")
        
        if group_schedule.empty:
            print("Try partial match (contains 'C')...")
            partial_match = df_schedule[df_schedule['session'].str.contains("C", na=False)].copy()
            print(f"Partial match count: {len(partial_match)}")

    # 3. Get Attendance
    response = supabase_mgr.client.table('attendance')\
        .select('id, check_in_time, status, type, students(student_name, qr_code_data), schedule(class_name, start_time)').execute()
    
    data = []
    if response.data:
        for r in response.data:
            s_name = r.get('students', {}).get('student_name', 'Unknown') if r.get('students') else 'Unknown'
            schedule_data = r.get('schedule', {}) or {}
            session = schedule_data.get('class_name', 'Unknown')
            data.append({
                'student_name': s_name,
                'session': session,
                'status': r['status'],
                'date': str(r['check_in_time']).split('T')[0] if r['check_in_time'] else ''
            })
    
    df_att = pd.DataFrame(data)
    print(f"Total attendance records: {len(df_att)}")
    
    student_att = df_att[df_att['student_name'].str.strip() == student_name.strip()]
    print(f"Attendance for {student_name}: {len(student_att)}")
    
    if not student_att.empty:
        match_name = group_name.replace("반", "").strip()
        group_att = student_att[student_att['session'].str.contains(match_name, na=False)]
        print(f"Group attendance for '{match_name}': {len(group_att)}")

if __name__ == "__main__":
    simulate_student_dash("김윤건", 4)

import pandas as pd
from datetime import datetime, date, timedelta
from supabase_client import supabase_mgr
import os

CLASS_GROUPS_CSV = "class_groups.csv"
TEACHER_GROUPS_CSV = "teacher_groups.csv"
USERS_CSV = "users.csv"

def generate_expected_schedules(start_date, end_date, weekdays, start_time_str, end_time_str, session_prefix):
    schedules = []
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    current_date = start_date
    session_count = 1
    while current_date <= end_date:
        if current_date.weekday() in weekdays:
            schedules.append({
                'date': current_date.isoformat(),
                'start': start_time_str,
                'end': end_time_str,
                'session_name': f"{session_prefix} {session_count}회차"
            })
            session_count += 1
        current_date += timedelta(days=1)
    return schedules

def sync_schedules():
    if not os.path.exists(CLASS_GROUPS_CSV): return print("No class_groups.csv found.")

    df_groups = pd.read_csv(CLASS_GROUPS_CSV, encoding='utf-8-sig')
    df_teacher_groups = pd.read_csv(TEACHER_GROUPS_CSV, encoding='utf-8-sig') if os.path.exists(TEACHER_GROUPS_CSV) else pd.DataFrame()
    df_users = pd.read_csv(USERS_CSV, encoding='utf-8-sig') if os.path.exists(USERS_CSV) else pd.DataFrame()
    
    # Create teacher mapping: group_id -> real_name
    teacher_map = {}
    if not df_teacher_groups.empty and not df_users.empty:
        for _, tg in df_teacher_groups.iterrows():
            # Match by username
            user_row = df_users[df_users['username'] == tg['teacher_username']]
            if not user_row.empty:
                real_name = user_row.iloc[0]['name']
                teacher_map[int(tg['group_id'])] = real_name

    # Get all existing schedules from Supabase
    existing_schedules = supabase_mgr.get_all_schedules()
    existing_map = {}
    for s in existing_schedules:
        st_dt = pd.to_datetime(s['start_time'])
        if st_dt.tzinfo:
            from datetime import timezone, timedelta
            kst = timezone(timedelta(hours=9))
            st_dt = st_dt.astimezone(kst)
        date_str = st_dt.date().isoformat()
        existing_map[(date_str, s['class_name'])] = s

    for _, group in df_groups.iterrows():
        g_id = int(group['group_id'])
        t_name = teacher_map.get(g_id, None)
        weekdays = [int(w) for w in str(group['weekdays']).split(',')]
        expected = generate_expected_schedules(
            group['start_date'], group['end_date'], weekdays, 
            group['start_time'], group['end_time'], group['group_name']
        )
        
        print(f"Checking group: {group['group_name']} (Teacher: {t_name})")
        
        for exp in expected:
            key = (exp['date'], exp['session_name'])
            st_dt_str = f"{exp['date']}T{exp['start']}:00+09:00"
            en_dt_str = f"{exp['date']}T{exp['end']}:00+09:00"
            
            if key not in existing_map:
                print(f"  [MISSING] {exp['session_name']} on {exp['date']} -> Inserting...")
                supabase_mgr.client.table('schedule').insert({
                    'class_name': exp['session_name'],
                    'start_time': st_dt_str,
                    'end_time': en_dt_str,
                    'teacher_name': t_name
                }).execute()
            else:
                s = existing_map[key]
                updates = {}
                if s['start_time'] != st_dt_str or s['end_time'] != en_dt_str:
                    updates['start_time'] = st_dt_str
                    updates['end_time'] = en_dt_str
                if s.get('teacher_name') != t_name:
                    updates['teacher_name'] = t_name
                
                if updates:
                    print(f"  [FIXING DATA] {exp['session_name']} on {exp['date']} -> Updating {list(updates.keys())}...")
                    supabase_mgr.client.table('schedule').update(updates).eq('id', s['id']).execute()

if __name__ == "__main__":
    sync_schedules()

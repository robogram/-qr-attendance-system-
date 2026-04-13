import pandas as pd
import os
import math
from supabase_client import supabase_mgr

def clean_data(df):
    """NaN 등을 None으로 처리"""
    return df.replace({math.nan: None})

def migrate_users():
    if not os.path.exists('users.csv'): return
    df = clean_data(pd.read_csv('users.csv', encoding='utf-8-sig'))
    
    # Mapping to Supabase Schema: id(UUID), username, password, role, created_at
    records_to_insert = []
    for _, row in df.iterrows():
        records_to_insert.append({
            'username': row.get('username'),
            'password': row.get('password'),
            'role': row.get('role')
        })
    
    if records_to_insert:
        try:
            response = supabase_mgr.client.table('users').insert(records_to_insert).execute()
            print(f"✅ Users migrated: {len(response.data)}")
        except Exception as e:
            print(f"❌ Error migrating users: {e}")

def migrate_students():
    if not os.path.exists('students.csv'): return {}
    df = clean_data(pd.read_csv('students.csv', encoding='utf-8-sig'))
    
    # Mapping: student_name, qr_code_data, parent_contact
    records_to_insert = []
    for _, row in df.iterrows():
        records_to_insert.append({
            'student_name': row.get('name'),
            'qr_code_data': row.get('qr_code'),
            'parent_contact': str(row.get('phone')) if row.get('phone') else None
        })
    
    student_mapping = {}
    if records_to_insert:
        try:
            response = supabase_mgr.client.table('students').insert(records_to_insert).execute()
            print(f"✅ Students migrated: {len(response.data)}")
            # Fetch inserted data to build mapping
            students = supabase_mgr.client.table('students').select('id, student_name').execute()
            student_mapping = {s['student_name']: s['id'] for s in students.data}
        except Exception as e:
            print(f"❌ Error migrating students: {e}")
            
    return student_mapping

def migrate_schedule():
    if not os.path.exists('schedule.csv'): return {}
    df = clean_data(pd.read_csv('schedule.csv', encoding='utf-8-sig'))
    
    # Mapping: class_name, teacher_name, start_time(TIMESTAMP), end_time(TIMESTAMP), zoom_meeting_id
    records_to_insert = []
    for _, row in df.iterrows():
        date_str = str(row.get('date')).strip()
        start_str = str(row.get('start')).strip()
        end_str = str(row.get('end')).strip()
        
        start_time = f"{date_str} {start_str}:00" if start_str and start_str != 'None' else None
        end_time = f"{date_str} {end_str}:00" if end_str and end_str != 'None' else None
        
        records_to_insert.append({
            'class_name': row.get('session'),
            'start_time': start_time,
            'end_time': end_time
        })
    
    schedule_mapping = {}
    if records_to_insert:
        try:
            response = supabase_mgr.client.table('schedule').insert(records_to_insert).execute()
            print(f"✅ Schedule migrated: {len(response.data)}")
            # Fetch inserted data to build mapping (by class_name and date logic, we use class_name as proxy here)
            schedules = supabase_mgr.client.table('schedule').select('id, class_name').execute()
            schedule_mapping = {s['class_name']: s['id'] for s in schedules.data}
        except Exception as e:
            print(f"❌ Error migrating schedule: {e}")
            
    return schedule_mapping

def migrate_attendance(student_mapping, schedule_mapping):
    if not os.path.exists('attendance.csv') or os.path.getsize('attendance.csv') == 0: return
    df = clean_data(pd.read_csv('attendance.csv', encoding='utf-8-sig'))
    
    # Mapping: student_id(FK), schedule_id(FK), check_in_time(TIMESTAMP), status, type
    records_to_insert = []
    for _, row in df.iterrows():
        student_name = row.get('student_name')
        session_name = row.get('session')
        source = row.get('source', 'qr')
        
        student_id = student_mapping.get(student_name)
        schedule_id = schedule_mapping.get(session_name)
        
        if not student_id or not schedule_id:
            continue # FK missing, skip
            
        attendance_type = '온라인' if source == 'zoom' else '오프라인'
        
        records_to_insert.append({
            'student_id': student_id,
            'schedule_id': schedule_id,
            'check_in_time': row.get('timestamp'),
            'status': row.get('status'),
            'type': attendance_type
        })
    
    if records_to_insert:
        try:
            response = supabase_mgr.client.table('attendance').insert(records_to_insert).execute()
            print(f"✅ Attendance migrated: {len(response.data)}")
        except Exception as e:
            print(f"❌ Error migrating attendance: {e}")

if __name__ == "__main__":
    if not supabase_mgr.client:
        print("Supabase client not initialized.")
    else:
        migrate_users()
        # Dependency resolution (Students and Schedule first)
        student_map = migrate_students()
        schedule_map = migrate_schedule()
        migrate_attendance(student_map, schedule_map)
        print("Migration process finished.")

import pandas as pd
from supabase_client import supabase_mgr
import os

def debug_report():
    print("--- Diagnostic Report Start ---")
    
    # 1. Fetch from Supabase
    print("Fetching attendance dataframe...")
    # This matches admin_app.py get_attendance_df()
    response = supabase_mgr.client.table('attendance')\
        .select('id, check_in_time, status, students(student_name, qr_code_data), schedule(class_name)').execute()
    data = []
    if response.data:
        for r in response.data:
            s_name = r.get('students', {}).get('student_name', 'Unknown') if r.get('students') else 'Unknown'
            session = r.get('schedule', {}).get('class_name', 'Unknown') if r.get('schedule') else 'Unknown'
            data.append({
                'student_name': s_name,
                'session': session,
                'status': r['status'],
                'date': str(r['check_in_time']).split('T')[0] if r['check_in_time'] else ''
            })
    df_att = pd.DataFrame(data)
    print(f"Total records in memory: {len(df_att)}")
    if not df_att.empty:
        print("Sample raw dates:", df_att['date'].unique()[:5])

    # 2. Filtering by target dates
    target_dates = ['2026-04-04', '2026-04-11', '2026-04-18', '2026-04-25']
    df_course = df_att[df_att['date'].isin(target_dates)].copy()
    print(f"Records after date filter: {len(df_course)}")
    if len(df_course) > 0:
        print(f"Filtered dates found: {df_course['date'].unique()}")

    # 3. Pivot Logic
    if not df_course.empty:
        pivot_df = df_course.pivot_table(
            index='student_name', 
            columns='date', 
            values='status', 
            aggfunc=lambda x: list(x)[0]
        ).reset_index()
        print(f"Pivot table rows (students): {len(pivot_df)}")
        print("Pivot columns:", pivot_df.columns.tolist())
    else:
        print("ALERT: df_course is empty. Filter criteria failed.")

    # 4. Name Consistency Check
    # Check if student_groups.csv names match Supabase names
    if os.path.exists('student_groups.csv'):
        df_sg = pd.read_csv('student_groups.csv', encoding='utf-8-sig')
        sg_names = set(df_sg['student_name'].tolist())
        att_names = set(df_att['student_name'].tolist())
        inter = sg_names.intersection(att_names)
        print(f"Student mapping names: {len(sg_names)}")
        print(f"Attendance student names: {len(att_names)}")
        print(f"Intersecting names (matched): {len(inter)}")
        
        if len(inter) == 0:
            print("CRITICAL: Zero overlap between student mapping and attendance records.")
            if len(att_names) > 0:
                print("Example attendance name:", repr(list(att_names)[0]))
            if len(sg_names) > 0:
                print("Example mapping name:", repr(list(sg_names)[0]))

if __name__ == "__main__":
    debug_report()

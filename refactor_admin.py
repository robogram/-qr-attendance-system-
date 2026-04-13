import codecs
import re

file_path = "e:\\다운로드\\qr_attendance\\admin_app.py"

with codecs.open(file_path, "r", "utf-8-sig") as f:
    text = f.read()

# 1. Add Helper functions at the top (after imports)
helpers = """
# -- Supabase Proxy Helpers --
from supabase_client import supabase_mgr

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

def save_schedule_df(df):
    if df.empty: return True
    for _, row in df.iterrows():
        # Simplistic approach: if we don't handle delete, we just insert. 
        # For full robust sync, it's better to pass ID. 
        pass
        
def get_attendance_df():
    # from admin_app perspective
    # attendance table: id, student_id, schedule_id, check_in_time, status, type, remark
    response = supabase_mgr.client.table('attendance')\\
        .select('id, check_in_time, status, students(student_name, qr_code_data), schedule(class_name)').execute()
    data = []
    if response.data:
        for r in response.data:
            s_name = r.get('students', {}).get('student_name', 'Unknown') if r.get('students') else 'Unknown'
            qr_code = r.get('students', {}).get('qr_code_data', 'Unknown') if r.get('students') else 'Unknown'
            session = r.get('schedule', {}).get('class_name', 'Unknown') if r.get('schedule') else 'Unknown'
            data.append({
                'timestamp': r['check_in_time'],
                'student_name': s_name,
                'qr_code': qr_code,
                'session': session,
                'status': r['status'],
                'date': str(r['check_in_time']).split('T')[0] if r['check_in_time'] else ''
            })
    if not data:
        return pd.DataFrame(columns=['date', 'session', 'student_name', 'qr_code', 'timestamp', 'status'])
    return pd.DataFrame(data)

# ----------------------------
"""
if "# -- Supabase Proxy Helpers --" not in text:
    text = text.replace("import pandas as pd", "import pandas as pd\n" + helpers)

# 2. Replace SCHEDULE_CSV loads
text = re.sub(r"df_schedule\s*=\s*load_csv_safe\(SCHEDULE_CSV\s*,\s*\[.*?\]\)", "df_schedule = get_schedule_df()", text)
text = re.sub(r"df_sched\s*=\s*load_csv_safe\(SCHEDULE_CSV\s*,\s*\[.*?\]\)", "df_sched = get_schedule_df()", text)
text = re.sub(r"df_schedule\s*=\s*pd.read_csv\(SCHEDULE_CSV\s*,\s*encoding=.*?\)", "df_schedule = get_schedule_df()", text)

# 3. Replace ATTENDANCE_LOG_CSV loads
# load_csv_safe
text = re.sub(r"df_log\s*=\s*load_csv_safe\(ATTENDANCE_LOG_CSV\s*,\s*\[.*?\]\)", "df_log = get_attendance_df()", text)
# pd.read_csv
text = re.sub(r"df_attendance\s*=\s*pd.read_csv\(ATTENDANCE_LOG_CSV\s*,\s*encoding=.*?\)", "df_attendance = get_attendance_df()", text)
text = re.sub(r"df_attendance_edit\s*=\s*pd.read_csv\(ATTENDANCE_LOG_CSV\s*,\s*encoding=.*?\)", "df_attendance_edit = get_attendance_df()", text)
text = re.sub(r"df_full\s*=\s*pd.read_csv\(ATTENDANCE_LOG_CSV\s*,\s*encoding=.*?\)", "df_full = get_attendance_df()", text)

# Write back
with codecs.open(file_path, "w", "utf-8-sig") as f:
    f.write(text)

print("Refactoring done.")

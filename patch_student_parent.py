import codecs
import re

helpers = """
# -- Supabase Proxy Helpers --
from supabase_client import supabase_mgr
import pandas as pd

def get_students_df():
    students = supabase_mgr.get_all_students()
    df = pd.DataFrame(students)
    if not df.empty:
        df = df.rename(columns={'student_name': 'name', 'qr_code_data': 'qr_code', 'parent_contact': 'phone'})
    return df if not df.empty else pd.DataFrame(columns=['name', 'qr_code', 'phone'])

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

def get_attendance_df():
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

def patch_file(filepath):
    with codecs.open(filepath, "r", "utf-8-sig") as f:
        text = f.read()

    if "# -- Supabase Proxy Helpers --" not in text:
        text = text.replace("import pandas as pd", "import pandas as pd\n" + helpers)

    # Patch load_students_cached / load_schedule_cached / load_attendance_cached bodies
    def patch_func(func_name, getter_str, text_to_patch):
        # find def func_name(): ... return df
        pattern = rf"(def {func_name}\(.*?\):\n(?:(?: {4}|\t).*?\n)*)"
        match = re.search(pattern, text_to_patch)
        if match:
            new_func = f"def {func_name}():\n    return {getter_str}\n\n"
            return text_to_patch.replace(match.group(1), new_func)
        return text_to_patch

    text = patch_func("load_students_cached", "get_students_df()", text)
    text = patch_func("load_schedule_cached", "get_schedule_df()", text)
    text = patch_func("load_attendance_cached", "get_attendance_df()", text)

    # For student_app.py which might use load_csv_safe(ATTENDANCE_LOG_CSV...)
    text = re.sub(r"load_csv_safe\(ATTENDANCE_LOG_CSV\s*,\s*\[.*?\]\)", "get_attendance_df()", text)
    text = re.sub(r"load_csv_safe\(SCHEDULE_CSV\s*,\s*\[.*?\]\)", "get_schedule_df()", text)
    text = re.sub(r"load_csv_safe\(STUDENTS_CSV\s*,\s*\[.*?\]\)", "get_students_df()", text)

    with codecs.open(filepath, "w", "utf-8-sig") as f:
        f.write(text)
    print(f"Patched {filepath}")

patch_file("e:\\다운로드\\qr_attendance\\parent_app.py")
patch_file("e:\\다운로드\\qr_attendance\\student_app.py")

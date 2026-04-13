from supabase_client import supabase_mgr
from datetime import datetime, timezone, timedelta

def final_check():
    kst = timezone(timedelta(hours=9))
    student = supabase_mgr.client.table('students').select('*').eq('student_name', '김윤건').execute()
    if not student.data:
        print("Student not found")
        return
    
    sid = student.data[0]['id']
    att = supabase_mgr.client.table('attendance').select('*, schedule(*)').eq('student_id', sid).order('check_in_time').execute()
    
    print(f"Student: 김윤건")
    for a in att.data:
        t = datetime.fromisoformat(a['check_in_time']).astimezone(kst)
        status = a['status']
        ctype = a['type']
        cname = a['schedule']['class_name'] if a['schedule'] else "Unknown"
        print(f"- {t.strftime('%Y-%m-%d %H:%M')} | {cname} | {status} | {ctype}")

if __name__ == "__main__":
    final_check()

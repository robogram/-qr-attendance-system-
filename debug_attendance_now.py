import sys, json

from supabase_client import supabase_mgr

sid = '24388f06-96b4-4f4c-9c9c-262cb3b9c4ba'

# 1. All attendance for this schedule
resp = supabase_mgr.client.table('attendance') \
    .select('*, students!student_id(student_name)') \
    .eq('schedule_id', sid) \
    .execute()

result = {"schedule_id": sid, "attendance": []}
for a in resp.data:
    sn = a.get('students', {}).get('student_name', '?')
    result["attendance"].append({
        "att_id": a['id'],
        "student_id": a['student_id'],
        "student_name": sn,
        "status": a['status'],
        "type": a.get('type'),
        "check_in": a['check_in_time'],
        "remark": a.get('remark','')
    })

# 2. All A-4 schedules
resp2 = supabase_mgr.client.table('schedule').select('*') \
    .ilike('class_name', '%A-4%').execute()
result["all_a4_schedules"] = []
for s in resp2.data:
    att_r = supabase_mgr.client.table('attendance').select('id') \
        .eq('schedule_id', s['id']).execute()
    result["all_a4_schedules"].append({
        "sid": s['id'],
        "class_name": s['class_name'],
        "start_time": s['start_time'],
        "group_id": s.get('group_id'),
        "attendance_count": len(att_r.data)
    })

with open('debug_result.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print("DONE - saved to debug_result.json")

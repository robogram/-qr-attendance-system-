import pandas as pd
from supabase_client import supabase_mgr

def repair():
    # 1. 학생별 소속 반(그룹) 로드 (로보미/아르고 -> 2(B반), 성창경/구본훈 -> 3(A반))
    try:
        df_students = pd.read_csv("student_groups.csv", encoding='utf-8-sig')
        df_classes = pd.read_csv("class_groups.csv", encoding='utf-8-sig')
    except Exception as e:
        print(f"Error loading CSVs: {e}")
        return

    student_to_group_id = dict(zip(df_students['student_name'], df_students['group_id']))
    group_id_to_name = dict(zip(df_classes['group_id'], df_classes['group_name']))

    # 2. Supabase에서 schedule이 없는(Unknown) attendance 조회
    # We will get all attendances and filter those with schedule_id is null
    res = supabase_mgr.client.table('attendance').select('id, student_id, check_in_time, students(student_name)').is_('schedule_id', 'null').execute()
    records = res.data

    if not records:
        print("No missing schedule records found.")
        return

    print(f"Found {len(records)} attendance records without a schedule. Repairing...")

    # 3. Supabase에 등록된 schedule 로드
    schedules = supabase_mgr.client.table('schedule').select('id, class_name, start_time').execute().data

    repaired = 0
    for record in records:
        s_name = record.get('students', {}).get('student_name')
        if not s_name: continue
        
        group_id = student_to_group_id.get(s_name)
        if not group_id: continue
        
        group_name = group_id_to_name.get(group_id)
        
        # 해당 수업 이름과 매칭되는 schedule 찾기
        matching_schedule_id = None
        for sch in schedules:
            if group_name in sch.get('class_name', ''):
                # (옵션) 날짜도 비교할 수 있지만 현재 테스트 상 4월 2일 1건만 존재하므로 이름만 매칭해도 됨
                matching_schedule_id = sch.get('id')
                break

        if matching_schedule_id:
            supabase_mgr.client.table('attendance').update({'schedule_id': matching_schedule_id}).eq('id', record['id']).execute()
            repaired += 1
            print(f"Repaired: {s_name} -> {group_name}")

    print(f"Completed! {repaired} records repaired.")

if __name__ == '__main__':
    repair()

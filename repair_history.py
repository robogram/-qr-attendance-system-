import os
from supabase_client import supabase_mgr
from datetime import datetime, date, timezone, timedelta

def repair_data():
    kst = timezone(timedelta(hours=9))
    
    print("--- Repairing 4/4 (April 4th) Schedules ---")
    # 4/4 일정이 삭제되어 출석 기록이 'Unknown'이 된 상태
    # A반(09:30), B반(14:00), C반(16:00) 일정을 다시 생성해줌
    slots = [
        ("A반", "09:30", "11:30", "임상희"),
        ("B반", "14:00", "16:00", "유자남"),
        ("C반", "16:00", "18:00", "전윤애")
    ]
    
    new_schedule_ids = {}
    for name, start, end, teacher in slots:
        st_str = f"2026-04-04T{start}:00+09:00"
        en_str = f"2026-04-04T{end}:00+09:00"
        
        # 중복 체크
        existing = supabase_mgr.client.table('schedule')\
            .select('id')\
            .eq('class_name', name)\
            .eq('start_time', st_str)\
            .execute()
        
        if not existing.data:
            res = supabase_mgr.client.table('schedule').insert({
                'class_name': name,
                'start_time': st_str,
                'end_time': en_str,
                'teacher_name': teacher
            }).execute()
            if res.data:
                print(f"Created 4/4 schedule: {name}")
                new_schedule_ids[name] = res.data[0]['id']
        else:
            new_schedule_ids[name] = existing.data[0]['id']

    # 4/4 출석 기록 re-linking (시간대에 맞게)
    print("Re-linking 4/4 attendance records...")
    att_44 = supabase_mgr.client.table('attendance')\
        .select('*')\
        .gte('check_in_time', '2026-04-04T00:00:00')\
        .lt('check_in_time', '2026-04-05T00:00:00')\
        .is_('schedule_id', 'null')\
        .execute()
    
    for r in att_44.data:
        check_in = datetime.fromisoformat(r['check_in_time'].replace('Z', '+00:00')).astimezone(kst)
        target_id = None
        if check_in.hour < 12: target_id = new_schedule_ids.get("A반")
        elif 12 <= check_in.hour < 15: target_id = new_schedule_ids.get("B반")
        else: target_id = new_schedule_ids.get("C반")
        
        if target_id:
            supabase_mgr.client.table('attendance').update({'schedule_id': target_id}).eq('id', r['id']).execute()

    print("\n--- Repairing 4/11 (Today) Missing Zoom Participants ---")
    # 4/11 줌 기록 중 누락된 사람들을 출석부에도 추가 (상호 보정)
    # 이미 'admin_app.py'에 추가했으므로, 여기서는 줌 participants 리스트를 직접 가져와서 누락분만 보충
    from zoom_integration import zoom_mgr
    target_date = date(2026, 4, 11)
    zoom_p = zoom_mgr.get_meeting_participants("89732348121", target_date=target_date)
    
    # 현재 Supabase 출석 리스트
    att_11 = supabase_mgr.client.table('attendance')\
        .select('*, students(student_name)')\
        .gte('check_in_time', '2026-04-11T00:00:00')\
        .lt('check_in_time', '2026-04-12T00:00:00')\
        .execute()
    existing_names = { r['students']['student_name'] for r in att_11.data if r.get('students') }
    
    for p in zoom_p:
        name = (p.get('name') or p.get('user_name')).strip()
        # 특수 문자 제거 매칭 (예: "A_홍길동" -> "홍길동")
        clean_name = name.split('_')[-1].split(' ')[-1]
        
        if clean_name not in existing_names and len(clean_name) >= 2:
            # 학생 정보 찾기
            std_res = supabase_mgr.client.table('students').select('id').ilike('student_name', f"%{clean_name}%").execute()
            if std_res.data:
                std_id = std_res.data[0]['id']
                # 일정 찾기 (가장 가까운 시간)
                sched_res = supabase_mgr.client.table('schedule')\
                    .select('id')\
                    .gte('start_time', '2026-04-11T00:00:00')\
                    .lt('start_time', '2026-04-12T00:00:00')\
                    .execute()
                
                if sched_res.data:
                    sched_id = sched_res.data[0]['id'] # 대략 첫 번째 일정에 배정 (사용자가 나중에 수정 가능)
                    supabase_mgr.client.table('attendance').insert({
                        'student_id': std_id,
                        'schedule_id': sched_id,
                        'check_in_time': p['join_time'],
                        'status': '출석',
                        'type': 'Zoom(복구)'
                    }).execute()
                    print(f"Recovered attendance for {clean_name} (Zoom)")

    print("Repair complete.")

if __name__ == "__main__":
    repair_data()

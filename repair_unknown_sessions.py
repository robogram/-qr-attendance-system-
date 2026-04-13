import os
from supabase_client import supabase_mgr
from datetime import datetime, timezone, timedelta

def repair_unknowns():
    print("--- Repairing Unknown Session Links (4/11) ---")
    
    kst = timezone(timedelta(hours=9))
    target_date = "2026-04-11"
    
    # 4/11의 고정된 일정 ID들 가져오기
    sched_res = supabase_mgr.client.table('schedule')\
        .select('id, class_name, start_time')\
        .gte('start_time', f"{target_date}T00:00:00")\
        .lt('start_time', f"{target_date}T23:59:59")\
        .execute()
    
    # schedule_map: "A반" -> id, "B반" -> id, "C반" -> id
    schedule_map = {}
    for s in sched_res.data:
        name = s['class_name']
        schedule_map[name] = s['id']
    
    print(f"Schedules found for {target_date}: {schedule_map}")

    # schedule_id가 None인 4/11 출석 기록 조회
    att_res = supabase_mgr.client.table('attendance')\
        .select('id, check_in_time')\
        .gte('check_in_time', f"{target_date}T00:00:00")\
        .lt('check_in_time', f"{target_date}T23:59:59")\
        .execute()
    
    count = 0
    for r in att_res.data:
        # 이미 연결된 경우라도 schedule_id가 None이거나 혹시 잘못 연결된 경우 재판단 가능 (여기서는 None만 처리)
        # 위 쿼리에서 is_('schedule_id', 'null') 을 쓰지 않은 이유는 전체를 검수하기 위함
        
        # 다시 쿼리해서 schedule_id 확인
        curr = supabase_mgr.client.table('attendance').select('schedule_id').eq('id', r['id']).execute()
        if curr.data and curr.data[0]['schedule_id'] is not None:
             continue
             
        # 시간 기반 판정
        dt = datetime.fromisoformat(r['check_in_time'].replace('Z', '+00:00')).astimezone(kst)
        hour = dt.hour
        
        target_class = None
        if hour < 12: 
            target_class = "A반"
        elif 12 <= hour < 15: 
            target_class = "B반"
        else: 
            target_class = "C반"
            
        target_id = schedule_map.get(target_class)
        if target_id:
            print(f"Re-linking ID {r['id']} (Time: {dt.strftime('%H:%M:%S')}) -> {target_class}")
            supabase_mgr.client.table('attendance').update({'schedule_id': target_id}).eq('id', r['id']).execute()
            count += 1

    print(f"Repair complete. {count} records updated.")

if __name__ == "__main__":
    repair_unknowns()

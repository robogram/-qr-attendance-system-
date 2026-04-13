from supabase_client import supabase_mgr
from datetime import datetime, date, timedelta

def create_future_schedules():
    # A반, B반, C반의 4/18, 4/25 일정을 생성합니다.
    target_dates = ['2026-04-18', '2026-04-25']
    slots = [
        ("A반", "09:30", "11:30", "임상희"),
        ("B반", "14:00", "16:00", "유자남"),
        ("C반", "16:00", "18:00", "전윤애")
    ]
    
    for date_str in target_dates:
        for name, start, end, teacher in slots:
            st_str = f"{date_str}T{start}:00+09:00"
            en_str = f"{date_str}T{end}:00+09:00"
            
            # 중복 체크
            existing = supabase_mgr.client.table('schedule')\
                .select('id')\
                .eq('class_name', name)\
                .eq('start_time', st_str)\
                .execute()
            
            if not existing.data:
                supabase_mgr.client.table('schedule').insert({
                    'class_name': name,
                    'start_time': st_str,
                    'end_time': en_str,
                    'teacher_name': teacher
                }).execute()
                print(f"Created schedule: {name} on {date_str}")
            else:
                print(f"Schedule already exists: {name} on {date_str}")

if __name__ == "__main__":
    create_future_schedules()

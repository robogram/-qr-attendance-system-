import os
import pandas as pd
from supabase_client import supabase_mgr
from datetime import datetime, timezone, timedelta

def sync_data():
    kst = timezone(timedelta(hours=9))
    excel_path = '출석부_최종본_2026-04-11확정.xlsx'
    
    if not os.path.exists(excel_path):
        print(f"Error: Excel file not found: {excel_path}")
        return

    print("--- 1. Cleaning up Existing Data ---")
    # Delete all attendance records (Warning: This is destructive as requested)
    try:
        # Attendance has foreign keys to schedules and students
        supabase_mgr.client.table('attendance').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        print("Attendance records cleared.")
        
        # Delete all schedules
        supabase_mgr.client.table('schedule').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        print("Schedules cleared.")
    except Exception as e:
        print(f"Error during cleanup: {e}")
        return

    print("\n--- 2. Initializing New Schedules (09:30-11:30) ---")
    dates = ["2026-04-04", "2026-04-11", "2026-04-18", "2026-04-25"]
    classes = [
        {"name": "A반", "teacher": "임상희"},
        {"name": "B반", "teacher": "유자남"},
        {"name": "C반", "teacher": "전윤애"}
    ]
    
    schedule_map = {} # (date, class_name) -> schedule_id
    
    for d_str in dates:
        for c in classes:
            start_time = f"{d_str}T09:30:00+09:00"
            end_time = f"{d_str}T11:30:00+09:00"
            
            res = supabase_mgr.client.table('schedule').insert({
                "class_name": c["name"],
                "teacher_name": c["teacher"],
                "start_time": start_time,
                "end_time": end_time
            }).execute()
            
            if res.data:
                sid = res.data[0]['id']
                schedule_map[(d_str, c["name"])] = sid
                print(f"Created schedule: {c['name']} on {d_str} (ID: {sid})")

    print("\n--- 3. Mapping Students ---")
    all_students = supabase_mgr.client.table('students').select('id, student_name').execute()
    student_map = {s['student_name']: s['id'] for s in all_students.data}
    print(f"Mapped {len(student_map)} students from database.")

    print("\n--- 4. Importing Attendance from Excel ---")
    for sheet in ['A반', 'B반', 'C반']:
        print(f"\nProcessing Sheet: {sheet}")
        try:
            df = pd.read_excel(excel_path, sheet_name=sheet, header=1)
            # Correct columns mapping based on research
            # Col 0: 이름, Col 2: 2026-04-04, Col 3: 2026-04-11
            
            # Clean up column names (sometimes they have spaces or weird characters)
            df.columns = [str(c).strip() for c in df.columns]
            
            target_dates = ["2026-04-04", "2026-04-11"]
            
            for index, row in df.iterrows():
                name = str(row.get('이름', '')).strip()
                if not name or name == 'nan' or '메모' in name or '합계' in name:
                    continue
                
                std_id = student_map.get(name)
                if not std_id:
                    print(f"Student '{name}' not found in DB. Skipping.")
                    continue
                
                for d_str in target_dates:
                    status_raw = str(row.get(d_str, '')).strip()
                    if status_raw in ['출석', '결석']:
                        sched_id = schedule_map.get((d_str, sheet))
                        if not sched_id:
                            continue
                        
                        # Use 09:30 as default check-in time for records
                        check_in = f"{d_str}T09:30:00+09:00"
                        
                        supabase_mgr.client.table('attendance').insert({
                            "student_id": std_id,
                            "schedule_id": sched_id,
                            "check_in_time": check_in,
                            "status": status_raw,
                            "type": "오프라인"
                        }).execute()

                        # print(f"Synced {name} on {d_str} -> {status_raw}")
            
            print(f"Finished importing {sheet}")
        except Exception as e:
            print(f"Error processing sheet {sheet}: {e}")


    print("\n--- Cleanup and Sync Complete ---")

if __name__ == "__main__":
    sync_data()

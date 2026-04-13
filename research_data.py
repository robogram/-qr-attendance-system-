from supabase_client import supabase_mgr
from datetime import datetime, timezone, timedelta
import pandas as pd
import os

def research():
    kst = timezone(timedelta(hours=9))
    
    # 1. Schedules
    sched_res = supabase_mgr.client.table('schedule').select('*').order('start_time').execute()
    print("--- Current Schedules ---")
    for s in sched_res.data:
        st = datetime.fromisoformat(s['start_time']).astimezone(kst)
        print(f"ID: {s['id']} | {s['class_name']} | {st.strftime('%Y-%m-%d %H:%M')} | Teacher: {s['teacher_name']}")
    
    # 2. Attendance count
    att_res = supabase_mgr.client.table('attendance').select('id', count='exact').execute()
    print(f"\nTotal Attendance Records: {att_res.count}")
    
    # 3. Students count
    std_res = supabase_mgr.client.table('students').select('id', count='exact').execute()
    print(f"Total Students: {std_res.count}")

    # 4. Check Excel sheets content
    excel_path = '출석부_최종본_2026-04-11확정.xlsx'
    if os.path.exists(excel_path):
        xl = pd.ExcelFile(excel_path)
        print(f"\nExcel Sheets: {xl.sheet_names}")
        for sheet in ['A반', 'B반', 'C반']:
            if sheet in xl.sheet_names:
                df = pd.read_excel(excel_path, sheet_name=sheet)
                print(f"Sheet {sheet} columns: {list(df.columns[:10])}")
                # Print first few names for matching
                # Usually name is in the first column or second row
                print(f"Sheet {sheet} sample names: {df.iloc[1:5, 0].values}")

if __name__ == "__main__":
    research()

from supabase_client import supabase_mgr
import pandas as pd

try:
    schedules = supabase_mgr.get_all_schedules()
    if not schedules:
        print("No schedules found in Supabase.")
    else:
        df = pd.DataFrame(schedules)
        # Convert times to KST for readability
        df['start_time'] = pd.to_datetime(df['start_time']).dt.tz_convert('Asia/Seoul')
        df['end_time'] = pd.to_datetime(df['end_time']).dt.tz_convert('Asia/Seoul')
        print(df[['id', 'class_name', 'start_time', 'teacher_name']])
except Exception as e:
    print(f"Error: {e}")

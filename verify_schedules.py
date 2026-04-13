
from supabase_client import supabase_mgr
import pandas as pd

def check_schedules():
    print("Checking schedule records in Supabase...")
    schedules = supabase_mgr.get_all_schedules()
    if not schedules:
        print("No schedules found.")
        return
        
    df = pd.DataFrame(schedules)
    print(f"Total schedules: {len(df)}")
    print("\nunique sessions (class_name):")
    for name in df['class_name'].unique():
        print(f"'{name}' (hex: {name.encode('utf-8').hex()})")
        
    print("\nSample records:")
    print(df[['id', 'class_name', 'start_time']].head(10))

if __name__ == "__main__":
    check_schedules()

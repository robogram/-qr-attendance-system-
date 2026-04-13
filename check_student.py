
from supabase_client import supabase_mgr
import pandas as pd

def check_student_record(student_name):
    print(f"Searching for attendance records for '{student_name}'...")
    response = supabase_mgr.client.table('attendance')\
        .select('id, check_in_time, status, students(student_name), schedule(class_name)')\
        .execute()
    
    if not response.data:
        print("No records in table.")
        return
        
    df = pd.DataFrame(response.data)
    # Extract student name
    df['s_name'] = df['students'].apply(lambda x: x.get('student_name') if x else 'Unknown')
    df['c_name'] = df['schedule'].apply(lambda x: x.get('class_name') if x else 'Unknown')
    
    matches = df[df['s_name'].str.strip() == student_name.strip()]
    print(f"Found {len(matches)} records for {student_name}.")
    for _, row in matches.iterrows():
        print(f"  Class: {row['c_name']}, Time: {row['check_in_time']}, Status: {row['status']}")

    if matches.empty:
        print("Available student names in attendance table (unique):")
        print(df['s_name'].unique().tolist())

if __name__ == "__main__":
    check_student_record("이로운")


from supabase_client import supabase_mgr
import pandas as pd

def check_attendance():
    print("Checking attendance records in Supabase...")
    # Get attendance with student name and schedule name
    response = supabase_mgr.client.table('attendance').select('id, check_in_time, status, student_id, schedule_id, students(student_name), schedule(class_name)').execute()
    
    if not response.data:
        print("No attendance records found.")
        return
        
    df = pd.DataFrame(response.data)
    print(f"Total records: {len(df)}")
    
    # Check for null students or schedules
    null_students = df[df['students'].isna()]
    null_schedules = df[df['schedule'].isna()]
    
    if not null_students.empty:
        print(f"Warning: {len(null_students)} records have missing student info.")
    if not null_schedules.empty:
        print(f"Warning: {len(null_schedules)} records have missing schedule info.")
        
    # Sample records
    print("\nSample records:")
    for _, row in df.head(5).iterrows():
        s_name = row['students'].get('student_name') if row['students'] else 'N/A'
        c_name = row['schedule'].get('class_name') if row['schedule'] else 'N/A'
        print(f"ID: {row['id']}, Student: {s_name}, Class: {c_name}, Status: {row['status']}, Time: {row['check_in_time']}")

    # Check specifically for Kim Yun-geon
    kim = df[df['students'].apply(lambda x: x.get('student_name') == '김윤건' if x else False)]
    print(f"\nRecords for 김윤건: {len(kim)}")
    for _, row in kim.iterrows():
        c_name = row['schedule'].get('class_name') if row['schedule'] else 'N/A'
        print(f"  Class: {c_name}, Date: {row['check_in_time']}, Status: {row['status']}")

if __name__ == "__main__":
    check_attendance()

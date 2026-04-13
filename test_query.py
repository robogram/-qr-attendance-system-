
from supabase_client import supabase_mgr
import pandas as pd

def test_app_query():
    print("Testing the exact query used in student_app.py...")
    try:
        response = supabase_mgr.client.table('attendance')\
            .select('id, check_in_time, status, type, students(student_name, qr_code_data), schedule(class_name, start_time)').execute()
        
        print(f"Response status: {response.status_code if hasattr(response, 'status_code') else 'N/A'}")
        if not response.data:
            print("Response data is EMPTY!")
            # Check for errors
            if hasattr(response, 'error') and response.error:
                print(f"Error: {response.error}")
        else:
            print(f"Fetched {len(response.data)} records.")
            sample = response.data[0]
            print(f"Sample structure: {sample.keys()}")
            print(f"Sample students: {sample.get('students')}")
            print(f"Sample schedule: {sample.get('schedule')}")
            
    except Exception as e:
        print(f"Query CRASHED: {e}")

if __name__ == "__main__":
    test_app_query()

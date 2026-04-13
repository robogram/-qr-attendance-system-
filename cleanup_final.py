import os
from supabase_client import supabase_mgr
from datetime import date

def clean_all_corrupted_schedules():
    print("--- Cleaning all corrupted schedule names in Supabase ---")
    try:
        res = supabase_mgr.client.table('schedule').select('*').execute()
        for s in res.data:
            name = s.get('class_name', '')
            teacher = s.get('teacher_name', '')
            updates = {}
            
            # Map corrupted characters to real ones if possible
            if 'A' in name: updates['class_name'] = name.replace('A', 'A반')
            elif 'B' in name: updates['class_name'] = name.replace('B', 'B반')
            elif 'C' in name: updates['class_name'] = name.replace('C', 'C반')
            
            if 'ӻ' in teacher: updates['teacher_name'] = '임상희'
            elif '' in teacher and len(teacher) == 1: updates['teacher_name'] = '전윤애' # Assuming single corrupted char is her name
            
            if updates:
                print(f"Updating ID {s['id']}: {updates}")
                supabase_mgr.client.table('schedule').update(updates).eq('id', s['id']).execute()
        
        print("Cleanup complete.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    clean_all_corrupted_schedules()

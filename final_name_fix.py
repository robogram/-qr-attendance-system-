import os
from supabase_client import supabase_mgr

def strict_cleanup():
    print("--- Strict Schedule Name Cleanup ---")
    res = supabase_mgr.client.table('schedule').select('id, class_name').execute()
    
    for row in res.data:
        old_name = row['class_name']
        new_name = None
        
        # 'A', 'B', 'C'가 포함된 경우 각각 고정된 이름으로 변경
        if 'A' in old_name.upper():
            new_name = "A반"
        elif 'B' in old_name.upper():
            new_name = "B반"
        elif 'C' in old_name.upper():
            new_name = "C반"
            
        if new_name and old_name != new_name:
            print(f"Fixing: {old_name} -> {new_name} (ID: {row['id']})")
            supabase_mgr.client.table('schedule').update({'class_name': new_name}).eq('id', row['id']).execute()

    print("Cleanup complete.")

if __name__ == "__main__":
    strict_cleanup()

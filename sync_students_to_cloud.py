import pandas as pd
from supabase_client import supabase_mgr
import os

def sync_student_groups():
    print("🚀 Starting Student Group Synchronization...")
    
    # 1. Load local CSVs
    class_groups_csv = "class_groups.csv"
    student_groups_csv = "student_groups.csv"
    
    if not os.path.exists(class_groups_csv) or not os.path.exists(student_groups_csv):
        print("❌ Error: Missing local CSV files (class_groups.csv or student_groups.csv)")
        return

    df_local_classes = pd.read_csv(class_groups_csv, encoding='utf-8-sig')
    df_local_students = pd.read_csv(student_groups_csv, encoding='utf-8-sig')
    
    # Map local group_id to group_name
    local_id_to_name = {row['group_id']: row['group_name'] for _, row in df_local_classes.iterrows()}
    
    # 2. Get Supabase group mappings
    print("📡 Fetching Supabase class groups...")
    supabase_groups = supabase_mgr.client.table('class_groups').select('id, group_name').execute().data
    name_to_supabase_id = {g['group_name']: g['id'] for g in supabase_groups}
    
    print(f"✅ Supabase Groups found: {list(name_to_supabase_id.keys())}")

    # 3. Update students in Supabase
    print("📝 Updating student group assignments...")
    updated_count = 0
    errors = 0
    
    for _, row in df_local_students.iterrows():
        name = row['student_name']
        local_gid = row['group_id']
        group_name = local_id_to_name.get(local_gid)
        
        if not group_name:
            print(f"⚠️ Warning: No group name found for local ID {local_gid} (Student: {name})")
            continue
            
        supabase_gid = name_to_supabase_id.get(group_name)
        if not supabase_gid:
            print(f"⚠️ Warning: Group '{group_name}' not found in Supabase (Student: {name})")
            continue
            
        # Update Supabase
        try:
            res = supabase_mgr.client.table('students') \
                .update({'class_group_id': supabase_gid}) \
                .eq('student_name', name) \
                .execute()
            
            if res.data:
                print(f"✅ Updated {name}: {group_name} (Supabase ID: {supabase_gid})")
                updated_count += 1
            else:
                print(f"❓ No student found in Supabase with name '{name}'")
        except Exception as e:
            print(f"❌ Error updating {name}: {e}")
            errors += 1

    print(f"\n✨ Synchronization Complete!")
    print(f"   - Total Updated: {updated_count}")
    print(f"   - Errors: {errors}")

if __name__ == "__main__":
    sync_student_groups()

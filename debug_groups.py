from supabase_client import supabase_mgr

# Check class groups
resp = supabase_mgr.client.table('class_groups').select('*').execute()
print("--- Class Groups ---")
for g in resp.data:
    print(g)
    
print("\n--- Students in C-4 ---")
resp2 = supabase_mgr.client.table('class_groups').select('*').ilike('group_name', '%C-4%').execute()
if resp2.data:
    c4_id = resp2.data[0]['id']
    sts = supabase_mgr.client.table('students').select('*').eq('class_group_id', c4_id).execute()
    for s in sts.data:
        print(s['student_name'])
else:
    print("Cannot find C-4 group")

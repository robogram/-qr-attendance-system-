import json
from supabase_client import supabase_mgr

def try_fetch(column):
    try:
        res = supabase_mgr.client.table('students').select(f'id,{column}').limit(1).execute()
        return True, res.data
    except Exception as e:
        return False, str(e)

print("Trying class_group_id:", try_fetch('class_group_id'))
print("Trying group_id:", try_fetch('group_id'))
print("Trying no group:", try_fetch('qr_code_data'))

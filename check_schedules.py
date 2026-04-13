from supabase_client import supabase_mgr

schedules = supabase_mgr.client.table('schedule').select('id,class_name,start_time,end_time').execute().data
for s in schedules:
    print(s['id'], s['class_name'], s['start_time'], s['end_time'])

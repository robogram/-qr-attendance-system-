import pandas as pd
from datetime import datetime, date, timedelta
from supabase_client import supabase_mgr
import os
import sys

# Set stdout to utf-8 to avoid encoding errors on Windows
# sys.stdout.reconfigure(encoding='utf-8') # Only for newer Python

CLASS_GROUPS_CSV = "class_groups.csv"

def sync_schedules():
    if not os.path.exists(CLASS_GROUPS_CSV):
        print(f"[ERROR] {CLASS_GROUPS_CSV} not found.")
        return

    try:
        df_groups = pd.read_csv(CLASS_GROUPS_CSV, encoding='utf-8-sig')
    except Exception as e:
        print(f"[ERROR] Loading CSV: {e}")
        return

    if df_groups.empty:
        print("[INFO] No class groups to sync.")
        return

    sync_count = 0
    print(f"[INFO] Syncing {len(df_groups)} class groups to Supabase...")

    for _, group in df_groups.iterrows():
        try:
            group_name = group['group_name']
            weekdays = [int(w) for w in str(group['weekdays']).split(',')]
            start_date = pd.to_datetime(group['start_date']).date()
            end_date = pd.to_datetime(group['end_date']).date()
            start_time = group['start_time']
            end_time = group['end_time']

            current_date = start_date
            while current_date <= end_date:
                if current_date.weekday() in weekdays:
                    date_str = current_date.isoformat()
                    # Compose KST ISO strings (+09:00)
                    st_dt_str = f"{date_str}T{start_time}:00+09:00"
                    en_dt_str = f"{date_str}T{end_time}:00+09:00"

                    # Check if already exists in Supabase to avoid duplicates
                    # We match by class_name and start_time
                    existing = supabase_mgr.client.table('schedule').select('id')\
                        .eq('class_name', group_name)\
                        .eq('start_time', st_dt_str).execute()

                    if not existing.data:
                        supabase_mgr.client.table('schedule').insert({
                            'class_name': group_name,
                            'start_time': st_dt_str,
                            'end_time': en_dt_str
                        }).execute()
                        sync_count += 1
                        print(f"[SUCCESS] Created: {group_name} on {date_str}")
                    else:
                        print(f"[SKIP] Already exists: {group_name} on {date_str}")
                current_date += timedelta(days=1)
        except Exception as e:
            print(f"[ERROR] Syncing group {group.get('group_name')}: {e}")

    print(f"[FINISH] Sync completed! {sync_count} schedules created.")

if __name__ == "__main__":
    sync_schedules()

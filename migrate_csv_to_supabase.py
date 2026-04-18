import pandas as pd
import os
from supabase_client import supabase_mgr
from config import CLASS_GROUPS_CSV, STUDENT_GROUPS_CSV, TEACHER_GROUPS_CSV

def migrate_to_supabase():
    print(">>> Starting migration to Supabase...")

    # 1. Class Groups
    if os.path.exists(CLASS_GROUPS_CSV):
        print(f"--- Migrating {CLASS_GROUPS_CSV} ---")
        df = pd.read_csv(CLASS_GROUPS_CSV, encoding='utf-8-sig')
        for _, row in df.iterrows():
            data = row.to_dict()
            # pandas na -> None
            data = {k: (None if pd.isna(v) else v) for k, v in data.items()}
            res = supabase_mgr.upsert_class_group(data)
            if res:
                print(f"[OK] Migrated group: {data['group_name']}")
            else:
                print(f"[Error] Failed to migrate group: {data['group_name']}")

    # 2. Student Groups
    if os.path.exists(STUDENT_GROUPS_CSV):
        print(f"--- Migrating {STUDENT_GROUPS_CSV} ---")
        df = pd.read_csv(STUDENT_GROUPS_CSV, encoding='utf-8-sig')
        for _, row in df.iterrows():
            data = row.to_dict()
            data = {k: (None if pd.isna(v) else v) for k, v in data.items()}
            res = supabase_mgr.insert_student_group(data)
            if res:
                print(f"[OK] Migrated student mapping: {data['student_name']} -> {data['group_id']}")

    # 3. Teacher Groups
    if os.path.exists(TEACHER_GROUPS_CSV):
        print(f"--- Migrating {TEACHER_GROUPS_CSV} ---")
        df = pd.read_csv(TEACHER_GROUPS_CSV, encoding='utf-8-sig')
        for _, row in df.iterrows():
            data = row.to_dict()
            data = {k: (None if pd.isna(v) else v) for k, v in data.items()}
            # Remove UUID if exists to let Supabase generate new one, or keep if standard
            if 'id' in data: del data['id'] 
            res = supabase_mgr.insert_teacher_group(data)
            if res:
                print(f"[OK] Migrated teacher mapping: {data['teacher_username']} -> {data['group_id']}")

    print("Migration completed!")

if __name__ == "__main__":
    migrate_to_supabase()

import pandas as pd
from supabase_client import supabase_mgr
import os

def test_matching():
    # Simulate get_students_for_schedule fallback logic
    session_name = "A반 1회차"
    
    try:
        df_classes = pd.read_csv("class_groups.csv", encoding='utf-8-sig')
        df_std_groups = pd.read_csv("student_groups.csv", encoding='utf-8-sig')
        all_db_students = supabase_mgr.get_all_students()
        
        print(f"Loaded {len(df_classes)} classes, {len(df_std_groups)} student-group mappings, {len(all_db_students)} students from DB.")
        
        matched_group_id = None
        for _, grp in df_classes.iterrows():
            g_name = str(grp['group_name']).strip()
            if g_name and g_name in session_name:
                matched_group_id = grp['group_id']
                print(f"Matched session '{session_name}' to group '{g_name}' (ID: {matched_group_id})")
                break
        
        if matched_group_id:
            group_students_df = df_std_groups[df_std_groups['group_id'] == matched_group_id]
            valid_student_names = set(group_students_df['student_name'].dropna().tolist())
            print(f"Found {len(valid_student_names)} students in CSV for this group.")
            
            matches = [s for s in all_db_students if s['student_name'] in valid_student_names]
            print(f"Matched {len(matches)} students between CSV and DB.")
            
            if not matches and valid_student_names:
                print("⚠️ SAMPLE MISMATCH CHECK:")
                csv_sample = list(valid_student_names)[0]
                db_sample = all_db_students[0]['student_name']
                print(f"  CSV Sample: {csv_sample} (type: {type(csv_sample)})")
                print(f"  DB Sample: {db_sample} (type: {type(db_sample)})")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_matching()

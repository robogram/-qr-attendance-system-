from supabase_client import supabase_mgr
import json

def debug_attendance_schema():
    print("🧹 Debugging Attendance Schema...")
    
    # 1. Check all columns on students table
    print("\n-- 1. Students Table Raw Check --")
    res1 = supabase_mgr.client.table('students').select('*').limit(1).execute()
    print(json.dumps(res1.data, indent=2, ensure_ascii=False))

    # 2. Check all columns on attendance table
    print("\n-- 2. Attendance Table Raw Check --")
    res2 = supabase_mgr.client.table('attendance').select('*').limit(1).execute()
    print(json.dumps(res2.data, indent=2, ensure_ascii=False))

    # 3. Try join query with explicit columns
    # If the error is 'students_1.class_group_id does not exist', 
    # it means students is aliased to students_1.
    # Let's try selecting everything first to see the structure.
    print("\n-- 3. Attendance Joined with Students (*) --")
    res3 = supabase_mgr.client.table('attendance').select('*, students(*)').limit(1).execute()
    print(json.dumps(res3.data, indent=2, ensure_ascii=False))
    
    # 4. Try specific column selection that caused error
    print("\n-- 4. Testing Specific Column Join --")
    try:
        res4 = supabase_mgr.client.table('attendance') \
            .select('id, students(student_name, class_group_id)') \
            .limit(1).execute()
        print("✅ Status: Success")
        print(json.dumps(res4.data, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ Status: Failed\nError: {e}")

if __name__ == "__main__":
    debug_attendance_schema()

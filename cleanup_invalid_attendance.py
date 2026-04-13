from supabase_client import supabase_mgr
import json

def cleanup_attendance():
    print("🧹 Starting Attendance Cleanup (Removing Cross-Class Duplicates)...")
    
    # 1. Fetch all attendance records with student and schedule group info
    try:
        # We need students!inner and schedule!inner to filter in the join
        # but Supabase Python client might be easier if we just fetch and filter in Python
        # to ensure we have the latest group_id for students.
        
        print("📡 Fetching attendance data...")
        query = supabase_mgr.client.table('attendance').select(
            'id, student_id, schedule_id, students(student_name, class_group_id), schedule(class_name, group_id)'
        ).execute()
        
        records = query.data
        if not records:
            print("✅ No attendance records found.")
            return

        to_delete = []
        for rec in records:
            student = rec.get('students')
            schedule = rec.get('schedule')
            
            if not student or not schedule:
                continue
                
            s_group = student.get('class_group_id')
            c_group = schedule.get('group_id')
            
            # If student's current group doesn't match the class group, it's a "zombie" record
            if s_group != c_group:
                print(f"🚩 Found Mismatch: {student['student_name']} (Group {s_group}) in {schedule.get('class_name', 'Unknown')} (Group {c_group}) - ID: {rec['id']}")
                to_delete.append(rec['id'])

        if not to_delete:
            print("✅ No invalid records discovered.")
        else:
            print(f"🗑️ Deleting {len(to_delete)} invalid records...")
            # Supabase delete with .in_
            for i in range(0, len(to_delete), 100):
                chunk = to_delete[i:i+100]
                supabase_mgr.client.table('attendance').delete().in_('id', chunk).execute()
            print(f"✨ Successfully deleted {len(to_delete)} records.")

    except Exception as e:
        print(f"❌ Error during cleanup: {e}")

if __name__ == "__main__":
    cleanup_attendance()

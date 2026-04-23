import os
from supabase import create_client, Client
from dotenv import load_dotenv

# .env 파일 로드 (현재 파일 위치 기준)
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

# 🆕 HTTP/2 프로토콜 오류(RemoteProtocolError) 방지를 위해 HTTP/1.1 강제 시도
os.environ["HTTPX_HTTP2"] = "0"

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

class SupabaseManager:
    def __init__(self):
        if not SUPABASE_URL or not SUPABASE_KEY:
            self.client = None
            print("⚠️ Supabase credentials missing. Check your .env file.")
        else:
            self.client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # --- Users ---
    def get_user_by_username(self, username):
        if not self.client: return None
        try:
            response = self.client.table('users').select('*').eq('username', username).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"❌ Error getting user by username: {e}")
            return None

    def get_user_by_id(self, user_id):
        if not self.client: return None
        try:
            response = self.client.table('users').select('*').eq('id', user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"❌ Error getting user by id: {e}")
            return None
        
    def get_all_users(self):
        if not self.client: return []
        try:
            response = self.client.table('users').select('*').execute()
            return response.data
        except Exception as e:
            print(f"❌ Error getting all users: {e}")
            return []
        
    def insert_user(self, user_data):
        if not self.client: return None
        try:
            res = self.client.table('users').insert(user_data).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            print(f"❌ Error inserting user: {e}")
            return None
            
    def update_user(self, user_id, user_data):
        if not self.client: return False
        try:
            self.client.table('users').update(user_data).eq('id', user_id).execute()
            return True
        except Exception as e:
            print(f"Error updating user: {e}")
            return False
            
    def delete_user(self, user_id):
        if not self.client: return False
        try:
            self.client.table('users').delete().eq('id', user_id).execute()
            return True
        except Exception as e:
            print(f"❌ Error deleting user: {e}")
            return False

    def get_user_by_name_and_password(self, name, password):
        if not self.client: return None
        try:
            response = self.client.table('users').select('*')\
                .eq('name', name)\
                .eq('password', password)\
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"❌ Error getting user by name/pw: {e}")
            return None

    # --- Students ---
    def get_all_students(self):
        if not self.client: return []
        response = self.client.table('students').select('*').execute()
        return response.data
        
    def get_students_by_group(self, group_id):
        if not self.client: return []
        response = self.client.table('students').select('*').eq('class_group_id', group_id).execute()
        return response.data
    def load_valid_codes(self):
        """유효한 학생 QR 코드 목록(data) 반환"""
        if not self.client: return set()
        response = self.client.table('students').select('qr_code_data').execute()
        return {s['qr_code_data'] for s in response.data}
        
    def get_student_by_qr(self, qr_code_data):
        if not self.client: return None
        response = self.client.table('students').select('*').eq('qr_code_data', qr_code_data).execute()
        return response.data[0] if response.data else None

    # --- Schedule ---
    def get_all_schedules(self):
        if not self.client: return []
        try:
            response = self.client.table('schedule').select('*').execute()
            return response.data
        except Exception as e:
            print(f"❌ Error getting all schedules: {e}")
            return []
    def get_schedule_for_date(self, target_date_str):
        """해당 날짜(YYYY-MM-DD)에 해당하는 수업 목록 반환 (KST 기준 필터)"""
        if not self.client: return []
        
        # 💡 한국 시간(KST) 대역을 명시적으로 사용 (+09:00)
        # 이래야 새벽 수업(UTC 기준 전날 저녁)이 누락되지 않습니다.
        start_bound = f"{target_date_str}T00:00:00+09:00"
        end_bound = f"{target_date_str}T23:59:59+09:00"
        
        try:
            response = self.client.table('schedule').select('*')\
                .gte('start_time', start_bound)\
                .lte('start_time', end_bound).execute()
            return response.data
        except Exception as e:
            print(f"❌ Error fetching schedule for date {target_date_str}: {e}")
            return []

    def get_schedule_by_id(self, schedule_id):
        if not self.client: return None
        try:
            response = self.client.table('schedule').select('*').eq('id', schedule_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"❌ Error getting schedule by id: {e}")
            return None

    # --- Attendance ---
    def check_already_attended(self, student_id, schedule_id):
        """특정 학생이 특정 수업에 이미 출석했는지 확인"""
        if not self.client: return False
        try:
            response = self.client.table('attendance').select('id')\
                .eq('student_id', student_id)\
                .eq('schedule_id', schedule_id).execute()
            return len(response.data) > 0
        except Exception as e:
            print(f"❌ Error checking attendance: {e}")
            return False

    def insert_attendance(self, student_id, schedule_id, check_in_time, status, type_str='오프라인', remark=''):
        """새로운 출석 기록 추가"""
        if not self.client: return False
        record = {
            'student_id': student_id,
            'schedule_id': schedule_id,
            'check_in_time': check_in_time,
            'status': status,
            'type': type_str,
            'remark': remark
        }
        try:
            self.client.table('attendance').insert(record).execute()
            return True
        except Exception as e:
            print(f"❌ Supabase insert failed: {e}")
            return False

    # --- Class Groups ---
    def get_all_class_groups(self):
        if not self.client: return []
        try:
            response = self.client.table('class_groups').select('*').execute()
            return response.data
        except Exception as e:
            print(f"❌ Error getting class groups: {e}")
            return []

    def upsert_class_group(self, group_data):
        if not self.client: return None, "Supabase 클라이언트가 초기화되지 않았습니다."
        try:
            # group_id를 기준으로 upsert (conflict 시 update)
            res = self.client.table('class_groups').upsert(group_data, on_conflict='group_id').execute()
            
            # 실제 데이터베이스에 변경사항이 생겼는지 확인
            if hasattr(res, 'data') and res.data:
                return res.data[0], None
            else:
                # 데이터가 안 돌아오면 실제 DB를 다시 조회해서 확인 (안전장치)
                check = self.client.table('class_groups').select('*').eq('group_id', group_data['group_id']).execute()
                if check.data:
                    return check.data[0], None
                return None, "데이터베이스 저장 실패 (응답 데이터 없음)"
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error upserting class group: {error_msg}")
            return None, error_msg

    def delete_class_group(self, group_id):
        if not self.client: return False
        try:
            self.client.table('class_groups').delete().eq('group_id', group_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting class group: {e}")
            return False

    # --- Student Groups ---
    def get_all_student_groups(self):
        if not self.client: return []
        response = self.client.table('student_groups').select('*').execute()
        return response.data

    def insert_student_group(self, mapping_data):
        if not self.client: return None
        try:
            res = self.client.table('student_groups').insert(mapping_data).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            print(f"Error inserting student group mapping: {e}")
            return None

    def delete_student_group(self, student_name, group_id):
        if not self.client: return False
        try:
            self.client.table('student_groups').delete().eq('student_name', student_name).eq('group_id', group_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting student group mapping: {e}")
            return False

    # --- Teacher Groups ---
    def get_all_teacher_groups(self):
        if not self.client: return []
        response = self.client.table('teacher_groups').select('*').execute()
        return response.data

    def get_teacher_groups_by_teacher(self, teacher_username):
        if not self.client: return []
        response = self.client.table('teacher_groups').select('*').eq('teacher_username', teacher_username).execute()
        return response.data

    def insert_teacher_group(self, mapping_data):
        if not self.client: return None
        try:
            res = self.client.table('teacher_groups').insert(mapping_data).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            print(f"Error inserting teacher group mapping: {e}")
            return None

    def delete_teacher_group(self, mapping_id):
        if not self.client: return False
        try:
            self.client.table('teacher_groups').delete().eq('id', mapping_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting teacher group mapping: {e}")
            return False

    def delete_teacher_group_strict(self, teacher_username, group_id, date_str=None):
        """선생님 배정 해제 (상세 조건)"""
        if not self.client: return False
        query = self.client.table('teacher_groups').delete()\
            .eq('teacher_username', teacher_username)\
            .eq('group_id', group_id)
        if date_str:
            query = query.eq('date', date_str)
        else:
            query = query.is_('date', 'null')
            
        try:
            query.execute()
            return True
        except Exception as e:
            print(f"Error deleting teacher group mapping strict: {e}")
            return False

# 글로벌 인스턴스
supabase_mgr = SupabaseManager()

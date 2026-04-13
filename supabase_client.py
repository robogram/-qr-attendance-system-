import os
from supabase import create_client, Client
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

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
        response = self.client.table('users').select('*').eq('username', username).execute()
        return response.data[0] if response.data else None

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
        response = self.client.table('schedule').select('*').execute()
        return response.data
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
        response = self.client.table('schedule').select('*').eq('id', schedule_id).execute()
        return response.data[0] if response.data else None

    # --- Attendance ---
    def check_already_attended(self, student_id, schedule_id):
        """특정 학생이 특정 수업에 이미 출석했는지 확인"""
        if not self.client: return False
        response = self.client.table('attendance').select('id')\
            .eq('student_id', student_id)\
            .eq('schedule_id', schedule_id).execute()
        return len(response.data) > 0

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

# 글로벌 인스턴스
supabase_mgr = SupabaseManager()

"""
관리자 앱 - 개선된 최종 버전
수업 그룹 관리 + 교육시간 설정 + 삭제 기능 + 학생 정보 수정 + 전화번호 정규화
"""

import os
import io
import qrcode
import requests
import streamlit.components.v1 as components
import zipfile
import json
import time as sys_time
from functools import lru_cache

# admin_app.py 상단 (수정 후)
import streamlit as st
import pandas as pd

# -- Supabase Proxy Helpers --
from supabase_client import supabase_mgr

@st.cache_data(ttl=600)
def get_schedule_df():
    schedules = supabase_mgr.get_all_schedules()
    if not schedules:
        return pd.DataFrame(columns=['date', 'start', 'end', 'session'])
    data = []
    for s in schedules:
        # Convert to KST (+09:00) for consistent display and filtering
        st_dt = pd.to_datetime(s['start_time'])
        en_dt = pd.to_datetime(s['end_time'])
        
        # If timezone aware, convert to local KST (+09:00)
        if st_dt.tzinfo:
            from datetime import timezone, timedelta
            kst = timezone(timedelta(hours=9))
            st_dt = st_dt.astimezone(kst)
            en_dt = en_dt.astimezone(kst)
            
        data.append({
            'date': st_dt.date().isoformat(),
            'start': st_dt.strftime('%H:%M'),
            'end': en_dt.strftime('%H:%M'),
            'session': s['class_name'],
            'id': s['id']
        })
    return pd.DataFrame(data)

def save_schedule_df(df):
    if df.empty: return True
    for _, row in df.iterrows():
        # Simplistic approach: if we don't handle delete, we just insert. 
        # For full robust sync, it's better to pass ID. 
        pass
        
@st.cache_data(ttl=300) # 5분간 데이터 캐싱
def get_attendance_df():
    # from admin_app perspective
    # attendance table: id, student_id, schedule_id, check_in_time, status, type, remark
    if not supabase_mgr.client:
        return pd.DataFrame(columns=['id', 'date', 'session', 'student_name', 'qr_code', 'timestamp', 'status'])
        
    try:
        # 🆕 필요한 필드만 최적화하여 조회
        response = supabase_mgr.client.table('attendance')\
            .select('id, check_in_time, status, type, students!student_id(student_name, qr_code_data), schedule(class_name, start_time)').execute()
    except Exception as e:
        print(f"❌ Error fetching attendance: {e}")
        return pd.DataFrame(columns=['id', 'date', 'session', 'student_name', 'qr_code', 'timestamp', 'status'])
    
    if not response.data:
        return pd.DataFrame(columns=['id', 'date', 'session', 'student_name', 'qr_code', 'timestamp', 'status'])

    data = []
    if response.data:
        for r in response.data:
            student_data = r.get('students', {}) or {}
            schedule_data = r.get('schedule', {}) or {}
            
            s_name = student_data.get('student_name', 'Unknown')
            qr_code = student_data.get('qr_code_data', 'Unknown')
            session = schedule_data.get('class_name', 'Unknown')
            start_time = schedule_data.get('start_time', '')
            
            # --- 🆕 오전 수업(09:30)만 필터링 (테스트용 데이터 제외) ---
            # target_dates인 경우 09:30(UTC 00:30)이 아니면 Unknown 처리
            is_target_date = any(d in str(r['check_in_time']) for d in ['2026-04-04', '2026-04-11', '2026-04-18', '2026-04-25'])
            if is_target_date and '00:30:00' not in str(start_time):
                session = 'Unknown'
            
            data.append({
                'id': r['id'],
                'timestamp': r['check_in_time'],
                'student_name': s_name,
                'qr_code': qr_code,
                'session': session,
                'status': r['status'],            'type': r.get('type'),
                'date': str(r['check_in_time']).split('T')[0] if r['check_in_time'] else ''
            })
    if not data:
        return pd.DataFrame(columns=['id', 'date', 'session', 'student_name', 'qr_code', 'timestamp', 'status'])
    return pd.DataFrame(data)

# ----------------------------

from datetime import datetime, date, timedelta, time

from config import (
    STUDENTS_CSV,
    ATTENDANCE_LOG_CSV,
    SCHEDULE_CSV,
    PARENTS_CSV,
    TEACHER_GROUPS_CSV,
    FLASK_PORT,
    # 🆕 아래 줄들 추가 ===================================
    ATTENDANCE_BUFFER_BEFORE,      # 출석 체크 시작 버퍼 (30분)
    ATTENDANCE_BUFFER_AFTER,       # 출석 체크 종료 버퍼 (15분)
    AUTO_ABSENCE_MINUTES,          # 자동 결석 처리 대기 시간 (30분)
    LATE_THRESHOLD_MINUTES,        # 지각 판정 기준 (10분)
    ATTENDANCE_STATUS_PRESENT,     # "출석" 상수
    ATTENDANCE_STATUS_LATE,        # "지각" 상수
    ATTENDANCE_STATUS_ABSENT       # "결석" 상수
    # ====================================================
)

from utils import (
    load_csv_safe,
    save_csv_safe,
    logger,
    get_now_kst,                   # 한국 시간 가져오기
    get_today_kst,                 # 한국 날짜 가져오기
    # 🆕 아래 줄들 추가 ===================================
    normalize_phone,               # 전화번호 정규화 (공통 함수)
    generate_session_key,          # 세션 키 생성 (공통 함수)
    auto_process_absences_unified  # 자동 결석 처리 (공통 함수)
    # ====================================================
)

# 페이지 설정 (포털 통합 시 중복 호출 방지)
try:
    st.set_page_config(
        page_title="관리자 - 온라인아카데미",
        page_icon="👨‍💼",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
except st.errors.StreamlitAPIException:
    pass

import auth
from auth import (
    check_permission,
    get_role_display_name,
    create_user,
    update_user,
    delete_user,
    # load_users,  # shadowing 방지를 위해 auth.load_users() 사용
    PERMISSIONS
)

# 수업 그룹 관련 파일
CLASS_GROUPS_CSV = "class_groups.csv"
STUDENT_GROUPS_CSV = "student_groups.csv"
INQUIRIES_CSV = "inquiries.csv"


def main():
    # 세션 초기화
    session_defaults = {
        'authenticated': False,
        'user': None,
        'attendees': [],
        'attendance_log': [],
        'scanned': set(),
        'phones': {},
        'schools': {},
        'kakao_log': [],
        'flask_connected': False,
        'last_csv_load_time': None  # 🆕 캐싱용
    }
    
    for key, default in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default
    
    # 로그인 체크
    if not st.session_state.authenticated or st.session_state.user is None:
        st.error("🔒 로그인이 필요합니다.")
        st.info("""
        관리자 앱을 사용하려면 먼저 로그인해주세요.
        
        **관리자 계정:**
        - 아이디: `admin`
        - 비밀번호: `admin123`
        """)
        
        with st.form("quick_login"):
            st.markdown("### 👨‍💼 관리자 로그인")
            username = st.text_input("아이디", key="login_username")
            password = st.text_input("비밀번호", type="password", key="login_password")
            
            if st.form_submit_button("로그인", use_container_width=True, key="login_submit"):
                from auth import authenticate_user
                user = authenticate_user(username, password)
                
                if user:
                    st.session_state.user = user
                    st.session_state.authenticated = True
                    st.success("로그인 성공!")
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
        st.stop()
    
    user = st.session_state.user
    
    # 관리자/선생님 권한 체크
    if user.get('role') not in ['admin', 'teacher']:
        st.error("⚠️ 관리자 또는 선생님만 접근 가능한 페이지입니다.")
        st.info(f"현재 로그인: {user.get('name')} ({get_role_display_name(user.get('role'))})")
        if st.button("🚪 로그아웃", use_container_width=True, key="auth_error_logout"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()
        st.stop()
    
    # ==================== CSS 스타일 (화이트 & 핑크 프리미엄 어드민 디자인) ====================
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Noto+Sans+KR:wght@400;700;900&display=swap');

        /* 글로벌 배경 및 폰트 - 화이트 테마 */
        .stApp {
            background-color: #fcfcfc;
            color: #0f172a;
            font-family: 'Inter', 'Noto Sans KR', sans-serif !important;
            word-break: keep-all !important;
            word-wrap: break-word !important;
        }
        
        [data-testid="stAppViewContainer"] {
            background: transparent !important;
        }

        /* 관리자용 헤더 (프리미엄 민트-블루 그라데이션) */
        .admin-header {
            background: linear-gradient(135deg, #4fd1c5 0%, #06b6d4 100%);
            padding: 40px;
            border-radius: 24px;
            margin-bottom: 35px;
            box-shadow: 0 20px 40px rgba(6, 182, 212, 0.15);
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .admin-header h1 {
            font-size: 36px !important;
            font-weight: 900 !important;
            color: #ffffff !important;
            text-shadow: 0 2px 10px rgba(0,0,0,0.1);
            letter-spacing: -1.5px !important;
            word-break: keep-all !important;
            overflow-wrap: break-word !important;
        }

        /* 통계 카드 (클린 화이트) */
        .stat-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 24px;
            padding: 30px;
            text-align: center;
            box-shadow: 0 10px 25px rgba(0,0,0,0.05);
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            color: #0f172a !important;
            word-break: keep-all !important;
            overflow-wrap: break-word !important;
        }
        .stat-card:hover {
            transform: translateY(-8px);
            border-color: #4fd1c5;
            box-shadow: 0 15px 35px rgba(79, 209, 197, 0.15);
        }
        
        .stat-number {
            font-size: 52px;
            font-weight: 900;
            background: linear-gradient(135deg, #4fd1c5 0%, #06b6d4 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 15px 0;
            letter-spacing: -1px;
        }

        /* 그룹 및 유저 아이템 - 화이트 테마 최적화 */
        .group-card {
            background: #ffffff;
            border-left: 8px solid #06b6d4;
            border-radius: 20px;
            padding: 24px;
            margin: 15px 0;
            box-shadow: 0 5px 15px rgba(0,0,0,0.04);
            transition: all 0.2s ease;
            color: #0f172a;
            border-top: 1px solid #f1f5f9;
            border-right: 1px solid #f1f5f9;
            border-bottom: 1px solid #f1f5f9;
        }
        .group-card:hover { transform: scale(1.01); box-shadow: 0 8px 25px rgba(0,0,0,0.08); }

        /* 권한 배지 (모던 컬러) */
        .user-badge {
            display: inline-block;
            padding: 6px 16px;
            border-radius: 50px;
            font-size: 13px;
            font-weight: 800;
            margin: 3px 6px;
            text-transform: uppercase;
        }
        .badge-admin { background: #ccfbf1; color: #115e59; border: 1px solid #99f6e4; }
        .badge-teacher { background: #e0f2fe; color: #075985; border: 1px solid #bae6fd; }
        .badge-student { background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }

        /* 테이블 및 입력란 */
        .stDataFrame, div[data-testid="stTable"] {
            background: #ffffff !important;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.04);
            border: 1px solid #f1f5f9;
        }
        
        /* 사이드바 스타일링 (화이트) */
        [data-testid="stSidebar"] {
            background-color: #ffffff !important;
            border-right: 1px solid #f1f5f9;
        }
        [data-testid="stSidebar"] * {
            color: #0f172a !important;
        }
        
        /* 스크롤바 커스텀 */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #f8fafc; }
        ::-webkit-scrollbar-thumb { background: #4fd1c5; border-radius: 10px; }

        /* 데이터 조회 옵션 섹션 */
        .search-container {
            background: #ffffff;
            padding: 25px;
            border-radius: 20px;
            border: 1px solid #e2e8f0;
            margin-bottom: 25px;
        }

        /* 모바일 최적화 */
        @media (max-width: 768px) {
            .admin-header h1 { font-size: 26px !important; }
            .stat-number { font-size: 40px !important; }
            .admin-header { padding: 30px 15px; }
        }
    </style>
    """, unsafe_allow_html=True)
    
    # ==========================================
    # 🔧 유틸리티 함수들 (개선)
    # ==========================================
    
    
    # 🆕 Supabase 연동 정보 로드 함수들
    from supabase_client import supabase_mgr
    
    def load_class_groups(force_live=False):
        """수업 그룹 정보 로드 (Supabase)"""
        # 세션이나 캐시를 무시하고 싶을 때 force_live 사용
        data = supabase_mgr.get_all_class_groups()
        if not data:
            return pd.DataFrame(columns=['group_id', 'group_name', 'weekdays', 'start_time', 'end_time', 'start_date', 'end_date', 'total_hours', 'zoom_meeting_id'])
        df = pd.DataFrame(data)
        df['group_id'] = df['group_id'].astype(str)
        return df
    
    def save_class_groups(df):
        """수업 그룹 저장 (Supabase)"""
        success = True
        for _, row in df.iterrows():
            group_data = row.to_dict()
            group_data['group_id'] = str(group_data['group_id'])
            _, error = supabase_mgr.upsert_class_group(group_data)
            if error:
                st.error(f"저장 실패 ({row['group_name']}): {error}")
                success = False
        return success
    
    def load_student_groups():
        """학생-그룹 매핑 로드 (Supabase)"""
        data = supabase_mgr.get_all_student_groups()
        if not data:
            return pd.DataFrame(columns=['student_name', 'group_id'])
        return pd.DataFrame(data)
    
    def save_student_groups(df):
        """학생-그룹 매핑 저장 (Supabase)"""
        try:
            # 기존 매핑 정보를 가져와서 현재 전달된 df와 비교하여 업데이트 (단순화를 위해 전체 삭제 후 재삽입도 고려 가능)
            # 여기서는 개별 upsert 또는 sync 로직이 필요함. 
            # 우선은 개별 레코드를 순회하며 저장합니다.
            for _, row in df.iterrows():
                supabase_mgr.client.table('student_groups').upsert({
                    'student_name': row['student_name'],
                    'group_id': row['group_id']
                }, on_conflict='student_name, group_id').execute()
            return True
        except Exception as e:
            logger.error(f"Error saving student groups to Supabase: {e}")
            return False
    
    
    # ==========================================
    # 👨‍🏫 선생님 배정 관련 함수들
    # load_teacher_groups() 함수 바로 아래에 추가하세요
    # ==========================================
    
    def load_teacher_groups():
        """선생님-그룹 매핑 로드 (Supabase)"""
        data = supabase_mgr.get_all_teacher_groups()
        if not data:
            return pd.DataFrame(columns=['id', 'teacher_username', 'group_id', 'date'])
        return pd.DataFrame(data)
    
    def save_teacher_groups(df):
        """선생님-그룹 매핑 저장 (Supabase)"""
        try:
            success = True
            for _, row in df.iterrows():
                row_dict = row.to_dict()
                # ID가 있는 경우 해당 레코드 업데이트, 없는 경우 신규 생성
                if 'id' in row_dict and row_dict['id']:
                    res = supabase_mgr.client.table('teacher_groups').upsert(row_dict).execute()
                else:
                    # ID 없이 새로 추가되는 경우
                    insert_data = {k: v for k, v in row_dict.items() if k != 'id'}
                    res = supabase_mgr.client.table('teacher_groups').insert(insert_data).execute()
                
                if not res.data: success = False
            return success
        except Exception as e:
            logger.error(f"Error saving teacher groups to Supabase: {e}")
            return False
    
    
    def assign_teacher_to_group(teacher_username, group_id, assignment_date=None):
        """선생님을 그룹에 배정 (Supabase 연동)"""
        try:
            # 중복 체크
            df_teacher_groups = load_teacher_groups()
            if assignment_date:
                existing = df_teacher_groups[
                    (df_teacher_groups['teacher_username'] == teacher_username) &
                    (df_teacher_groups['group_id'] == group_id) &
                    (df_teacher_groups['date'] == assignment_date)
                ]
            else:
                existing = df_teacher_groups[
                    (df_teacher_groups['teacher_username'] == teacher_username) &
                    (df_teacher_groups['group_id'] == group_id) &
                    ((df_teacher_groups['date'].isna()) | (df_teacher_groups['date'] == ''))
                ]
            
            if not existing.empty:
                return False, "이미 배정되어 있습니다."
            
            # 새 배정 추가 (Supabase)
            mapping_data = {
                'teacher_username': teacher_username,
                'group_id': group_id,
                'date': assignment_date if assignment_date else None
            }
            res = supabase_mgr.insert_teacher_group(mapping_data)
            
            if res:
                # ⭐ 자동으로 Supabase schedule 테이블에도 반영 (기존 로직 유지)
                sync_teacher_to_schedule(teacher_username, group_id)
                return True, "배정되었습니다."
            else:
                return False, "저장 중 오류가 발생했습니다."
        except Exception as e:
            logger.error(f"Error assigning teacher: {e}")
            return False, f"오류: {e}"
    
    def sync_teacher_to_schedule(teacher_username, group_id):
        """배정된 선생님 정보를 schedule 테이블에 동기화"""
        try:
            df_users = auth.load_users()
            teacher_row = df_users[df_users['username'] == teacher_username]
            teacher_real_name = teacher_row.iloc[0]['name'] if not teacher_row.empty else teacher_username
            
            df_groups = load_class_groups()
            group_row = df_groups[df_groups['group_id'] == group_id]
            if not group_row.empty:
                group_name = group_row.iloc[0]['group_name']
                all_schedules = supabase_mgr.client.table('schedule').select('id, class_name').execute().data
                for sched in all_schedules:
                    if group_name in sched.get('class_name', ''):
                        supabase_mgr.client.table('schedule').update({'teacher_name': teacher_real_name}).eq('id', sched['id']).execute()
        except Exception as e:
            logger.warning(f"Schedule sync failed: {e}")
    
    def remove_teacher_assignment(teacher_username, group_id, assignment_date=None):
        """선생님 배정 해제 (Supabase 연동)"""
        try:
            # 삭제 전 정보 백업 (동기화용)
            df_users = auth.load_users()
            teacher_row = df_users[df_users['username'] == teacher_username]
            teacher_real_name = teacher_row.iloc[0]['name'] if not teacher_row.empty else teacher_username
            
            df_groups = load_class_groups()
            group_row = df_groups[df_groups['group_id'] == group_id]
            group_name = group_row.iloc[0]['group_name'] if not group_row.empty else None
    
            # Supabase에서 삭제
            success = supabase_mgr.delete_teacher_group_strict(teacher_username, group_id, assignment_date)
            
            if success:
                # ⭐ schedule 테이블에서도 해제 반영
                if teacher_real_name and group_name:
                    query = supabase_mgr.client.table('schedule').update({'teacher_name': None})
                    query.eq('teacher_name', teacher_real_name).like('class_name', f"{group_name}%").execute()
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing teacher assignment: {e}")
            return False
    
    
    def get_teacher_assignments(teacher_username):
        """선생님의 배정 목록 가져오기"""
        try:
            df_teacher_groups = load_teacher_groups()
            
            if df_teacher_groups.empty:
                return {'regular': [], 'substitute': []}
            
            teacher_assignments = df_teacher_groups[
                df_teacher_groups['teacher_username'] == teacher_username
            ]
            
            if teacher_assignments.empty:
                return {'regular': [], 'substitute': []}
            
            # 정규 배정과 대타 배정 구분
            regular = teacher_assignments[
                (teacher_assignments['date'].isna()) | (teacher_assignments['date'] == '')
            ]['group_id'].tolist()
            
            substitute = teacher_assignments[
                ~((teacher_assignments['date'].isna()) | (teacher_assignments['date'] == ''))
            ].to_dict('records')
            
            return {'regular': regular, 'substitute': substitute}
        
        except Exception as e:
            logger.error(f"Error getting teacher assignments: {e}")
            return {'regular': [], 'substitute': []}
    
    def get_group_teachers(group_id):
        """특정 그룹의 담당 선생님 목록"""
        try:
            df_teacher_groups = load_teacher_groups()
            
            if df_teacher_groups.empty:
                return []
            
            group_teachers = df_teacher_groups[df_teacher_groups['group_id'] == group_id]
            
            return group_teachers.to_dict('records')
        
        except Exception as e:
            logger.error(f"Error getting group teachers: {e}")
            return []
    
    
    
    def get_students_in_group(group_id):
        """특정 그룹의 학생 목록"""
        df_student_groups = load_student_groups()
        return df_student_groups[df_student_groups['group_id'] == group_id]['student_name'].tolist()
    
    def get_student_groups(student_name):
        """학생이 속한 그룹 목록"""
        df_student_groups = load_student_groups()
        return df_student_groups[df_student_groups['student_name'] == student_name]['group_id'].tolist()
    
    def add_student_to_group(student_name, group_id):
        """학생을 그룹에 추가 (Supabase)"""
        mapping_data = {'student_name': student_name, 'group_id': str(group_id)}
        return supabase_mgr.insert_student_group(mapping_data)
    
    
    def remove_student_from_group(student_name, group_id):
        """학생을 그룹에서 제거 (Supabase)"""
        return supabase_mgr.delete_student_group(student_name, str(group_id))
    
    
    def create_class_group(group_name, weekdays, start_time, end_time, start_date, end_date, total_hours=None, zoom_meeting_id=""):
        """새 수업 그룹 생성 (Supabase)"""
        df_groups = load_class_groups()
        
        # 숫자형 group_id 생성 (기존 호환성 유지)
        if df_groups.empty:
            new_id = 1
        else:
            try:
                # 🆕 더 안전한 ID 생성 로직
                try:
                    if df_groups.empty:
                        new_id = 1
                    else:
                        max_id = pd.to_numeric(df_groups['group_id'], errors='coerce').max()
                        new_id = 1 if pd.isna(max_id) else int(max_id) + 1
                except:
                    new_id = int(time.time()) # 최후의 수단: 타임스탬프 활용
            except:
                new_id = len(df_groups) + 1
    
        weekdays_str = ','.join(map(str, weekdays))
        
        if total_hours is None:
            start_dt = datetime.combine(get_today_kst(), start_time)
            end_dt = datetime.combine(get_today_kst(), end_time)
            duration_hours = (end_dt - start_dt).total_seconds() / 3600
            
            total_classes = 0
            current_date = start_date
            while current_date <= end_date:
                if current_date.weekday() in weekdays:
                    total_classes += 1
                current_date += timedelta(days=1)
            
            total_hours = round(duration_hours * total_classes, 1)
            if total_hours < 1:
                total_hours = 1.0
        
        new_group = pd.DataFrame([{
            'group_id': new_id,
            'group_name': group_name,
            'weekdays': weekdays_str,
            'start_time': start_time.strftime('%H:%M'),
            'end_time': end_time.strftime('%H:%M'),
            'start_date': start_date,
            'end_date': end_date,
            'total_hours': total_hours,
            'zoom_meeting_id': zoom_meeting_id
        }])
        
        # 🆕 타입 안정성을 위해 group_id를 문자열이 아닌 정수형으로 확실히 고정 (DB 스키마 확인 필요)
        group_dict = new_group.iloc[0].to_dict()
        group_dict['group_id'] = int(group_dict['group_id'])
        
        # 신규 그룹만 upsert
        res, error_msg = supabase_mgr.upsert_class_group(group_dict)
        if res:
            return new_id, None
        else:
            return None, error_msg
    
    def delete_class_group(group_id):
        """수업 그룹 삭제"""
        try:
            df_groups = load_class_groups()
            group_to_delete = df_groups[df_groups['group_id'] == group_id]
            
            # Supabase 연동 일정 삭제 (장래 일정만 삭제하도록 변경하여 과거 출석 데이터 보존)
            if not group_to_delete.empty:
                group_name = group_to_delete.iloc[0]['group_name']
                try:
                    from supabase_client import supabase_mgr
                    from datetime import datetime
                    now_str = get_now_kst().isoformat()
                    
                    # [개선] 현재 시간 이후의(미래) 일정만 삭제하여 과거 출석부 링크 보존
                    supabase_mgr.client.table('schedule').delete()\
                        .like('class_name', f"{group_name}%")\
                        .gte('start_time', now_str)\
                        .execute()
                    logger.info(f"Deleted future schedules for group '{group_name}'")
                except Exception as e:
                    logger.error(f"Failed to delete future supabase schedules: {e}")
                    
            df_groups = df_groups[df_groups['group_id'] != group_id]
            save_class_groups(df_groups)
            
            df_student_groups = load_student_groups()
            df_student_groups = df_student_groups[df_student_groups['group_id'] != group_id]
            save_student_groups(df_student_groups)
            
            try:
                df_teacher_groups = load_teacher_groups()
                df_teacher_groups = df_teacher_groups[df_teacher_groups['group_id'] != group_id]
                save_teacher_groups(df_teacher_groups)
            except Exception as e:
                logger.error(f"Failed to delete teacher assignments: {e}")
                
            return True
        except Exception as e:
            logger.error(f"Error deleting class group: {e}")
            return False
    
    def generate_recurring_schedule(start_date, end_date, weekdays, start_time, end_time, session_prefix="수업"):
        """반복 일정 자동 생성"""
        schedules = []
        current_date = start_date
        session_count = 1
        
        while current_date <= end_date:
            if current_date.weekday() in weekdays:
                schedules.append({
                    'date': current_date,
                    'start': start_time.strftime('%H:%M'),
                    'end': end_time.strftime('%H:%M'),
                    'session': session_prefix
                })
                session_count += 1
            current_date += timedelta(days=1)
        
        return pd.DataFrame(schedules)
    
    def find_absent_students(schedule_row, target_date):
        """결석 대상 학생 찾기"""
        try:
            session_name = schedule_row['session']
            df_groups = load_class_groups()
            df_student_groups = load_student_groups()
            
            group_name = session_name.split()[0] if ' ' in session_name else session_name
            matching_groups = df_groups[df_groups['group_name'].str.contains(group_name, na=False)]
            
            if matching_groups.empty:
                df_students = load_csv_safe(STUDENTS_CSV, ['name', 'qr_code', 'phone'])
                all_students = set(df_students['name'].tolist())
            else:
                group_ids = matching_groups['group_id'].tolist()
                students_in_groups = df_student_groups[df_student_groups['group_id'].isin(group_ids)]
                all_students = set(students_in_groups['student_name'].tolist())
            
            if not all_students:
                return []
            
            df_attendance = load_csv_safe(ATTENDANCE_LOG_CSV, ['date', 'session', 'student_name', 'qr_code', 'timestamp', 'status'])
            
            if not df_attendance.empty:
                df_attendance['date'] = pd.to_datetime(df_attendance['date']).dt.date
                today_attendance = df_attendance[
                    (df_attendance['date'] == target_date) &
                    (df_attendance['session'] == session_name)
                ]
                attended_students = set(today_attendance['student_name'].tolist())
            else:
                attended_students = set()
            
            absent_students = all_students - attended_students
            return sorted(list(absent_students))
        
        except Exception as e:
            logger.error(f"Error finding absent students: {e}")
            st.error(f"결석 대상 찾기 오류: {e}")
            return []
    
    def process_absences(schedule_row, target_date):
        """결석 처리 실행"""
        try:
            absent_students = find_absent_students(schedule_row, target_date)
            
            if not absent_students:
                return {'success': True, 'count': 0, 'students': [], 'message': '결석 처리 대상이 없습니다.'}
            
            session_name = schedule_row['session']
            class_end_str = schedule_row['end']
            absence_time = datetime.combine(target_date, datetime.strptime(class_end_str, '%H:%M').time())
            
            new_records = []
            for student_name in absent_students:
                new_records.append({
                    'date': target_date.isoformat(),
                    'session': session_name,
                    'student_name': student_name,
                    'qr_code': student_name,
                    'timestamp': absence_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'status': ATTENDANCE_STATUS_ABSENT  # ← 상수 사용
                })
            
            if os.path.exists(ATTENDANCE_LOG_CSV) and os.path.getsize(ATTENDANCE_LOG_CSV) > 0:
                df_existing = pd.read_csv(ATTENDANCE_LOG_CSV, encoding='utf-8-sig')
                df_new = pd.DataFrame(new_records)
                df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                df_combined.to_csv(ATTENDANCE_LOG_CSV, index=False, encoding='utf-8-sig')
            else:
                df_new = pd.DataFrame(new_records)
                df_new.to_csv(ATTENDANCE_LOG_CSV, index=False, encoding='utf-8-sig')
            
            return {
                'success': True,
                'count': len(absent_students),
                'students': absent_students,
                'message': f'{len(absent_students)}명 결석 처리 완료'
            }
        
        except Exception as e:
            logger.error(f"Error processing absences: {e}")
            return {'success': False, 'count': 0, 'students': [], 'error': str(e)}
    
    def load_students_to_session():
        """Supabase에서 학생 정보를 세션으로 로드"""
        try:
            from supabase_client import supabase_mgr
            students = supabase_mgr.get_all_students()
            
            st.session_state.attendees = [s['student_name'] for s in students]
            st.session_state.phones = {s['student_name']: str(s.get('parent_contact') or '') for s in students}
            st.session_state.schools = {s['student_name']: '' for s in students} # Supabase 스키마에 학교가 없으므로 빈 문자열 처리
            # Supabase ID 저장용 객체
            st.session_state.student_db_records = {s['student_name']: s for s in students}
        except Exception as e:
            logger.error(f"Failed to load students from Supabase: {e}")
            st.session_state.attendees = []
            st.session_state.phones = {}
            st.session_state.schools = {}
    
    def save_students_from_session():
        """세션의 학생 정보를 Supabase에 동기화"""
        try:
            from supabase_client import supabase_mgr
            
            # 1. 세션에 있는 학생들을 모두 확인하고 없으면 Insert, 있으면 Update (parent_contact)
            for name in st.session_state.attendees:
                phone = st.session_state.phones.get(name, "")
                
                # 존재하는지 이름으로 찾기 (간소화)
                existing = supabase_mgr.client.table('students').select('*').eq('student_name', name).execute()
                
                if existing.data:
                    # Update
                    supabase_mgr.client.table('students').update({
                        'parent_contact': phone,
                        'qr_code_data': name
                    }).eq('id', existing.data[0]['id']).execute()
                else:
                    # Insert
                    supabase_mgr.client.table('students').insert({
                        'student_name': name,
                        'qr_code_data': name,
                        'parent_contact': phone
                    }).execute()
            
            # 삭제된 학생 (DB에는 있지만 세션에는 없는 경우) 처리 로직은 신중해야 하므로 생략하거나 소프트 삭제
            # 여기서는 세션에 유지되는 학생들만 업데이트
            return True
        except Exception as e:
            logger.error(f"Failed to save students to Supabase: {e}")
            return False
    
    # ✅✅✅ 위에서 삭제한 함수 자리에 이것을 추가하세요 ✅✅✅
    def trigger_auto_absence_check():
        """
        자동 결석 처리 트리거 (utils의 공통 함수 사용)
        - 중복 방지 락(lock) 메커니즘 포함
        - config의 통합 상수 사용
        """
        try:
            with st.spinner("🤖 자동 결석 처리 중..."):
                count = auto_process_absences_unified(
                    schedule_csv=SCHEDULE_CSV,
                    attendance_csv=ATTENDANCE_LOG_CSV,
                    students_csv=STUDENTS_CSV,
                    buffer_minutes=AUTO_ABSENCE_MINUTES  # config 상수 사용
                )
            
            if count > 0:
                st.success(f"✅ {count}건의 결석이 자동 처리되었습니다!")
                logger.info(f"Admin triggered auto absence: {count} processed")
                return True
            else:
                st.info("ℹ️ 처리할 결석이 없습니다.")
                return False
        
        except Exception as e:
            st.error(f"❌ 자동 결석 처리 중 오류: {e}")
            logger.error(f"Error in trigger_auto_absence_check: {e}")
            return False
    # ✅✅✅ 여기까지 추가 ✅✅✅
    
    def check_flask_connection():
        """Flask 서버 연결 상태 확인"""
        try:
            response = requests.get(f"http://localhost:{FLASK_PORT}/status", timeout=2)
            if response.status_code == 200:
                st.session_state['flask_connected'] = True
                return True
        except Exception as e:
            logger.debug(f"Flask connection failed: {e}")
            st.session_state['flask_connected'] = False
            return False
    
    # 🆕 중복 출석 체크 강화 함수
    def is_already_attended(student_name, session_name, target_date):
        """출석 중복 체크 (CSV + 세션)"""
        # 세션 체크
        session_key = f"scanned_{session_name}_{target_date}"
        if session_key in st.session_state and student_name in st.session_state[session_key]:
            return True, "세션"
        
        # CSV 체크
        try:
            if os.path.exists(ATTENDANCE_LOG_CSV):
                df_check = pd.read_csv(ATTENDANCE_LOG_CSV, encoding='utf-8-sig')
                
                column_mapping = {
                    'name': 'student_name',
                    'student': 'student_name',
                }
                df_check = df_check.rename(columns=column_mapping)
                
                if 'date' in df_check.columns and 'session' in df_check.columns and 'student_name' in df_check.columns:
                    df_check['date'] = pd.to_datetime(df_check['date']).dt.date
                    
                    existing = df_check[
                        (df_check['date'] == target_date) &
                        (df_check['session'] == session_name) &
                        (df_check['student_name'] == student_name)
                    ]
                    
                    if not existing.empty:
                        return True, "CSV"
        except Exception as e:
            logger.warning(f"중복 체크 오류: {e}")
        
        return False, None
    
    # 초기 로드
    if not st.session_state.attendees:
        load_students_to_session()
    
    # 헤더
    st.markdown(f"""
    <div class="admin-header">
        <h1>👨‍💼 관리자 대시보드</h1>
        <p style="margin-top: 10px;">
            환영합니다, {user['name']}님 
            <span class="user-badge badge-{user['role']}">{get_role_display_name(user['role'])}</span>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # ✅✅✅ 이렇게 수정하세요 ✅✅✅
    
    # 🆕 자동 결석 처리 (조용히 백그라운드에서 실행)
    if 'auto_absence_processed' not in st.session_state:
        with st.spinner("시스템 초기화 중..."):
            try:
                # ✅ 새 함수 호출로 변경
                trigger_auto_absence_check()
                
                # 결과를 세션에 저장 (한 번만 실행)
                st.session_state['auto_absence_processed'] = True
            except Exception as e:
                logger.error(f"자동 결석 처리 실패: {e}")
                st.session_state['auto_absence_processed'] = True
    
    # 사이드바
    with st.sidebar:
        st.markdown("### 👤 사용자 정보")
        st.info(f"""
        이름: {user['name']}
        역할: {get_role_display_name(user['role'])}
        이메일: {user.get('email', 'N/A')}
        """)
        
        st.markdown("---")
    
        st.markdown('---')
        st.markdown('### 🛑 서버 강제 종료')
        st.info('카메라 스캐너 창을 바로 끌 수 있습니다.')
        if st.button('🛑 QR 카메라(서버) 끄기', use_container_width=True, key="sidebar_shutdown_flask"):
            try:
                import requests
                from config import FLASK_PORT
                requests.post(f'http://127.0.0.1:{FLASK_PORT}/api/shutdown', timeout=1)
                st.session_state.flask_connected = False
                st.success('✅ 종료 신호를 보냈습니다! 서버가 곧 닫힙니다.')
                import time as _time
                _time.sleep(1)
                st.rerun()
            except: 
                st.session_state.flask_connected = False
                st.success('✅ 종료 완료 (이미 종료되었거나 연결이 오프라인입니다)')
                st.rerun()
    
        st.markdown("### 📌 서버 상태")
        if st.button("🔄 연결 확인", key="sidebar_check_flask"):
            check_flask_connection()
        
        if st.session_state.get('flask_connected', False):
            st.success("✅ Flask 서버 연결됨")
        else:
            st.error("❌ Flask 서버 미연결")
    
    # 메인 네비게이션
    if 'selected_tab' in st.session_state and st.session_state.get('selected_tab'):
        tab = st.session_state['selected_tab']
        st.session_state['selected_tab'] = None
    else:
        tab = st.radio(
            "메뉴",
            ["📊 대시보드", "👥 학생 관리", "🎓 수업 그룹","👨‍🏫 선생님 배정", "📅 일정 관리", "👨‍👩‍👧 보호자 관리","📞 문의 관리", "🔹 출석 체크", "📈 리포트", "🔐 사용자 관리"],
            horizontal=True,
            key="main_nav_radio"
        )
    
    # 🆕 Supabase 연결 상태 확인 및 경고
    if not supabase_mgr.client:
        st.warning("⚠️ Supabase에 연결되지 않았습니다. 실시간 데이터 저장 및 조회가 제한될 수 있습니다. (.env 파일을 확인해주세요)")
        
    # 모든 탭에서 공통으로 사용할 사용자 데이터 로드
    try:
        df_users = auth.load_users()
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        df_users = pd.DataFrame() # 빈 데이터프레임으로 대체하여 크래시 방지

    st.markdown("---")
    
    # ==========================================
    # 📊 대시보드
    # ==========================================
    if tab == "📊 대시보드":
        st.header("📊 대시보드")
           # 🆕 자동 결석 처리 결과 표시
        if st.session_state.get('auto_absence_count', 0) > 0:
            with st.expander("✅ 자동 결석 처리 완료", expanded=True):
                st.success(f"""
                **최근 수업 자동 결석 처리:**
                - 처리된 수업: {st.session_state.get('auto_absence_count', 0)}개
                - 결석 처리: {st.session_state.get('auto_absence_total', 0)}명
                
                💡 수업 종료 후 미출석 학생이 자동으로 결석 처리되었습니다.
                """)
                
                if st.button("확인", key="confirm_auto_absence"):
                    st.session_state['auto_absence_count'] = 0
                    st.rerun()
        
        df_schedule = get_schedule_df()
        # df_schedule['date'] is already a string 'YYYY-MM-DD' from get_schedule_df()
        today_sched = df_schedule[df_schedule['date'] == get_today_kst().isoformat()]
        
        if not today_sched.empty:
            st.markdown(f"### 📅 오늘의 수업 ({len(today_sched)}개)")
            for idx, row in today_sched.iterrows():
                st.success(f"**{row['start']} ~ {row['end']}** | {row['session']}")
        else:
            st.info("🔭 오늘 예정된 수업이 없습니다.")
        
        df_groups = load_class_groups()
        if not df_groups.empty:
            total_sessions = len(df_schedule)
            st.info(f"🎓 **전체 등록된 수업 세션:** {total_sessions}개 (총 {len(df_groups)}개 그룹)")
        
        st.markdown("###")
        
        col1, col2, col3, col4 = st.columns(4)
        
        total_students = len(st.session_state.attendees)
        
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">전체 학생</div>
                <div class="stat-number">{total_students}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            try:
                if check_flask_connection():
                    resp = requests.get(f"http://localhost:{FLASK_PORT}/attendance_log", timeout=2)
                    today_attendance = len(resp.json()) if resp.status_code == 200 else 0
                else:
                    today_attendance = 0
            except:
                today_attendance = 0
            
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">오늘 출석</div>
                <div class="stat-number" style="color: #4CAF50;">{today_attendance}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">수업 그룹</div>
                <div class="stat-number" style="color: #667eea;">{len(df_groups)}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            # df_users = auth.load_users() # 상단 공통 로드로 대체
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">전체 사용자</div>
                <div class="stat-number" style="color: #764ba2;">{len(df_users)}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("###")
        
        st.subheader("⚡ 빠른 실행")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("👥 학생 관리", use_container_width=True, key="quick_student"):
                st.session_state['selected_tab'] = '👥 학생 관리'
                st.rerun()
        
        with col2:
            if st.button("🔹 출석 시작", use_container_width=True, key="quick_attendance"):
                st.session_state['selected_tab'] = '🔹 출석 체크'
                st.rerun()
        
        with col3:
            if st.button("📈 리포트", use_container_width=True, key="quick_report"):
                st.session_state['selected_tab'] = '📈 리포트'
                st.rerun()
    
    # ==========================================
    # 👥 학생 관리 (수정 기능 포함)
    # ==========================================
    elif tab == "👥 학생 관리":
        st.header("👥 학생 관리")
        
        if not check_permission(user['role'], 'can_manage_students'):
            st.warning("⚠️ 학생 관리 권한이 없습니다. (읽기 전용)")
        
        # 학생 추가
        if check_permission(user['role'], 'can_manage_students'):
            if 'last_added_student' in st.session_state and st.session_state['last_added_student']:
                student_info = st.session_state['last_added_student']
                st.success(f"✅ {student_info['name']} 학생이 추가되었습니다!")
                
                if student_info['user_created']:
                    st.info(f"""
                    🎉 **학생 로그인 계정이 자동 생성되었습니다!**
                    
                    📋 **로그인 정보:**
                    - 아이디: `{student_info['username']}`
                    - 비밀번호: `student123`
                    """)
                
                if st.button("✔ 확인", key="clear_message"):
                    st.session_state['last_added_student'] = None
                    st.rerun()
                
                st.markdown("---")
            
            with st.expander("➕ 새 학생 추가", expanded=False):
                add_method = st.radio("추가 방법", ["직접 입력", "CSV 업로드"], horizontal=True, key="student_add_choice")
                
                if add_method == "직접 입력":
                    new_name = st.text_input("학생명", placeholder="홍길동", key="new_student_name_input")
                    new_phone = st.text_input("전화번호 (선택)", placeholder="010-1234-5678", key="new_student_phone_input")
                    new_school = st.text_input("학교명", placeholder="서울초등학교", key="new_student_school_input")
                    
                    if st.button("➕ 학생 추가", use_container_width=True, key="btn_add_student_manual"):
                        if new_name:
                            if new_name not in st.session_state.attendees:
                                normalized_phone = normalize_phone(new_phone)
                                
                                st.session_state.attendees.append(new_name)
                                st.session_state.phones[new_name] = normalized_phone
                                st.session_state.schools[new_name] = new_school
                                
                                username = f"student_{new_name}"
                                user_created = create_user(
                                    username=username,
                                    password="student123",
                                    role="student",
                                    name=new_name,
                                    phone=normalized_phone,
                                    student_id=new_name
                                )
                                
                                if save_students_from_session():
                                    st.session_state['last_added_student'] = {
                                        'name': new_name,
                                        'username': username,
                                        'user_created': user_created
                                    }
                                    st.rerun()
                            else:
                                st.warning("이미 등록된 학생입니다.")
                        else:
                            st.error("학생명을 입력해주세요.")
                
                else:
                    st.info("💡 **파일 작성 가이드:** 1열(A열)=이름, 2열(B열)=학교, 3열(C열)=전화번호, 4열(D열)=보호자명, 5열(E열)=보호자 연락처 순으로 작성해주세요. 첫 번째 행(1행)은 제목 행으로 무시됩니다.")
                    uploaded_file = st.file_uploader("명단 파일 업로드 (CSV, Excel)", type=['csv', 'xlsx', 'xls'], key="admin_student_batch_upload")
                    
                    if uploaded_file:
                        try:
                            # 1. 파일 확장자에 따른 읽기
                            if uploaded_file.name.lower().endswith('.csv'):
                                try:
                                    df_upload = pd.read_csv(uploaded_file, encoding='utf-8-sig')
                                except UnicodeDecodeError:
                                    uploaded_file.seek(0)
                                    df_upload = pd.read_csv(uploaded_file, encoding='cp949')
                            else:
                                df_upload = pd.read_excel(uploaded_file)
                            
                            added = 0
                            updated = 0
                            
                            # 2. 데이터 순회 (1행 제목은 pandas가 자동 제외)
                            for _, row in df_upload.iterrows():
                                # 1열: 이름
                                name = str(row.iloc[0]).strip() if not pd.isna(row.iloc[0]) else ""
                                # 2열: 학교 (없을 수도 있음)
                                school = str(row.iloc[1]).strip() if len(row) > 1 and not pd.isna(row.iloc[1]) else ""
                                # 3열: 전화번호 (없을 수도 있음)
                                phone = str(row.iloc[2]).strip() if len(row) > 2 and not pd.isna(row.iloc[2]) else ""
                                # 4열: 보호자명 (없을 수도 있음)
                                parent_name = str(row.iloc[3]).strip() if len(row) > 3 and not pd.isna(row.iloc[3]) else ""
                                # 5열: 보호자 연락처 (없을 수도 있음)
                                parent_phone = str(row.iloc[4]).strip() if len(row) > 4 and not pd.isna(row.iloc[4]) else ""
                                
                                if name and name.lower() != 'nan':
                                    normalized_phone = normalize_phone(phone)
                                    
                                    is_new = name not in st.session_state.attendees
                                    if is_new:
                                        st.session_state.attendees.append(name)
                                        added += 1
                                    else:
                                        updated += 1
                                        
                                    st.session_state.phones[name] = normalized_phone
                                    st.session_state.schools[name] = school
                                    
                                    create_user(
                                        username=f"student_{name}",
                                        password="student123",
                                        role="student",
                                        name=name,
                                        phone=normalized_phone,
                                        student_id=name
                                    )
                                    
                                    # 보호자 계정 자동 생성 (없으면 생성됨)
                                    if parent_name and parent_name.lower() != 'nan':
                                        norm_parent_phone = normalize_phone(parent_phone)
                                        create_user(
                                            username=f"parent_{parent_name}",
                                            password="parent123",
                                            role="parent",
                                            name=parent_name,
                                            phone=norm_parent_phone,
                                            student_id=name
                                        )
                            
                            if added > 0 or updated > 0:
                                save_students_from_session()
                                st.success(f"✅ 총 {added}명 신규 추가, {updated}명 정보(보호자 정보 포함) 업데이트 완료!")
                                st.rerun()
                            else:
                                st.warning("추가할 수 있는 새로운 학생 데이터가 없습니다. (빈 파일입니다)")
                                st.info("💡 아래는 업로드된 파일의 형태입니다. 'A열(1열)'에 이름이 있는지 확인해주세요.")
                                st.dataframe(df_upload.head())
                        except Exception as e:
                            st.error(f"파일 처리 중 오류가 발생했습니다: {e}")
        
        st.markdown("###")
        
        # 학생 목록 (수정 기능 포함)
        st.subheader(f"📋 전체 학생 ({len(st.session_state.attendees)}명)")
        
        if st.session_state.attendees:
            if 'editing_student' not in st.session_state:
                st.session_state.editing_student = None
            
            for idx, name in enumerate(st.session_state.attendees):
                phone = st.session_state.phones.get(name, '')
                school = st.session_state.schools.get(name, '')
                
                student_groups = get_student_groups(name)
                df_groups = load_class_groups()
                
                group_names = []
                if student_groups:
                    for gid in student_groups:
                        group_info = df_groups[df_groups['group_id'] == gid]
                        if not group_info.empty:
                            group_names.append(group_info.iloc[0]['group_name'])
                
                # 편집 모드
                if st.session_state.editing_student == name:
                    st.markdown(f"""
                    <div style="background: #e3f2fd; padding: 20px; border-radius: 10px; 
                                margin: 10px 0; border-left: 5px solid #2196F3;">
                        <h3 style="margin: 0 0 10px 0; color: #1565C0;">✏️ {name} 정보 수정</h3>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    with st.form(f"edit_form_{idx}"):
                        col_e1, col_e2 = st.columns(2)
                        
                        with col_e1:
                            edited_name = st.text_input("학생명", value=name, key=f"edit_name_{idx}")
                        
                        with col_e2:
                            edited_school = st.text_input("학교명", value=school, key=f"edit_school_{idx}")
                        
                        edited_phone = st.text_input(
                            "전화번호",
                            value=phone,
                            placeholder="010-1234-5678",
                            key=f"edit_phone_{idx}"
                        )
                        
                        st.caption("💡 전화번호는 010-1234-5678 형식으로 자동 변환됩니다.")
                        
                        col_submit, col_cancel = st.columns(2)
                        
                        with col_submit:
                            submitted = st.form_submit_button("💾 저장", use_container_width=True, type="primary", key=f"save_edit_student_{idx}")
                        
                        with col_cancel:
                            cancelled = st.form_submit_button("❌ 취소", use_container_width=True, key=f"cancel_edit_student_{idx}")
                        
                        if submitted:
                            normalized_phone = normalize_phone(edited_phone)
                            
                            if edited_name != name and edited_name in st.session_state.attendees:
                                st.error("❌ 이미 존재하는 학생 이름입니다.")
                            else:
                                st.session_state.attendees.remove(name)
                                if name in st.session_state.phones:
                                    del st.session_state.phones[name]
                                if name in st.session_state.schools:
                                    del st.session_state.schools[name]
                                
                                st.session_state.attendees.append(edited_name)
                                st.session_state.phones[edited_name] = normalized_phone
                                st.session_state.schools[edited_name] = edited_school
                                
                                if save_students_from_session():
                                    st.session_state.editing_student = None
                                    st.success(f"✅ {edited_name} 정보가 수정되었습니다!")
                                    st.rerun()
                        
                        if cancelled:
                            st.session_state.editing_student = None
                            st.rerun()
                    
                    st.markdown("---")
                
                # 일반 표시 모드
                else:
                    col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                    
                    with col1:
                        st.markdown(f"**{name}**")
                        if phone:
                            st.caption(f"📞 {phone}")
                        else:
                            st.caption("📞 전화번호 없음")
                        if school:
                            st.caption(f"🏫 {school}")
                        if group_names:
                            st.caption(f"🎓 {', '.join(group_names)}")
                        else:
                            st.caption("⚠️ 미배정")
                    
                    with col2:
                        buf = io.BytesIO()
                        qrcode.make(name).save(buf, 'PNG')
                        buf.seek(0)
                        st.download_button(
                            "📱 QR",
                            buf.getvalue(),
                            file_name=f"{name}_QR.png",
                            mime='image/png',
                            key=f"admin_qr_download_{idx}_{name}",
                            use_container_width=True
                        )
                    
                    with col3:
                        if check_permission(user['role'], 'can_manage_students'):
                            if st.button("✏️", key=f"edit_{idx}", help="수정", use_container_width=True):
                                st.session_state.editing_student = name
                                st.rerun()
                    
                    with col4:
                        if check_permission(user['role'], 'can_manage_students'):
                            if st.button("🗑️", key=f"del_{idx}", help="삭제", use_container_width=True):
                                st.session_state.attendees.remove(name)
                                if name in st.session_state.phones:
                                    del st.session_state.phones[name]
                                if name in st.session_state.schools:
                                    del st.session_state.schools[name]
                                save_students_from_session()
                                st.success(f"{name} 학생이 삭제되었습니다.")
                                st.rerun()
            
            st.markdown("###")
            
            # 전화번호 일괄 수정
            if check_permission(user['role'], 'can_manage_students'):
                with st.expander("🔧 전화번호 일괄 수정 (0으로 시작하도록)"):
                    st.info("""
                    **전화번호 일괄 수정:**
                    - 1로 시작하는 전화번호를 010으로 자동 변환합니다.
                    - 형식: 010-1234-5678
                    """)
                    
                    needs_fix = []
                    for name in st.session_state.attendees:
                        phone = st.session_state.phones.get(name, '')
                        phone_str = str(phone) if phone else ''
                        
                        if phone_str and phone_str.strip() != '' and not phone_str.startswith('0'):
                            needs_fix.append((name, phone_str, normalize_phone(phone_str)))
                    
                    if needs_fix:
                        st.warning(f"⚠️ 수정이 필요한 전화번호: {len(needs_fix)}개")
                        
                        for name, old_phone, new_phone in needs_fix[:5]:
                            st.markdown(f"- {name}: `{old_phone}` → `{new_phone}`")
                        
                        if len(needs_fix) > 5:
                            st.caption(f"... 외 {len(needs_fix) - 5}개")
                        
                        if st.button("🔧 일괄 수정 실행", use_container_width=True, type="primary", key="btn_fix_phones_batch"):
                            for name, old_phone, new_phone in needs_fix:
                                st.session_state.phones[name] = new_phone
                            
                            if save_students_from_session():
                                st.success(f"✅ {len(needs_fix)}개의 전화번호가 수정되었습니다!")
                                st.balloons()
                                st.rerun()
                    else:
                        st.success("✅ 모든 전화번호가 올바른 형식입니다!")
            
            st.markdown("###")
            
            if st.button("📦 전체 QR ZIP 다운로드", use_container_width=True, key="btn_download_all_qr"):
                with st.spinner("ZIP 파일 생성 중..."):
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                        for name in st.session_state.attendees:
                            qr_buffer = io.BytesIO()
                            qrcode.make(name).save(qr_buffer, 'PNG')
                            zip_file.writestr(f"{name}_QR.png", qr_buffer.getvalue())
                    
                    zip_buffer.seek(0)
                    st.download_button(
                        "📥 ZIP 다운로드",
                        zip_buffer.getvalue(),
                        file_name=f"QR_Codes_{get_today_kst()}.zip",
                        mime='application/zip',
                        use_container_width=True,
                        key="download_all_qr_zip"
                    )
        else:
            st.info("등록된 학생이 없습니다.")
    
    # ==========================================
    # 🎓 수업 그룹
    # ==========================================
    elif tab == "🎓 수업 그룹":
        st.header("🎓 수업 그룹(반) 관리")
        
        # 🚀 실시간 장애 진단 도구
        with st.sidebar.expander("🛠️ 긴급 진단 도구", expanded=True):
            is_live = st.checkbox("🚀 실시간 DB 모드 (모든 캐시 무시)", value=False)
            if st.button("🧹 전역 캐시 비우기"):
                st.cache_data.clear()
                st.rerun()
        
        # 데이터 로드 (실시간 모드 시 즉시 로드)
        df_groups = load_class_groups(force_live=is_live)
        raw_count = len(df_groups)
        raw_db_data = df_groups.to_dict('records')
        
        # 🏁 필터링 처리
        if is_live:
            st.warning("⚠️ **실시간 진단 모드 활성화:** 필터가 해제된 전체 데이터입니다.")
            hide_ended = False
        else:
            col_hide1, col_hide2 = st.columns([3, 1])
            with col_hide2:
                hide_ended = st.checkbox("🏁 종료된 수업 숨기기", value=False, key="hide_passed_groups")
        
        # 필터링 결과 요약
        st.sidebar.metric("DB 그룹 개수", f"{raw_count}개")
        st.sidebar.metric("현재 표시 개수", f"{len(df_groups)}개")
        
        if hide_ended:
            try:
                # 🆕 문자열 대 문자열로 가장 단순하고 확실하게 비교
                # DB의 end_date가 'YYYY-MM-DD' 형식이면 안전하게 작동함
                df_groups = df_groups[df_groups['end_date'].astype(str) >= today_str].copy()
            except Exception as e:
                logger.error(f"Simple filtering failed: {e}")
                pass
        
        if check_permission(user['role'], 'can_manage_schedule'):
            # 🔗 일정 동기화(복구) 기능 추가
            with st.expander("🔄 시스템 관리 및 일정 복구", expanded=False):
                st.info("💡 **일정 동기화**: 로컬 설정(class_groups.csv)을 기준으로 Supabase의 일정을 동기화합니다. 누락된 일정을 복구하거나 잘못된 시간을 바로잡습니다.")
                if st.button("🚀 모든 수업 일정 강제 동기화 (Supabase 복구)", use_container_width=True, key="sync_all_schedules_btn"):
                    with st.spinner("일정 데이터를 동기화하는 중..."):
                        
                        sync_count = 0
                        fix_count = 0
                        
                        # 현재 Supabase 일정 로드
                        existing_schedules = get_schedule_df()
                        existing_map = {} # (date, class_name) -> id
                        for _, s in existing_schedules.iterrows():
                            existing_map[(s['date'], s['session'])] = s['id']
                        
                        # 교사 매핑 로드
                        df_teacher_groups = load_teacher_groups()
                        # df_users = auth.load_users() # 상단 공통 로드로 대체
                        teacher_map = {}
                        if not df_teacher_groups.empty and not df_users.empty:
                            for _, tg in df_teacher_groups.iterrows():
                                u_row = df_users[df_users['username'] == tg['teacher_username']]
                                if not u_row.empty:
                                    teacher_map[int(tg['group_id'])] = u_row.iloc[0]['name']
    
                        batch_inserts = []
                        for _, group in df_groups.iterrows():
                            g_id = int(group['group_id'])
                            t_name = teacher_map.get(g_id, None)
                            weekdays = [int(w) for w in str(group['weekdays']).split(',')]
                            z_id = group.get('zoom_meeting_id', '')
                            
                            # Generate all expected sessions for this group
                            current_date = pd.to_datetime(group['start_date']).date()
                            end_date = pd.to_datetime(group['end_date']).date()
                            
                            while current_date <= end_date:
                                if current_date.weekday() in weekdays:
                                    session_name = group['group_name']
                                    date_str = current_date.isoformat()
                                    start_t = group['start_time']
                                    end_t = group['end_time']
                                    
                                    st_dt_str = f"{date_str}T{start_t}:00+09:00"
                                    en_dt_str = f"{date_str}T{end_t}:00+09:00"
                                    
                                    already_exists = any(
                                        session_name in key[1] 
                                        for key in existing_map.keys() 
                                        if key[0] == date_str
                                    )
                                    
                                    if not already_exists:
                                        batch_inserts.append({
                                            'class_name': session_name,
                                            'start_time': st_dt_str,
                                            'end_time': en_dt_str,
                                            'teacher_name': t_name,
                                            'zoom_meeting_id': z_id
                                        })
                                current_date += timedelta(days=1)
                        
                        if batch_inserts:
                            # Split batch if too large (Supabase limit)
                            chunk_size = 50
                            for i in range(0, len(batch_inserts), chunk_size):
                                supabase_mgr.client.table('schedule').insert(batch_inserts[i:i+chunk_size]).execute()
                            sync_count = len(batch_inserts)
                        
                        if sync_count > 0:
                            st.success(f"✅ 동기화 완료! {sync_count}개의 누락된 일정을 복구했습니다.")
                        else:
                            st.info("모든 일정이 이미 최신 상태입니다.")
                        st.rerun()
    
        if not check_permission(user['role'], 'can_manage_schedule'):
            st.warning("⚠️ 수업 관리 권한이 없습니다.")
        else:
            with st.expander("➕ 새 수업 그룹 생성", expanded=False):
                st.markdown("### 📋 그룹 정보")
                group_name = st.text_input("그룹명 (예: A반, 초급반)", placeholder="A반", key="create_group_name_input")
                
                st.markdown("### 📅 수업 일정")
                col1, col2 = st.columns(2)
                
                with col1:
                    group_start_date = st.date_input("시작 날짜", get_today_kst(), key="create_group_start_date")
                    group_end_date = st.date_input("종료 날짜", get_today_kst() + timedelta(days=90), key="create_group_end_date")
                
                with col2:
                    group_start_time = st.time_input("수업 시작 시간", time(9, 0), step=timedelta(minutes=5), key="create_group_start_time")
                    group_end_time = st.time_input("수업 종료 시간", time(10, 0), step=timedelta(minutes=5), key="create_group_end_time")
                
                st.markdown("### 📆 수업 요일")
                weekday_names = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
                group_weekdays = st.multiselect(
                    "수업 요일 선택",
                    options=list(range(7)),
                    default=[0, 2, 4],
                    format_func=lambda x: weekday_names[x],
                    key="create_group_weekdays_select"
                )
                
                st.markdown("### 🕐 총 교육시간 설정")
                
                if group_weekdays and group_start_date and group_end_date:
                    start_datetime = datetime.combine(get_today_kst(), group_start_time)
                    end_datetime = datetime.combine(get_today_kst(), group_end_time)
                    duration_hours = (end_datetime - start_datetime).total_seconds() / 3600
                    
                    estimated_classes = 0
                    current_date = group_start_date
                    while current_date <= group_end_date:
                        if current_date.weekday() in group_weekdays:
                            estimated_classes += 1
                        current_date += timedelta(days=1)
                    
                    auto_total_hours = duration_hours * estimated_classes
                    
                    st.info(f"""
                    📊 **자동 계산된 정보**
                    - 1회 수업 시간: {duration_hours:.1f}시간
                    - 예상 수업 횟수: {estimated_classes}회
                    - 총 교육시간: {auto_total_hours:.1f}시간
                    """)
                    
                    col_auto, col_manual = st.columns(2)
                    
                    with col_auto:
                        use_auto = st.checkbox("자동 계산 사용", value=True, key="create_group_use_auto_hours")
                    
                    with col_manual:
                        if not use_auto:
                            manual_hours = st.number_input(
                                "총 교육시간 (시간)",
                                min_value=0.0,
                                max_value=1000.0,
                                value=auto_total_hours,
                                step=0.5,
                                key="create_group_manual_hours_input"
                            )
                            final_total_hours = manual_hours
                        else:
                            final_total_hours = auto_total_hours
                    
                    group_zoom_id = st.text_input("Zoom 회의 ID (선택 사항)", placeholder="예: 1234567890", key="new_group_zoom_id")
                    
                    st.success(f"✅ 설정된 총 교육시간: **{final_total_hours:.1f}시간**")
                else:
                    final_total_hours = 1.0
                    st.warning("⚠️ 날짜와 요일을 먼저 설정해주세요.")
                
                st.markdown("###")
                
                if st.button("🎓 수업 그룹 생성", use_container_width=True, type="primary", key="btn_create_class_group"):
                    if not group_name:
                        st.error("그룹명을 입력해주세요.")
                    elif not group_weekdays:
                        st.error("최소 1개 이상의 요일을 선택해주세요.")
                    else:
                        # 생성 시도 알림
                        with st.spinner("수업 그룹을 생성하는 중..."):
                            new_group_id = create_class_group(
                                group_name=group_name,
                                weekdays=group_weekdays,
                                start_time=group_start_time,
                                end_time=group_end_time,
                                start_date=group_start_date,
                                end_date=group_end_date,
                                total_hours=final_total_hours,
                                zoom_meeting_id=group_zoom_id
                            )
                        
                        if new_group_id:
                            new_schedules = generate_recurring_schedule(
                                start_date=group_start_date,
                                end_date=group_end_date,
                                weekdays=group_weekdays,
                                start_time=group_start_time,
                                end_time=group_end_time,
                                session_prefix=group_name
                            )
                            
                            if not new_schedules.empty:
                                batch_inserts = []
                                for _, r_sched in new_schedules.iterrows():
                                    st_dt = f"{r_sched['date']}T{r_sched['start']}:00"
                                    en_dt = f"{r_sched['date']}T{r_sched['end']}:00"
                                    batch_inserts.append({
                                        'class_name': r_sched['session'],
                                        'start_time': f"{st_dt}+09:00",
                                        'end_time': f"{en_dt}+09:00",
                                        'zoom_meeting_id': group_zoom_id
                                    })
                                
                                try:
                                    if batch_inserts:
                                        res_sched = supabase_mgr.client.table('schedule').insert(batch_inserts).execute()
                                        if not res_sched.data:
                                            st.warning("⚠️ 수업 그룹은 생성되었으나, 세부 일정(Schedule) 데이터 정합성 확인이 필요합니다.")
                                except Exception as e:
                                    st.error(f"❌ 세부 일정(Schedule) 저장 실패: {e}")
                                    logger.error(f"Failed to batch insert schedule: {e}")
                            
                            st.success(f"✅ {group_name} 그룹이 생성되었습니다! (총 {len(new_schedules)}회)")
                            st.cache_data.clear() # 캐시 삭제
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(f"❌ 수업 그룹 생성에 실패했습니다: {error_info}")
                            with st.expander("🛠️ 상세 에러 진단 정보", expanded=True):
                                st.warning("데이터베이스 저장 시도 중 오류가 발생했습니다.")
                                st.write("실제로 전송된 데이터:")
                                st.json({
                                    'group_name': group_name,
                                    'start_date': group_start_date.isoformat(),
                                    'end_date': group_end_date.isoformat(),
                                    'weekdays': group_weekdays
                                })
                                st.info("💡 팁: 동일한 수업 정보가 이미 있거나, 데이터베이스 권한(RLS) 문제일 수 있습니다.")
        
        st.markdown("---")
        st.markdown("### 📋 전체 수업 그룹")
        
        if not df_groups.empty:
            for idx, group in df_groups.iterrows():
                weekdays_list = [int(x) for x in str(group['weekdays']).split(',')]
                weekday_names_kr = ["월", "화", "수", "목", "금", "토", "일"]
                weekdays_display = ', '.join([weekday_names_kr[d] for d in weekdays_list])
                
                students_in_group = get_students_in_group(group['group_id'])
                total_hours = group.get('total_hours', 1.0)
                
                col_main, col_delete = st.columns([5, 1])
                
                with col_main:
                    st.markdown(f"""
                    <div class="group-card">
                        <h3>🎓 {group['group_name']}</h3>
                        <p>📅 {weekdays_display}요일 | ⏰ {group['start_time']} ~ {group['end_time']}</p>
                        <p>📆 {group['start_date']} ~ {group['end_date']}</p>
                        <p>🕐 총 교육시간: {total_hours:.1f}시간</p>
                        <p>👥 등록 학생: {len(students_in_group)}명</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_delete:
                    if check_permission(user['role'], 'can_manage_schedule'):
                        if st.button("🗑️ 삭제", key=f"delete_group_{group['group_id']}", use_container_width=True):
                            if delete_class_group(group['group_id']):
                                st.success(f"{group['group_name']} 그룹이 삭제되었습니다.")
                                st.rerun()
                
                with st.expander(f"⚙️ {group['group_name']} 상세 관리 (학생/Zoom 연동)"):
                    st.markdown("##### 🌐 Zoom 회의 연동")
                    
                    current_zoom_id = ""
                    try:
                        from supabase_client import supabase_mgr
                        sched_data = supabase_mgr.client.table('schedule').select('zoom_meeting_id').like('class_name', f"{group['group_name']}%").limit(1).execute().data
                        if sched_data and sched_data[0].get('zoom_meeting_id'):
                            current_zoom_id = str(sched_data[0]['zoom_meeting_id'])
                    except:
                        pass
                    
                    col_z1, col_z2 = st.columns([3, 1])
                    with col_z1:
                        new_zoom_id = st.text_input("Zoom 회의 ID", value=current_zoom_id, key=f"zoom_id_{group['group_id']}", label_visibility="collapsed", placeholder="Zoom 회의 ID 입력 (예: 1234567890)")
                    with col_z2:
                        if st.button("저장", key=f"btn_zoom_{group['group_id']}", use_container_width=True):
                            try:
                                # 1. Supabase 업데이트
                                from supabase_client import supabase_mgr
                                supabase_mgr.client.table('schedule').update({'zoom_meeting_id': new_zoom_id}).like('class_name', f"{group['group_name']}%").execute()
                                
                                # 2. 로컬 CSV 업데이트 (템플릿 보존)
                                df_groups_all = load_class_groups()
                                if 'zoom_meeting_id' not in df_groups_all.columns:
                                    df_groups_all['zoom_meeting_id'] = ''
                                df_groups_all['zoom_meeting_id'] = df_groups_all['zoom_meeting_id'].astype(object)
                                df_groups_all.loc[df_groups_all['group_id'] == group['group_id'], 'zoom_meeting_id'] = str(new_zoom_id)
                                save_class_groups(df_groups_all)
                                
                                st.success("✅ Zoom ID가 동기화되었습니다!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"오류: {e}")
                    
                    st.markdown("---")
                    
                    if students_in_group:
                        st.markdown("##### 현재 등록된 학생")
                        for student in students_in_group:
                            col_a, col_b = st.columns([4, 1])
                            with col_a:
                                st.text(f"👤 {student}")
                            with col_b:
                                if st.button("제거", key=f"remove_{group['group_id']}_{student}"):
                                    if remove_student_from_group(student, group['group_id']):
                                        st.success(f"{student} 제거됨")
                                        st.rerun()
                    else:
                        st.info("등록된 학생이 없습니다.")
                    
                    st.markdown("---")
                    st.markdown("##### 학생 추가")
                    
                    available_students = [s for s in st.session_state.attendees if s not in students_in_group]
                    
                    if available_students:
                        student_to_add = st.selectbox(
                            "추가할 학생 선택",
                            available_students,
                            key=f"add_student_{group['group_id']}"
                        )
                        
                        if st.button("➕ 학생 추가", key=f"btn_add_{group['group_id']}", use_container_width=True):
                            if add_student_to_group(student_to_add, group['group_id']):
                                st.success(f"✅ {student_to_add}을(를) {group['group_name']}에 추가했습니다!")
                                st.rerun()
                    else:
                        st.info("모든 학생이 이미 이 그룹에 등록되어 있습니다.")
                    
                    st.markdown("---")
                    st.markdown("##### 엑셀/CSV 명단으로 일괄 추가")
                    st.info("💡 1열(A열)에 학생 이름이 있는 파일을 업로드하면 해당 학생들을 이 수업 그룹에 일괄 추가합니다.")
                    
                    group_uploaded_file = st.file_uploader("명단 업로드 (CSV, Excel)", type=['csv', 'xlsx', 'xls'], key=f"group_upload_{group['group_id']}")
                    if group_uploaded_file:
                        try:
                            if group_uploaded_file.name.lower().endswith('.csv'):
                                try:
                                    df_group = pd.read_csv(group_uploaded_file, encoding='utf-8-sig')
                                except:
                                    group_uploaded_file.seek(0)
                                    df_group = pd.read_csv(group_uploaded_file, encoding='cp949')
                            else:
                                df_group = pd.read_excel(group_uploaded_file)
                            
                            group_added = 0
                            for _, row in df_group.iterrows():
                                g_name = str(row.iloc[0]).strip() if not pd.isna(row.iloc[0]) else ""
                                if g_name and g_name.lower() != 'nan' and g_name in st.session_state.attendees and g_name not in students_in_group:
                                    if add_student_to_group(g_name, group['group_id']):
                                        group_added += 1
                            
                            if group_added > 0:
                                st.success(f"✅ {group_added}명의 학생이 이 수업 그룹에 추가되었습니다!")
                                st.rerun()
                            else:
                                st.warning("추가할 수 있는 학생이 없습니다. (사전에 '학생 관리'에서 등록된 학생만 추가됩니다. 파일의 학생 이름이 정확히 일치하는지 확인해 주세요.)")
                        except Exception as e:
                            st.error(f"파일 처리 오류: {e}")
                
                st.markdown("###")
        # 🆕 초정밀 디버그 도구
        with st.expander("🛠️ 데이터베이스 원본 상세 분석 (Raw JSON)", expanded=False):
            st.markdown(f"**현재 DB 레코드 총 개수:** `{len(df_groups)}개`")
            st.write("아래 JSON 데이터를 복사해서 주시면 정확한 분석이 가능합니다.")
            st.json(raw_db_data)
            
            if st.button("🔄 즉시 강제 새로고침 (DB 재조회)"):
                st.rerun()
    # ==========================================
    # 👨‍🏫 선생님 배정
    # ==========================================
    elif tab == "👨‍🏫 선생님 배정":
        st.header("👨‍🏫 선생님 수업 배정")
        
        if not check_permission(user['role'], 'can_manage_schedule'):
            st.warning("⚠️ 수업 관리 권한이 없습니다.")
            st.stop()
        
        # 선생님 목록 로드
        teachers = df_users[df_users['role'].isin(['teacher', 'admin'])].copy()
        
        # 수업 그룹 목록 로드
        df_groups = load_class_groups()
        
        if teachers.empty:
            st.warning("⚠️ 등록된 선생님이 없습니다.")
            st.info("💡 '사용자 관리' 탭에서 선생님 계정을 먼저 생성해주세요.")
            st.stop()
        
        if df_groups.empty:
            st.warning("⚠️ 등록된 수업 그룹이 없습니다.")
            st.info("💡 '수업 그룹' 탭에서 수업을 먼저 생성해주세요.")
            st.stop()
        
        st.success(f"👨‍🏫 **선생님:** {len(teachers)}명 | 🎓 **수업 그룹:** {len(df_groups)}개")
        
        st.markdown("---")
        
        # 선생님별 배정 관리
        for idx, teacher in teachers.iterrows():
            teacher_name = teacher['name']
            teacher_username = teacher['username']
            role_display = get_role_display_name(teacher['role'])
            
            # 현재 배정 현황
            assignments = get_teacher_assignments(teacher_username)
            regular_groups = assignments['regular']
            substitute_groups = assignments['substitute']
            
            # 확장 가능한 카드
            with st.expander(
                f"👤 {teacher_name} ({role_display}) - 담당: {len(regular_groups)}개 수업",
                expanded=False
            ):
                st.markdown(f"""
                <div style="background: #f0f7ff; padding: 15px; border-radius: 10px; 
                            border-left: 4px solid #2196F3; margin-bottom: 15px;">
                    <div style="font-weight: bold; font-size: 18px; color: #1565C0;">
                        👨‍🏫 {teacher_name}
                    </div>
                    <div style="color: #666; margin-top: 5px;">
                        🆔 {teacher_username} | 📧 {teacher.get('email', 'N/A')}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 탭으로 정규/대타 구분
                tab_regular, tab_substitute, tab_assign = st.tabs([
                    f"📚 정규 담당 ({len(regular_groups)}개)",
                    f"🔄 대타 수업 ({len(substitute_groups)}개)",
                    "➕ 새 배정"
                ])
                
                # 📚 정규 담당 수업
                with tab_regular:
                    st.info("💡 **정규 담당:** 이 선생님이 해당 반의 고정 강사로 지정됩니다. (모든 수업 일정에 반영)")
                    if regular_groups:
                        st.markdown("##### 현재 담당 중인 수업")
                        
                        for group_id in regular_groups:
                            group_info = df_groups[df_groups['group_id'] == group_id]
                            
                            if not group_info.empty:
                                group = group_info.iloc[0]
                                
                                col_info, col_action = st.columns([4, 1])
                                
                                with col_info:
                                    st.markdown(f"""
                                    <div style="background: white; padding: 12px; border-radius: 8px; 
                                                margin: 5px 0; border-left: 3px solid #4CAF50;">
                                        <div style="font-weight: bold; color: #333;">
                                            🎓 {group['group_name']}
                                        </div>
                                        <div style="color: #666; font-size: 13px; margin-top: 3px;">
                                            ⏰ {group['start_time']} ~ {group['end_time']} | 
                                            🕐 총 {group['total_hours']}시간
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                with col_action:
                                    if st.button(
                                        "🗑️ 해제",
                                        key=f"remove_regular_{teacher_username}_{group_id}",
                                        use_container_width=True
                                    ):
                                        if remove_teacher_assignment(teacher_username, group_id):
                                            st.success(f"✅ {group['group_name']} 배정이 해제되었습니다.")
                                            st.rerun()
                                        else:
                                            st.error("❌ 해제 중 오류가 발생했습니다.")
                    else:
                        st.info("📭 아직 담당 수업이 없습니다.")
                
                # 🔄 대타 수업
                with tab_substitute:
                    if substitute_groups:
                        st.markdown("##### 대타 수업 일정")
                        
                        # 날짜순 정렬
                        substitute_sorted = sorted(
                            substitute_groups,
                            key=lambda x: x['date'],
                            reverse=True
                        )
                        
                        for sub in substitute_sorted:
                            group_id = sub['group_id']
                            sub_date = sub['date']
                            
                            group_info = df_groups[df_groups['group_id'] == group_id]
                            
                            if not group_info.empty:
                                group = group_info.iloc[0]
                                
                                col_info, col_action = st.columns([4, 1])
                                
                                with col_info:
                                    st.markdown(f"""
                                    <div style="background: #fff8e1; padding: 12px; border-radius: 8px; 
                                                margin: 5px 0; border-left: 3px solid #FFA000;">
                                        <div style="font-weight: bold; color: #333;">
                                            🔄 {group['group_name']} (대타)
                                        </div>
                                        <div style="color: #666; font-size: 13px; margin-top: 3px;">
                                            📅 {sub_date} | 
                                            ⏰ {group['start_time']} ~ {group['end_time']}
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                with col_action:
                                    if st.button(
                                        "🗑️ 취소",
                                        key=f"remove_sub_{teacher_username}_{group_id}_{sub_date}",
                                        use_container_width=True
                                    ):
                                        if remove_teacher_assignment(teacher_username, group_id, sub_date):
                                            st.success(f"✅ 대타 수업이 취소되었습니다.")
                                            st.rerun()
                                        else:
                                            st.error("❌ 취소 중 오류가 발생했습니다.")
                    else:
                        st.info("📭 예정된 대타 수업이 없습니다.")
                
                # ➕ 새 배정
                with tab_assign:
                    st.markdown("##### 수업 배정하기")
                    
                    assignment_type = st.radio(
                        "배정 유형",
                        ["📚 정규 담당", "🔄 대타 수업"],
                        key=f"assign_type_{teacher_username}",
                        horizontal=True
                    )
                    
                    # 배정 가능한 그룹 (이미 정규 담당이 아닌 그룹)
                    available_groups = df_groups[~df_groups['group_id'].isin(regular_groups)]
                    
                    if not available_groups.empty:
                        selected_group = st.selectbox(
                            "🎓 수업 그룹 선택",
                            available_groups['group_id'].tolist(),
                            format_func=lambda x: available_groups[available_groups['group_id'] == x]['group_name'].iloc[0],
                            key=f"admin_group_select_{teacher_username}_{idx}"
                        )
                        
                        # 그룹 정보 표시
                        group_detail = available_groups[available_groups['group_id'] == selected_group].iloc[0]
                        
                        st.info(f"""
                        **선택한 수업:**
                        - 📚 {group_detail['group_name']}
                        - ⏰ {group_detail['start_time']} ~ {group_detail['end_time']}
                        - 🕐 총 {group_detail['total_hours']}시간
                        """)
                        
                        # 대타인 경우 날짜 선택
                        if assignment_type == "🔄 대타 수업":
                            substitute_date = st.date_input(
                                "📅 대타 날짜",
                                value=get_today_kst(),
                                key=f"sub_date_{teacher_username}"
                            )
                            
                            st.caption("💡 특정 날짜에만 해당 수업을 진행합니다.")
                        else:
                            substitute_date = None
                        
                        # 배정 버튼
                        if st.button(
                            f"✅ {teacher_name}에게 배정하기",
                            key=f"assign_btn_{teacher_username}",
                            use_container_width=True,
                            type="primary"
                        ):
                            success, message = assign_teacher_to_group(
                                teacher_username,
                                selected_group,
                                substitute_date.isoformat() if substitute_date else None
                            )
                            
                            if success:
                                st.success(f"✅ {message}")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error(f"❌ {message}")
                    else:
                        st.warning("⚠️ 배정 가능한 수업이 없습니다.")
                        st.caption("💡 모든 수업이 이미 정규 담당으로 배정되어 있습니다.")
            
            st.markdown("###")
        
        st.markdown("---")
        
        # 그룹별 담당 선생님 현황
        st.subheader("🎓 수업별 담당 선생님")
        
        for idx, group in df_groups.iterrows():
            group_teachers = get_group_teachers(group['group_id'])
            
            # 정규 담당과 대타 구분
            regular_teachers = [
                t for t in group_teachers 
                if pd.isna(t.get('date')) or t.get('date') == ''
            ]
            
            substitute_teachers = [
                t for t in group_teachers 
                if not (pd.isna(t.get('date')) or t.get('date') == '')
            ]
            
            with st.expander(
                f"🎓 {group['group_name']} - 담당: {len(regular_teachers)}명",
                expanded=False
            ):
                col_info, col_teachers = st.columns([2, 3])
                
                with col_info:
                    st.markdown(f"""
                    **수업 정보:**
                    - ⏰ {group['start_time']} ~ {group['end_time']}
                    - 📅 {group['start_date']} ~ {group['end_date']}
                    - 🕐 총 {group['total_hours']}시간
                    """)
                
                with col_teachers:
                    st.markdown("**📚 정규 담당 선생님:**")
                    if regular_teachers:
                        for teacher_assign in regular_teachers:
                            teacher_info = teachers[teachers['username'] == teacher_assign['teacher_username']]
                            if not teacher_info.empty:
                                st.success(f"👨‍🏫 {teacher_info.iloc[0]['name']}")
                    else:
                        st.info("배정된 선생님이 없습니다.")
                    
                    if substitute_teachers:
                        st.markdown("**🔄 대타 일정:**")
                        for sub in substitute_teachers:
                            teacher_info = teachers[teachers['username'] == sub['teacher_username']]
                            if not teacher_info.empty:
                                st.warning(f"📅 {sub['date']} - {teacher_info.iloc[0]['name']}")
    
    # ==========================================
    # 📅 일정 관리
    # ==========================================
    elif tab == "📅 일정 관리":
        st.header("📅 일정 보기")
        
        df_sched = get_schedule_df()
        df_sched['date'] = pd.to_datetime(df_sched['date']).dt.date
        
        if not df_sched.empty:
            min_date = df_sched['date'].min()
            max_date = df_sched['date'].max()
            total_classes = len(df_sched)
            
            st.success(f"""
            📚 **전체 일정:** {total_classes}회  
            📆 **기간:** {min_date} ~ {max_date}
            """)
        
        st.info("💡 **일정은 '수업 그룹' 탭에서 생성됩니다.**")
        
        if not df_sched.empty:
            df_sched_sorted = df_sched.sort_values('date', ascending=False)
            
            st.markdown("### 📋 전체 일정")
            
            for idx, row in df_sched_sorted.iterrows():
                is_today = row['date'] == get_today_kst()
                
                col1, col2, col3 = st.columns([4, 4, 1])
                
                # db query to get current record details
                current_teacher = ""
                current_zoom_id = ""
                current_class_name = row['session']
                current_date = row['date']
                current_start = row['start']
                current_end = row['end']
                
                try:
                    s_data = supabase_mgr.client.table('schedule').select('*').eq('id', row['id']).execute().data
                    if s_data:
                        current_record = s_data[0]
                        current_teacher = current_record.get('teacher_name') or ""
                        current_zoom_id = current_record.get('zoom_meeting_id') or ""
                        current_class_name = current_record.get('class_name') or row['session']
                        # Supabase에서 가져온 원본 시간 (ISO format)
                        raw_start = current_record.get('start_time')
                        raw_end = current_record.get('end_time')
                except: pass
    
                with col1:
                    # 📝 수업 정보 수정 (이름, 날짜, 시간)
                    new_class_name = st.text_input("수업명", value=current_class_name, key=f"name_{row['id']}", label_visibility="collapsed")
                    c1_a, c1_b = st.columns(2)
                    with c1_a:
                        new_date = st.date_input("날짜", value=current_date, key=f"date_{row['id']}", label_visibility="collapsed")
                    with c1_b:
                        st.caption(f"현재: {current_start}~{current_end}")
                    
                    new_start_t = st.text_input("시작 (HH:MM)", value=current_start, key=f"start_{row['id']}", label_visibility="collapsed")
                    new_end_t = st.text_input("종료 (HH:MM)", value=current_end, key=f"end_{row['id']}", label_visibility="collapsed")
    
                with col2:
                    if check_permission(user['role'], 'can_manage_schedule'):
                        try:
                            # 계정 정보 불러오기
                            # df_users = auth.load_users() # 상단 공통 로드로 대체
                            teacher_df = df_users[df_users['role'].isin(['teacher', 'admin'])]
                            teacher_names = teacher_df['name'].tolist()
                        except:
                            teacher_names = []
                            
                        options = ['미배정'] + teacher_names
                        start_idx = options.index(current_teacher) if current_teacher in options else 0
                        
                        new_teacher = st.selectbox("👨‍🏫 담당", options, index=start_idx, key=f"sel_t_{row['id']}", label_visibility="collapsed")
                        new_zoom = st.text_input("🌐 Zoom ID", value=current_zoom_id, key=f"zoom_t_{row['id']}", label_visibility="collapsed", placeholder="Zoom ID 입력")
                        
                        if st.button("저장", key=f"btn_t_{row['id']}", use_container_width=True, type="primary"):
                            try:
                                # 시간 조합 (KST)
                                st_dt_str = f"{new_date.isoformat()}T{new_start_t}:00+09:00"
                                en_dt_str = f"{new_date.isoformat()}T{new_end_t}:00+09:00"
                                
                                t_val = None if new_teacher == "미배정" else new_teacher
                                z_val = None if not new_zoom.strip() else new_zoom.strip()
                                
                                supabase_mgr.client.table('schedule').update({
                                    'class_name': new_class_name,
                                    'start_time': st_dt_str,
                                    'end_time': en_dt_str,
                                    'teacher_name': t_val,
                                    'zoom_meeting_id': z_val
                                }).eq('id', row['id']).execute()
                                st.success("✅ 일정이 업데이트되었습니다!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"저장 오류: {e}")
    
                with col3:
                    if check_permission(user['role'], 'can_manage_schedule'):
                        # ❌ 버튼을 '취소' 의미로 변경 및 경고 추가
                        if st.button("❌", key=f"del_sched_{row['id']}", help="이 일정만 취소(삭제)합니다", use_container_width=True):
                            try:
                                supabase_mgr.client.table('schedule').delete().eq('id', row['id']).execute()
                                st.success("일정이 취소되었습니다.")
                                sys_time.sleep(0.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"취소 오류: {e}")
        else:
            st.info("등록된 일정이 없습니다.")
    
    # ==========================================
    # 👨‍👩‍👧 보호자 관리
    # ==========================================
    elif tab == "👨‍👩‍👧 보호자 관리":
        st.header("👨‍👩‍👧‍👦 보호자 관리")
        
        df_parents = load_csv_safe(PARENTS_CSV, ['student', 'parent_name', 'phone'])
        
        if check_permission(user['role'], 'can_manage_students'):
            with st.expander("➕ 새 보호자 추가", expanded=False):
                p_student = st.selectbox("학생 선택", st.session_state.attendees, key="add_parent_student_select")
                p_name = st.text_input("👨‍👩‍👧 보호자명", key="add_parent_name_input")
                p_phone = st.text_input("📞 전화번호", key="add_parent_phone_input")
                
                if st.button("➕ 보호자 추가", use_container_width=True, key="btn_add_parent_manual"):
                    if p_student and p_name and p_phone:
                        new_parent = pd.DataFrame([{
                            'student': p_student,
                            'parent_name': p_name,
                            'phone': normalize_phone(p_phone)
                        }])
                        df_parents = pd.concat([df_parents, new_parent], ignore_index=True)
                        
                        create_user(
                            username=f"parent_{p_name}",
                            password="parent123",
                            role="parent",
                            name=p_name,
                            phone=normalize_phone(p_phone),
                            student_id=p_student
                        )
                        
                        if save_csv_safe(df_parents, PARENTS_CSV):
                            st.success("✅ 보호자가 추가되었습니다!")
                            st.info(f"학부모 계정도 생성되었습니다. ID: parent_{p_name}, PW: parent123")
                            st.rerun()
                    else:
                        st.error("모든 정보를 입력해주세요.")
        
        st.markdown("###")
        
        if not df_parents.empty:
            for idx, row in df_parents.iterrows():
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    st.markdown(f"""
                    <div style="background: white; padding: 15px; border-radius: 10px; 
                                margin: 5px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                        <div style="font-weight: bold; font-size: 16px;">
                            👤 {row['student']} → 👨‍👩‍👧 {row['parent_name']}
                        </div>
                        <div style="color: #666; margin-top: 5px;">
                            📞 {row['phone']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    if check_permission(user['role'], 'can_manage_students'):
                        if st.button("🗑️", key=f"del_parent_{idx}", help="삭제", use_container_width=True):
                            df_parents.drop(idx, inplace=True)
                            df_parents.reset_index(drop=True, inplace=True)
                            if save_csv_safe(df_parents, PARENTS_CSV):
                                st.success("보호자가 삭제되었습니다.")
                                st.rerun()
        else:
            st.info("등록된 보호자가 없습니다.")
    
    # ==========================================
    # 📞 문의 관리
    # ==========================================
    elif tab == "📞 문의 관리":
        st.header("📞 문의 관리")
        
        # 문의 로드 함수
        def load_inquiries():
            if not os.path.exists(INQUIRIES_CSV):
                return pd.DataFrame(columns=['timestamp', 'student_name', 'parent_name', 'inquiry_type', 'content', 'status', 'response', 'response_time'])
            
            try:
                df = pd.read_csv(INQUIRIES_CSV, encoding='utf-8-sig')
                df = df.fillna('')
                
                if 'inquiry_text' in df.columns and 'content' not in df.columns:
                    df = df.rename(columns={'inquiry_text': 'content'})
                
                if 'parent_name' not in df.columns:
                    df['parent_name'] = df.get('student_name', '')
                
                return df
            except Exception as e:
                logger.error(f"문의 데이터 로드 실패: {e}")
                return pd.DataFrame(columns=['timestamp', 'student_name', 'parent_name', 'inquiry_type', 'content', 'status', 'response', 'response_time'])
        
        # 문의 저장 함수
        def save_inquiries(df):
            try:
                df.to_csv(INQUIRIES_CSV, index=False, encoding='utf-8-sig')
                return True
            except Exception as e:
                logger.error(f"문의 데이터 저장 실패: {e}")
                return False
        
        # 답변 업데이트 함수
        def update_inquiry_response(timestamp, student_name, response_text, new_status='완료'):
            try:
                df = load_inquiries()
                
                mask = (df['timestamp'] == timestamp) & (df['student_name'] == student_name)
                
                if not df[mask].empty:
                    df.loc[mask, 'response'] = response_text
                    df.loc[mask, 'response_time'] = get_now_kst().strftime('%Y-%m-%d %H:%M:%S')
                    df.loc[mask, 'status'] = new_status
                    
                    return save_inquiries(df)
                
                return False
            except Exception as e:
                logger.error(f"답변 저장 실패: {e}")
                return False
        
        # 문의 삭제 함수
        def delete_inquiry(timestamp, student_name):
            try:
                df = load_inquiries()
                df = df[~((df['timestamp'] == timestamp) & (df['student_name'] == student_name))]
                return save_inquiries(df)
            except Exception as e:
                logger.error(f"문의 삭제 실패: {e}")
                return False
        
        # 문의 목록 로드
        df_inquiries = load_inquiries()
        
        if df_inquiries.empty:
            st.info("📭 아직 접수된 문의가 없습니다.")
            st.stop()
        
        # 필터 섹션
        st.markdown("### 🔍 조회 옵션")
        
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        
        with col_filter1:
            status_filter = st.selectbox(
                "📊 상태",
                ["전체", "접수", "처리중", "완료"],
                key="inquiry_status_filter"
            )
        
        with col_filter2:
            inquiry_types = ["전체"] + sorted(df_inquiries['inquiry_type'].unique().tolist())
            type_filter = st.selectbox(
                "📋 유형",
                inquiry_types,
                key="inquiry_type_filter"
            )
        
        with col_filter3:
            sort_order = st.selectbox(
                "⏱️ 정렬",
                ["최신순", "오래된순"],
                key="inquiry_sort"
            )
        
        # 필터 적용
        df_filtered = df_inquiries.copy()
        
        if status_filter != "전체":
            df_filtered = df_filtered[df_filtered['status'] == status_filter]
        
        if type_filter != "전체":
            df_filtered = df_filtered[df_filtered['inquiry_type'] == type_filter]
        
        # 정렬
        ascending = (sort_order == "오래된순")
        df_filtered = df_filtered.sort_values('timestamp', ascending=ascending)
        
        st.markdown("---")
        
        # 통계 요약
        st.markdown("### 📊 문의 통계")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total = len(df_filtered)
            st.metric("전체", f"{total}건")
        
        with col2:
            pending = len(df_filtered[df_filtered['status'] == '접수'])
            st.metric("📝 접수", f"{pending}건")
        
        with col3:
            processing = len(df_filtered[df_filtered['status'] == '처리중'])
            st.metric("⏳ 처리중", f"{processing}건")
        
        with col4:
            completed = len(df_filtered[df_filtered['status'] == '완료'])
            st.metric("✅ 완료", f"{completed}건")
        
        st.markdown("---")
        
        # 문의 목록
        st.markdown("### 📋 문의 내역")
        
        if df_filtered.empty:
            st.info("선택한 조건에 해당하는 문의가 없습니다.")
        else:
            for idx, inquiry in df_filtered.iterrows():
                status_color = {
                    '접수': '#FFA500',
                    '처리중': '#2196F3',
                    '완료': '#4CAF50'
                }.get(inquiry['status'], '#666')
                
                status_emoji = {
                    '접수': '📝',
                    '처리중': '⏳',
                    '완료': '✅'
                }.get(inquiry['status'], '📋')
                
                # 문의 카드
                with st.expander(
                    f"{status_emoji} [{inquiry['inquiry_type']}] {inquiry['student_name']} - {inquiry['timestamp'][:16]}",
                    expanded=False
                ):
                    # 상태 배지
                    st.markdown(f"""
                    <div style="display: inline-block; background: {status_color}; 
                                color: white; padding: 5px 15px; border-radius: 20px; 
                                font-size: 13px; margin-bottom: 15px;">
                        {inquiry['status']}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 문의 정보
                    col_info1, col_info2 = st.columns(2)
                    
                    with col_info1:
                        st.markdown(f"""
                        **📅 문의 시간:** {inquiry['timestamp']}  
                        **👤 학생:** {inquiry['student_name']}  
                        **👨‍👩‍👧 학부모:** {inquiry.get('parent_name', 'N/A')}
                        """)
                    
                    with col_info2:
                        st.markdown(f"""
                        **📋 유형:** {inquiry['inquiry_type']}  
                        **📊 상태:** {inquiry['status']}
                        """)
                    
                    st.markdown("---")
                    
                    # 문의 내용
                    st.markdown("**💬 문의 내용:**")
                    st.info(inquiry['content'])
                    
                    st.markdown("---")
                    
                    # 기존 답변 표시
                    has_response = (
                        inquiry.get('response') is not None and 
                        not pd.isna(inquiry.get('response')) and 
                        str(inquiry['response']).strip() != ''
                    )
                    
                    if has_response:
                        st.markdown("**📝 답변 내역:**")
                        
                        response_time = inquiry.get('response_time', '시간 미상')
                        if pd.isna(response_time) or response_time == '':
                            response_time = '시간 미상'
                        
                        st.markdown(f"""
                        <div style="background: #f0f7ff; padding: 15px; border-radius: 10px; 
                                    border-left: 4px solid #2196F3; margin-bottom: 15px;">
                            <div style="color: #1976D2; font-weight: bold; margin-bottom: 10px;">
                                💬 관리자 답변
                            </div>
                            <div style="color: #666; font-size: 13px; margin-bottom: 10px;">
                                📅 {response_time}
                            </div>
                            <div style="color: #333; line-height: 1.6; white-space: pre-wrap;">
                                {str(inquiry['response'])}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    # 답변 작성/수정 폼
                    st.markdown("**✍️ 답변 작성/수정:**")
                    
                    with st.form(f"response_form_{idx}"):
                        # 상태 변경
                        new_status = st.selectbox(
                            "상태 변경",
                            ["접수", "처리중", "완료"],
                            index=["접수", "처리중", "완료"].index(inquiry['status']),
                            key=f"status_{idx}"
                        )
                        
                        # 답변 내용
                        response_text = st.text_area(
                            "답변 내용",
                            value=str(inquiry['response']) if has_response else "",
                            height=150,
                            placeholder="학부모님께 전달할 답변을 작성해주세요...",
                            key=f"response_{idx}"
                        )
                        
                        col_submit, col_delete = st.columns([3, 1])
                        
                        with col_submit:
                            submitted = st.form_submit_button(
                                "💾 답변 저장",
                                use_container_width=True,
                                type="primary",
                                key=f"save_inquiry_resp_{idx}"
                            )
                        
                        with col_delete:
                            deleted = st.form_submit_button(
                                "🗑️ 삭제",
                                use_container_width=True,
                                type="secondary",
                                key=f"delete_inquiry_btn_{idx}"
                            )
                        
                        if submitted:
                            if response_text and len(response_text.strip()) >= 5:
                                if update_inquiry_response(
                                    inquiry['timestamp'],
                                    inquiry['student_name'],
                                    response_text.strip(),
                                    new_status
                                ):
                                    st.success("✅ 답변이 저장되었습니다!")
                                    st.balloons()
                                    st.rerun()
                                else:
                                    st.error("❌ 답변 저장 중 오류가 발생했습니다.")
                            else:
                                st.error("❌ 답변 내용을 5자 이상 입력해주세요.")
                        
                        if deleted:
                            if delete_inquiry(inquiry['timestamp'], inquiry['student_name']):
                                st.success("✅ 문의가 삭제되었습니다.")
                                st.rerun()
                            else:
                                st.error("❌ 문의 삭제 중 오류가 발생했습니다.")
    
    # ==========================================
    # 🔹 출석 체크 (개선 버전)
    # ==========================================
    elif tab == "🔹 출석 체크":
        st.header("🔹 QR 출석")
        
        df_schedule = get_schedule_df()
        df_schedule['date'] = pd.to_datetime(df_schedule['date']).dt.date
        today_sched = df_schedule[df_schedule['date'] == get_today_kst()]
        
        if today_sched.empty:
            st.warning("⚠️ 오늘 예정된 수업이 없습니다.")
            st.info("💡 '수업 그룹' 탭에서 수업을 먼저 등록해주세요.")
        else:
            now = get_now_kst()
            
            # 종료된 수업 필터링
            active_classes = []
            for idx, sched in today_sched.iterrows():
                class_end = datetime.strptime(sched['end'], '%H:%M').time()
                class_end_dt = datetime.combine(get_today_kst(), class_end)
                
                if now <= class_end_dt:
                    active_classes.append((idx, sched))
            
            if not active_classes:
                st.error("❌ 오늘의 모든 수업이 종료되었습니다.")
                st.info("📊 종료된 수업의 기록은 '리포트' 탭에서 확인하실 수 있습니다.")
                st.stop()
            
            # 여러 수업이 있는 경우 선택
            if len(active_classes) > 1:
                st.info(f"📚 **오늘 진행중/예정인 수업: {len(active_classes)}개**")
                
                class_options = []
                for i, (idx, sched) in enumerate(active_classes):
                    class_start = datetime.strptime(sched['start'], '%H:%M').time()
                    class_end = datetime.strptime(sched['end'], '%H:%M').time()
                    
                    if class_start <= now.time() <= class_end:
                        status = "🔴 진행중"
                    elif now.time() < class_start:
                        status = "⏰ 예정"
                    else:
                        status = ""
                    
                    option = f"{sched['session']} ({sched['start']} ~ {sched['end']}) {status}"
                    class_options.append(option)
                
                selected_class = st.selectbox(
                    "📋 출석 체크할 수업을 선택하세요",
                    class_options,
                    key="class_selector"
                )
                
                selected_idx = class_options.index(selected_class)
                _, row = active_classes[selected_idx]
            else:
                _, row = active_classes[0]
            
            st.success(f"📅 선택된 수업: {row['start']} ~ {row['end']} ({row['session']})")
            st.info(f"🕐 현재 시간: {now.strftime('%H:%M:%S')}")
            
            # 출석 가능 시간 체크
            class_start_str = row['start']
            class_end_str = row['end']
            
            try:
                class_start_time = datetime.strptime(class_start_str, '%H:%M').time()
                class_end_time = datetime.strptime(class_end_str, '%H:%M').time()
                
                class_start_dt = datetime.combine(get_today_kst(), class_start_time)
                class_end_dt = datetime.combine(get_today_kst(), class_end_time)
                attendance_start_dt = class_start_dt - timedelta(minutes=30)
            except Exception as e:
                st.error(f"시간 변환 오류: {e}")
                st.stop()
            
            if now < attendance_start_dt:
                time_until = attendance_start_dt - now
                minutes_until = int(time_until.total_seconds() / 60)
                seconds_until = int(time_until.total_seconds() % 60)
                
                st.error(f"⏰ 출석은 수업 시작 30분 전({attendance_start_dt.strftime('%H:%M')})부터 가능합니다.")
                st.info(f"⏳ **{minutes_until}분 {seconds_until}초 후** 출석 가능합니다.")
                st.stop()
            
            elif now > class_end_dt:
                st.error("❌ 수업이 종료되어 출석 체크가 불가능합니다.")
                st.info(f"**수업 시간:** {class_start_str} ~ {class_end_str}")
                st.warning("💡 수업 시간 내에만 출석 체크가 가능합니다.")
                st.stop()
            
            else:
                st.success(f"✅ 출석 체크 가능 시간입니다!")
                st.info(f"📅 출석 가능: {attendance_start_dt.strftime('%H:%M')} ~ {class_end_str}")
            
            st.markdown("---")
            
            # 하이브리드 카메라 시스템
            flask_available = check_flask_connection()
            
            col_mode1, col_mode2 = st.columns(2)
            
            with col_mode1:
                if flask_available:
                    st.success("✅ Flask 서버 연결됨 (데스크톱 모드)")
                else:
                    st.info("📱 모바일 모드 (카메라)")
            
            with col_mode2:
                if flask_available:
                    use_mobile = st.checkbox("📱 모바일 카메라로 전환", value=False, key="attendance_mobile_switch")
                else:
                    use_mobile = True
                    st.caption("💡 Flask 서버가 없어 자동으로 모바일 모드")
            
            st.markdown("---")
            
            # 🖥️ Flask Stream (데스크톱)
            if flask_available and not use_mobile:
                st.subheader("🖥️ 데스크톱 출석 체크 (연속 스캔)")
                st.info("💡 **빠른 연속 스캔**: QR 코드를 카메라에 비추면 자동으로 인식됩니다.")
                
                stream_url = f"http://127.0.0.1:{FLASK_PORT}/video_feed"
                
                html_code = f"""
                <div style="text-align:center; padding:10px;">
                    <img src="{stream_url}"
                         style="width:100%; max-width:1200px; height:auto; 
                                border:3px solid #4CAF50; border-radius:15px;
                                box-shadow: 0 4px 12px rgba(0,0,0,0.15);"
                         alt="QR 출석 스트림"/>
                </div>
                """
                
                components.html(html_code, height=900, scrolling=False)
                
                st.markdown("###")
                
                col1, col2, col3 = st.columns(3)
                
                try:
                    response = requests.get(f"http://localhost:{FLASK_PORT}/status", timeout=2)
                    if response.status_code == 200:
                        status_data = response.json()
                        
                        with col1:
                            st.metric("📊 총 스캔", status_data.get('total_scanned', 0))
                        
                        with col2:
                            st.metric("📝 기록수", status_data.get('total_records', 0))
                        
                        with col3:
                            available = "가능" if status_data.get('attendance_available', False) else "불가"
                            st.metric("🎯 출석 상태", available)
                except Exception as e:
                    st.warning(f"통계 정보를 불러올 수 없습니다: {e}")
                
                if st.button("🔄 출석현황 새로고침", use_container_width=True, key="attendance_refresh_log_btn"):
                    st.rerun()
            
            # 📱 Streamlit Camera (모바일)
            else:
                st.subheader("📱 모바일 출석 체크 (단일 스캔)")
                st.info("💡 **한 명씩 촬영**: 사진을 찍으면 QR 코드를 인식합니다.")
                
                picture = st.camera_input("📸 QR 코드를 카메라에 비춰주세요", key="attendance_mobile_camera_input")
                
                if picture:
                    try:
                        from PIL import Image
                        import cv2
                        import numpy as np
                        from pyzbar.pyzbar import decode
                        
                        image = Image.open(picture)
                        opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                        decoded_objects = decode(opencv_image)
                        
                        if decoded_objects:
                            for obj in decoded_objects:
                                qr_data = obj.data.decode('utf-8')
                                
                                df_students = load_csv_safe(STUDENTS_CSV, ['name', 'qr_code', 'phone'])
                                
                                student_row = df_students[
                                    (df_students['qr_code'] == qr_data) | 
                                    (df_students['name'] == qr_data)
                                ]
                                
                                if not student_row.empty:
                                    student_name = student_row.iloc[0]['name']
                                    
                                    # 중복 체크
                                    already_attended, source = is_already_attended(student_name, row['session'], get_today_kst())
                                    
                                    if already_attended:
                                        st.warning(f"⚠️ {student_name} 학생은 이미 이 수업에 출석 체크되었습니다.")
                                        continue
                                    
                                    attendance_time = get_now_kst()
                                    
                                    # 상태 판정
                                    if attendance_time <= class_start_dt:
                                        status = ATTENDANCE_STATUS_PRESENT
                                        
                                        status_icon = "✅"
                                        status_color = "#4CAF50"
                                        status_note = "정시 출석"
                                    elif attendance_time <= (class_start_dt + timedelta(minutes=10)):
                                        status = ATTENDANCE_STATUS_PRESENT
                                        
                                        status_icon = "✅"
                                        status_color = "#4CAF50"
                                        minutes_late = int((attendance_time - class_start_dt).total_seconds() / 60)
                                        status_note = f"{minutes_late}분 지각"
                                    elif attendance_time <= class_end_dt:
                                        status = ATTENDANCE_STATUS_LATE
                                    
                                        status_icon = "⏰"
                                        status_color = "#FF9800"
                                        status_note = "수업 중 도착"
                                    else:
                                        status = ATTENDANCE_STATUS_ABSENT
                                        status_icon = "❌"
                                        status_color = "#f44336"
                                        status_note = "수업 종료 후"
                                    
                                    attendance_record = {
                                        'date': get_today_kst().isoformat(),
                                        'session': row['session'],
                                        'student_name': student_name,
                                        'qr_code': qr_data,
                                        'timestamp': attendance_time.strftime('%Y-%m-%d %H:%M:%S'),
                                        'status': status
                                    }
                                    
                                    try:
                                        # Get student_id
                                        student_rec = supabase_mgr.client.table('students').select('id').eq('student_name', student_name).execute()
                                        student_id = student_rec.data[0]['id'] if student_rec.data else None
                                        
                                        # Get schedule_id
                                        class_start_dt_str = datetime.combine(get_today_kst(), class_start_time).isoformat()
                                        sched_rec = supabase_mgr.client.table('schedule').select('id').eq('class_name', row['session']).eq('start_time', class_start_dt_str).execute()
                                        schedule_id = sched_rec.data[0]['id'] if sched_rec.data else None
                                        
                                        if student_id and schedule_id:
                                            supabase_mgr.client.table('attendance').insert({
                                                'student_id': student_id,
                                                'schedule_id': schedule_id,
                                                'check_in_time': attendance_time.isoformat(),
                                                'status': status,
                                                'type': '오프라인'
                                            }).execute()
                                    except Exception as e:
                                        logger.error(f"Mobile attendance SB error: {e}")
                                    
                                    # 세션에 기록
                                    session_key = f"scanned_{row['session']}_{row['start']}_{get_today_kst()}"
                                    if session_key not in st.session_state:
                                        st.session_state[session_key] = set()
                                    st.session_state[session_key].add(student_name)
                                    
                                    st.markdown(f"""
                                    <div style="background: {status_color}; color: white; padding: 25px; 
                                                border-radius: 15px; text-align: center; margin: 20px 0;
                                                box-shadow: 0 4px 12px rgba(0,0,0,0.2);">
                                        <h1 style="margin: 0; font-size: 48px;">{status_icon}</h1>
                                        <h2 style="margin: 10px 0;">{status}</h2>
                                        <h3 style="margin: 10px 0;">{student_name}</h3>
                                        <p style="margin: 5px 0; font-size: 14px; opacity: 0.9;">{row['session']}</p>
                                        <p style="margin: 5px 0; font-size: 16px; font-weight: bold;">{status_note}</p>
                                        <p style="margin: 5px 0; font-size: 18px;">{attendance_time.strftime('%H:%M:%S')}</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    if status == "출석":
                                        st.balloons()
                                    else:
                                        st.snow()
                                    
                                    import time as _time
                                    __time.sleep(2)
                                    st.rerun()
                                else:
                                    st.error(f"❌ 등록되지 않은 QR 코드입니다: {qr_data}")
                        else:
                            st.warning("⚠️ QR 코드를 인식할 수 없습니다. 다시 시도해주세요.")
                    
                    except Exception as e:
                        st.error(f"❌ QR 코드 처리 중 오류 발생: {e}")
                        logger.error(f"QR processing error: {e}")
            
            st.markdown("---")
            
            # 출석현황 (생략 - 원본 코드 참조)
    # ==========================================
    # 📈 리포트 (출석 조회 + 수정 기능)
    # ==========================================
    elif tab == "📈 리포트":
        st.header("📊 출석 리포트")
        
        report_tab1, report_tab2, report_tab3 = st.tabs(["📋 출석 조회", "✏️ 출석 수정", "🎓 강좌 이수 현황"], key="admin_auto_2930")
        
        # ========================================
        # 📋 출석 조회 탭
        # ========================================
        with report_tab1:
            try:
                df_attendance = get_attendance_df()
                
                if df_attendance.empty:
                    st.info("🔭 아직 출석 기록이 없습니다.")
                    st.stop()
                
                column_mapping = {
                    'name': 'student_name',
                    'student': 'student_name',
                    'code': 'qr_code',
                    'time': 'timestamp'
                }
                df_attendance = df_attendance.rename(columns=column_mapping)
                
                if 'date' in df_attendance.columns:
                    df_attendance['date'] = pd.to_datetime(df_attendance['date']).dt.date
                elif 'timestamp' in df_attendance.columns:
                    df_attendance['date'] = pd.to_datetime(df_attendance['timestamp']).dt.date
                
                if 'status' not in df_attendance.columns:
                    df_attendance['status'] = '출석'
                
            except FileNotFoundError:
                st.info("🔭 아직 출석 기록이 없습니다.")
                st.stop()
            except Exception as e:
                st.error(f"출석 기록 로드 오류: {e}")
                st.stop()
            
            st.markdown("### 🔍 조회 옵션")
            
            col_filter1, col_filter2, col_filter3 = st.columns(3)
            
            with col_filter1:
                available_dates = sorted(df_attendance['date'].unique(), reverse=True)
                date_options = ["전체 기간"] + [str(d) for d in available_dates]
                selected_date = st.selectbox("📅 날짜 선택", date_options, key="report_date")
            
            with col_filter2:
                if 'session' in df_attendance.columns:
                    available_sessions = ["전체 수업"] + sorted(df_attendance['session'].unique().tolist())
                    selected_session = st.selectbox("📚 수업 선택", available_sessions, key="report_session")
                else:
                    selected_session = "전체 수업"
            
            with col_filter3:
                status_filter = st.selectbox("📊 상태", ["전체", ATTENDANCE_STATUS_PRESENT, ATTENDANCE_STATUS_LATE, ATTENDANCE_STATUS_ABSENT], key="report_status")
            
            df_filtered = df_attendance.copy()
            
            if selected_date != "전체 기간":
                df_filtered = df_filtered[df_filtered['date'] == pd.to_datetime(selected_date).date()]
            
            if selected_session != "전체 수업" and 'session' in df_filtered.columns:
                df_filtered = df_filtered[df_filtered['session'] == selected_session]
            
            if status_filter != "전체":
                df_filtered = df_filtered[df_filtered['status'] == status_filter]
            
            st.markdown("---")
            
            if not df_filtered.empty:
                st.markdown("### 📊 출결 통계")
                
                col1, col2, col3, col4 = st.columns(4)
                status_counts = df_filtered['status'].value_counts()
                
                with col1:
                    st.metric("✅ 출석", status_counts.get(ATTENDANCE_STATUS_PRESENT, 0))
                with col2:
                    st.metric("⏰ 지각", status_counts.get(ATTENDANCE_STATUS_LATE, 0))
                with col3:
                    st.metric("❌ 결석", status_counts.get(ATTENDANCE_STATUS_ABSENT, 0))
                with col4:
                    total = len(df_filtered)
                    present = status_counts.get(ATTENDANCE_STATUS_PRESENT, 0) + status_counts.get(ATTENDANCE_STATUS_LATE, 0)
                    rate = (present / total * 100) if total > 0 else 0
                    st.metric("📈 출석률", f"{rate:.1f}%")
                
                st.markdown("###")
                st.markdown("### 📋 상세 출석 기록")
                
                display_columns = ['student_name', 'timestamp', 'status', 'type']
                if 'session' in df_filtered.columns and selected_session == "전체 수업":
                    display_columns.insert(1, 'session')
                
                df_display = df_filtered[display_columns].copy()
                
                # '온라인' 타입인 경우 상태에 (줌) 추가 (학생 앱과 동일 로직)
                if 'type' in df_display.columns:
                    df_display['status'] = df_display.apply(
                        lambda r: f"{r['status']}(줌)" if str(r.get('type')) == '온라인' else r['status'], 
                        axis=1
                    )
                
                df_display = df_display.sort_values('timestamp', ascending=False)
                
                # 표시용 컬럼명 변경 (type은 숨김)
                final_cols = [c for c in df_display.columns if c != 'type']
                df_display = df_display[final_cols]
                
                df_display.columns = ['학생명' if col == 'student_name' else '수업' if col == 'session' else '시간' if col == 'timestamp' else '상태' if col == 'status' else col for col in df_display.columns]
                
                if '시간' in df_display.columns:
                    df_display['시간'] = pd.to_datetime(df_display['시간'], format='ISO8601', errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
                
                # Using st.data_editor for interactive row deletion
                st.markdown("💡 삭제하려면 마우스 커서를 올린 후 표시되는 '❌' 쓰레기통 버튼을 누르거나, 수정 탭을 활용할 수 있습니다. 아래에서 <b>직접 삭제</b> 버튼을 눌러도 됩니다.", unsafe_allow_html=True)
                
                # We display the dataframe but since data_editor doesn't directly delete from DB, we will just show the table
                st.dataframe(df_display, use_container_width=True, hide_index=True)
                st.markdown("###")
                
                with st.expander("🗑️ 출석 기록 직접 삭제"):
                    if not df_filtered.empty:
                        st.write("삭제할 기록을 선택하세요 (선택 즉시 데이터베이스에서 영구 삭제됩니다).")
                        if 'id' not in df_filtered.columns:
                            st.error("❌ 'id' 컴럼이 데이터에 없습니다. 페이지를 새로고침해 주세요.")
                        else:
                            for _, row in df_filtered.iterrows():
                                ts = row.get('timestamp', '')
                                ts_str = ts[11:19] if isinstance(ts, str) and len(ts) > 11 else str(ts)
                                status_label = f"{row.get('status', '')}(줌)" if str(row.get('type')) == '온라인' else row.get('status', '')
                                disp_str = f"{row.get('student_name', '알수없음')} | {row.get('session', '')} | {row.get('date', '')} {ts_str} | {status_label}"
                                
                                col1, col2 = st.columns([8, 2])
                                with col1:
                                    st.write(disp_str)
                                with col2:
                                    if st.button("🗑️ 삭제", key=f"admin_del_{row['id']}", type="secondary"):
                                        with st.spinner("삭제 중..."):
                                            try:
                                                res = supabase_mgr.client.table('attendance').delete().eq('id', row['id']).execute()
                                                
                                                if res.data or not res.error:
                                                    st.toast(f"✅ {row.get('student_name', '학생')} 기록 삭제 완료")
                                                    st.success("✅ 삭제되었습니다.")
                                                    import time as _time
                                                    _time.sleep(1)
                                                    st.rerun()
                                                else:
                                                    st.error(f"❌ 삭제 실패: {res.error}")
                                            except Exception as e:
                                                st.error(f"❌ 시스템 오류: {e}")
                                                logger.error(f"Deletion error: {e}")
                st.markdown("###")
                
                filename_parts = []
                if selected_date != "전체 기간":
                    filename_parts.append(selected_date.replace("-", ""))
                if selected_session != "전체 수업":
                    filename_parts.append(selected_session.replace(" ", "_"))
                
                filename = f"출석기록_{'_'.join(filename_parts) if filename_parts else '전체'}.csv"
                
                st.download_button("📥 CSV 다운로드", df_display.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'), file_name=filename, mime="text/csv", use_container_width=True, key="attendance_log_csv_download")
            else:
                st.warning("⚠️ 선택한 조건에 해당하는 출석 기록이 없습니다.")
        
        # ========================================
        # ✏️ 출석 수정 탭
        # ========================================
        with report_tab2:
            st.markdown("### ✏️ 과거 출석 기록 수정")
            
            if not check_permission(user['role'], 'can_manage_students'):
                st.warning("⚠️ 출석 수정 권한이 없습니다.")
                st.stop()
            
            try:
                df_schedule = get_schedule_df()
                
                if df_schedule.empty:
                    st.warning("⚠️ 등록된 수업 일정이 없습니다.")
                    st.info("💡 '일정 관리' 탭에서 수업을 먼저 등록해주세요.")
                    st.stop()
                
                df_schedule['date'] = pd.to_datetime(df_schedule['date'], format='ISO8601', errors='coerce').dt.date
                
            except FileNotFoundError:
                st.warning("⚠️ schedule.csv 파일이 없습니다.")
                st.stop()
            except Exception as e:
                st.error(f"일정 로드 실패: {e}")
                st.stop()
            
            try:
                if os.path.exists(ATTENDANCE_LOG_CSV):
                    df_attendance_edit = get_attendance_df()
                    
                    column_mapping = {
                        'name': 'student_name',
                        'student': 'student_name',
                        'code': 'qr_code',
                        'time': 'timestamp'
                    }
                    df_attendance_edit = df_attendance_edit.rename(columns=column_mapping)
                    
                    if 'date' in df_attendance_edit.columns:
                        df_attendance_edit['date'] = pd.to_datetime(df_attendance_edit['date']).dt.date
                    elif 'timestamp' in df_attendance_edit.columns:
                        df_attendance_edit['date'] = pd.to_datetime(df_attendance_edit['timestamp']).dt.date
                else:
                    df_attendance_edit = pd.DataFrame(columns=['date', 'session', 'student_name', 'qr_code', 'timestamp', 'status'])
            except Exception as e:
                st.warning(f"출석 기록 로드 중 오류 (무시됨): {e}")
                df_attendance_edit = pd.DataFrame(columns=['date', 'session', 'student_name', 'qr_code', 'timestamp', 'status'])
            
            st.markdown("#### 📅 1단계: 수정할 수업 선택")
            st.info("💡 출석 기록이 없는 수업도 선택하여 결석 처리할 수 있습니다.")
            
            col_edit1, col_edit2 = st.columns(2)
            
            with col_edit1:
                schedule_dates = sorted(df_schedule['date'].unique(), reverse=True)
                edit_date = st.selectbox("날짜 선택", schedule_dates, format_func=lambda x: str(x), key="edit_date_schedule")
            
            with col_edit2:
                date_schedule = df_schedule[df_schedule['date'] == edit_date]
                schedule_sessions = sorted(date_schedule['session'].unique().tolist())
                edit_session = st.selectbox("수업 선택", schedule_sessions, key="edit_session_schedule")
            
            st.markdown("---")
            
            selected_class = date_schedule[date_schedule['session'] == edit_session].iloc[0]
            
            st.markdown(f"""
            **선택한 수업:**
            - 📅 날짜: {edit_date}
            - 📚 수업: {edit_session}
            - ⏰ 시간: {selected_class['start']} ~ {selected_class['end']}
            """)
            
            st.markdown("---")
            st.markdown("#### 📋 2단계: 현재 출석 기록")
            
            if not df_attendance_edit.empty:
                session_records = df_attendance_edit[(df_attendance_edit['date'] == edit_date) & (df_attendance_edit['session'] == edit_session)].copy()
            else:
                session_records = pd.DataFrame(columns=['date', 'session', 'student_name', 'qr_code', 'timestamp', 'status'])
            
            if not session_records.empty:
                st.success(f"✅ 출석 기록 있음: {len(session_records)}명")
                
                for row_num, record in session_records.iterrows():
                    with st.expander(f"👤 {record['student_name']} - 현재: {record['status']}", expanded=False):
                        col_info, col_edit = st.columns([2, 3])
                        
                        with col_info:
                            st.markdown(f"**학생:** {record['student_name']}  \n**시간:** {record['timestamp']}  \n**현재 상태:** {record['status']}")
                        
                        with col_edit:
                            form_key = f"edit_{edit_date}_{edit_session}_{record['student_name']}_{row_num}"
                            
                            with st.form(form_key):
                                new_status = st.selectbox("변경할 상태", [ATTENDANCE_STATUS_PRESENT, ATTENDANCE_STATUS_LATE, ATTENDANCE_STATUS_ABSENT], index=[ATTENDANCE_STATUS_PRESENT, ATTENDANCE_STATUS_LATE, ATTENDANCE_STATUS_ABSENT].index(record['status']) if record['status'] in [ATTENDANCE_STATUS_PRESENT, ATTENDANCE_STATUS_LATE, ATTENDANCE_STATUS_ABSENT] else 0, key=f"status_{form_key}")
                                
                                col_save, col_delete = st.columns(2)
                                
                                with col_save:
                                    if st.form_submit_button("💾 상태 변경", use_container_width=True, key=f"btn_update_status_{form_key}"):
                                        try:
                                            df_full = get_attendance_df()
                                            column_mapping = {'name': 'student_name', 'student': 'student_name', 'code': 'qr_code', 'time': 'timestamp'}
                                            df_full = df_full.rename(columns=column_mapping)
                                            
                                            if 'date' in df_full.columns:
                                                df_full['date_original'] = df_full['date']
                                                df_full['date'] = pd.to_datetime(df_full['date']).dt.date
                                            
                                            mask = (df_full['date'] == edit_date) & (df_full['session'] == edit_session) & (df_full['student_name'] == record['student_name'])
                                            
                                            try:
                                                # Update directly in Supabase using the record's specific ID if available
                                                # Wait, get_attendance_df provides 'id' from attendance table? We added it!
                                                # record['id'] should exist if we passed it in 'record'
                                                rec_id = record.get('id')
                                                if rec_id:
                                                    supabase_mgr.client.table('attendance').update({'status': new_status}).eq('id', rec_id).execute()
                                                    st.success(f"✅ 상태가 '{new_status}'로 변경되었습니다!")
                                                    import time as _time
                                                    _time.sleep(1)
                                                    st.rerun()
                                                else:
                                                    st.error("레코드를 찾을 수 없습니다 (ID 없음).")
                                            except Exception as e:
                                                st.error(f"❌ 수정 실패: {e}")
                                        except Exception as e:
                                            st.error(f"저장 실패: {e}")
                                            logger.error(f"Failed to update attendance: {e}")
                                
                                with col_delete:
                                    if st.form_submit_button("🗑️ 기록 삭제", use_container_width=True, key=f"btn_delete_record_{form_key}"):
                                        try:
                                            df_full = get_attendance_df()
                                            column_mapping = {'name': 'student_name', 'student': 'student_name', 'code': 'qr_code', 'time': 'timestamp'}
                                            df_full = df_full.rename(columns=column_mapping)
                                            
                                            if 'date' in df_full.columns:
                                                df_full['date_original'] = df_full['date']
                                                df_full['date'] = pd.to_datetime(df_full['date']).dt.date
                                            
                                            rec_id = record.get('id')
                                            if rec_id:
                                                supabase_mgr.client.table('attendance').delete().eq('id', rec_id).execute()
                                            else:
                                                raise Exception("레코드 ID가 없습니다.")
                                            st.success(f"✅ {record['student_name']}의 출석 기록이 삭제되었습니다!")
                                            logger.info(f"Attendance deleted: {record['student_name']}")
                                            import time as _time
                                            _time.sleep(1)
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"삭제 실패: {e}")
                                            logger.error(f"Failed to delete attendance: {e}")
            else:
                st.warning("⚠️ 이 수업의 출석 기록이 아직 없습니다.")
                st.info("💡 아래에서 학생들을 추가하여 출석/결석 처리할 수 있습니다.")
            
            st.markdown("---")
            st.markdown("#### ➕ 3단계: 학생 출석/결석 처리")
            
            df_groups = load_class_groups()
            df_student_groups = load_student_groups()
            
            group_name = edit_session.split()[0] if ' ' in edit_session else edit_session
            matching_groups = df_groups[df_groups['group_name'].str.contains(group_name, na=False)]
            
            if not matching_groups.empty:
                group_ids = matching_groups['group_id'].tolist()
                students_in_groups = df_student_groups[df_student_groups['group_id'].isin(group_ids)]
                all_students = set(students_in_groups['student_name'].tolist())
            else:
                all_students = set(st.session_state.attendees)
            
            if not session_records.empty:
                recorded_students = set(session_records['student_name'].tolist())
            else:
                recorded_students = set()
            
            missing_students = sorted(list(all_students - recorded_students))
            
            add_tab1, add_tab2 = st.tabs(["➕ 개별 추가", "⚡ 일괄 결석 처리"], key="admin_auto_3266")
            
            with add_tab1:
                if missing_students:
                    st.info(f"📋 출석 기록이 없는 학생: {len(missing_students)}명")
                    
                    with st.form("add_individual_form"):
                        add_student = st.selectbox("추가할 학생 선택", missing_students, key="add_individual_student")
                        add_status = st.selectbox("출석 상태", [ATTENDANCE_STATUS_PRESENT, ATTENDANCE_STATUS_LATE, ATTENDANCE_STATUS_ABSENT], key="add_individual_status")
                        add_time = st.time_input("시간", value=datetime.strptime(selected_class['start'], '%H:%M').time(), key="add_individual_time")
                        
                        if st.form_submit_button("➕ 출석 기록 추가", use_container_width=True, key="btn_add_manual_attendance_item"):
                            try:
                                if os.path.exists(ATTENDANCE_LOG_CSV):
                                    df_full = get_attendance_df()
                                else:
                                    df_full = pd.DataFrame(columns=['date', 'session', 'student_name', 'qr_code', 'timestamp', 'status'])
                                
                                column_mapping = {'name': 'student_name', 'student': 'student_name', 'code': 'qr_code', 'time': 'timestamp'}
                                df_full = df_full.rename(columns=column_mapping)
                                
                                new_record = pd.DataFrame([{'date': edit_date.isoformat(), 'session': edit_session, 'student_name': add_student, 'qr_code': add_student, 'timestamp': datetime.combine(edit_date, add_time).strftime('%Y-%m-%d %H:%M:%S'), 'status': add_status}])
                                
                                df_full = pd.concat([df_full, new_record], ignore_index=True)
                                df_full.to_csv(ATTENDANCE_LOG_CSV, index=False, encoding='utf-8-sig')
                                
                                # ⭐ Supabase에도 즉시 동기화 추가
                                try:
                                    from supabase_client import supabase_mgr
                                    # student_id 찾기
                                    std_rec = supabase_mgr.client.table('students').select('id').eq('student_name', add_student).execute()
                                    student_id = std_rec.data[0]['id'] if std_rec.data else None
                                    
                                    # schedule_id 찾기 (해당 날짜/시간의 일정)
                                    start_dt_target = datetime.combine(edit_date, add_time).isoformat() + "+09:00"
                                    sched_rec = supabase_mgr.client.table('schedule').select('id')\
                                        .ilike('class_name', f"{edit_session}%")\
                                        .gte('start_time', f"{edit_date.isoformat()}T00:00:00")\
                                        .lte('start_time', f"{edit_date.isoformat()}T23:59:59").execute()
                                    schedule_id = sched_rec.data[0]['id'] if sched_rec.data else None
                                    
                                    if student_id:
                                        # schedule_id가 없어도(기존 대시보드 리포트와 동일하게) 일단 입력
                                        supabase_mgr.client.table('attendance').insert({
                                            'student_id': student_id,
                                            'schedule_id': schedule_id,
                                            'check_in_time': datetime.combine(edit_date, add_time).isoformat(),
                                            'status': add_status,
                                            'type': '수동수정'
                                        }).execute()
                                except Exception as sb_err:
                                    logger.warning(f"Manual add SB sync failed: {sb_err}")
    
                                st.success(f"✅ {add_student}의 출석 기록이 추가되었습니다! (상태: {add_status})")
                                logger.info(f"Attendance added: {add_student} - {add_status}")
                                st.balloons()
                                import time as _time
                                sys_time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"추가 실패: {e}")
                                logger.error(f"Failed to add attendance: {e}")
                else:
                    st.success("✅ 모든 학생의 출석 기록이 완료되었습니다!")
            
            with add_tab2:
                if missing_students:
                    st.warning(f"⚠️ 출석 기록이 없는 학생: {len(missing_students)}명")
                    st.info("💡 아래 버튼을 누르면 모든 미기록 학생을 **결석**으로 일괄 처리합니다.")
                    
                    with st.expander("📋 결석 처리될 학생 목록 보기"):
                        for student in missing_students:
                            st.text(f"• {student}")
                    
                    col_warn, col_action = st.columns([2, 1])
                    
                    with col_warn:
                        st.markdown("""
                        **⚠️ 주의사항:**
                        - 이 작업은 되돌릴 수 없습니다
                        - 모든 학생이 "결석"으로 처리됩니다
                        - 시간은 수업 종료 시간으로 기록됩니다
                        """)
                    
                    with col_action:
                        if st.button("⚡ 일괄 결석 처리", type="primary", use_container_width=True, key="btn_batch_absence_process"):
                            try:
                                if os.path.exists(ATTENDANCE_LOG_CSV):
                                    df_full = get_attendance_df()
                                else:
                                    df_full = pd.DataFrame(columns=['date', 'session', 'student_name', 'qr_code', 'timestamp', 'status'])
                                
                                column_mapping = {'name': 'student_name', 'student': 'student_name', 'code': 'qr_code', 'time': 'timestamp'}
                                df_full = df_full.rename(columns=column_mapping)
                                
                                absence_time = datetime.combine(edit_date, datetime.strptime(selected_class['end'], '%H:%M').time())
                                
                                new_records = []
                                for student in missing_students:
                                    new_records.append({'date': edit_date.isoformat(), 'session': edit_session, 'student_name': student, 'qr_code': student, 'timestamp': absence_time.strftime('%Y-%m-%d %H:%M:%S'), 'status': ATTENDANCE_STATUS_ABSENT})
                                
                                df_new = pd.DataFrame(new_records)
                                df_full = pd.concat([df_full, df_new], ignore_index=True)
                                df_full.to_csv(ATTENDANCE_LOG_CSV, index=False, encoding='utf-8-sig')
                                
                                # ⭐ Supabase에도 즉시 일괄 동기화 추가
                                try:
                                    from supabase_client import supabase_mgr
                                    # 일괄 등록용 데이터 리스트
                                    sb_records = []
                                    
                                    # schedule_id 하나만 찾으면 됨 (모두 동일 수업/날짜)
                                    sched_rec = supabase_mgr.client.table('schedule').select('id')\
                                        .ilike('class_name', f"{edit_session}%")\
                                        .gte('start_time', f"{edit_date.isoformat()}T00:00:00")\
                                        .lte('start_time', f"{edit_date.isoformat()}T23:59:59").execute()
                                    schedule_id = sched_rec.data[0]['id'] if sched_rec.data else None
                                    
                                    for student in missing_students:
                                        # student_id 찾기
                                        std_rec = supabase_mgr.client.table('students').select('id').eq('student_name', student).execute()
                                        student_id = std_rec.data[0]['id'] if std_rec.data else None
                                        
                                        if student_id:
                                            sb_records.append({
                                                'student_id': student_id,
                                                'schedule_id': schedule_id,
                                                'check_in_time': absence_time.isoformat(),
                                                'status': ATTENDANCE_STATUS_ABSENT,
                                                'type': '수동수정'
                                            })
                                    
                                    if sb_records:
                                        supabase_mgr.client.table('attendance').insert(sb_records).execute()
                                        logger.info(f"Bulk absence SB sync success: {len(sb_records)} students")
                                except Exception as sb_err:
                                    logger.warning(f"Bulk absence SB sync failed: {sb_err}")
                                
                                st.success(f"✅ {len(missing_students)}명의 학생이 결석 처리되었습니다!")
                                logger.info(f"Bulk absence processed: {len(missing_students)} students")
                                st.balloons()
                                sys_time.sleep(2)
                                st.rerun()
                            except Exception as e:
                                st.error(f"일괄 처리 실패: {e}")
                                logger.error(f"Failed to process bulk absence: {e}")
                else:
                    st.success("✅ 모든 학생의 출석 기록이 완료되었습니다!")
    
        # ========================================
        # 🎓 강좌 이수 현황 탭
        # ========================================
        with report_tab3:
            st.markdown("### 🎓 4주 강좌 이수 리포트 (4/4 ~ 4/25)")
            st.info("💡 4월 4일, 11일, 18일, 25일 총 4회의 수업 이수 현황을 집계합니다. (지각/온라인 모두 100% 인정)")
            
            target_dates_str = ['2026-04-04', '2026-04-11', '2026-04-18', '2026-04-25']
            
            try:
                df_att = get_attendance_df()
                df_std = load_csv_safe(STUDENTS_CSV, ['name', 'qr_code', 'phone'])
                # student_groups 정보가 필요하면 로드
                df_student_groups = pd.read_csv(STUDENT_GROUPS_CSV) if os.path.exists(STUDENT_GROUPS_CSV) else pd.DataFrame()
                df_groups = load_class_groups()
                
                # 1. 대상 날짜 데이터만 필터링
                df_course = df_att[df_att['date'].isin(target_dates_str)].copy()
                
                # 2. 학생별-날짜별 피벗 테이블 생성
                if not df_course.empty:
                    # Pivot
                    pivot_df = df_course.pivot_table(
                        index='student_name', 
                        columns='date', 
                        values='status', 
                        aggfunc=lambda x: list(x)[0]
                    ).reset_index()
                    
                    # 없는 날짜 컬럼 추가
                    for d in target_dates_str:
                        if d not in pivot_df.columns:
                            pivot_df[d] = None
                    
                    # 3. 데이터 정제 (아이콘 표시)
                    def get_status_icon(val):
                        if pd.isna(val) or val is None: return "⚪ -"
                        if val in [ATTENDANCE_STATUS_PRESENT, ATTENDANCE_STATUS_LATE, "출석", "지각"]: return "✅ 출석"
                        if val in [ATTENDANCE_STATUS_ABSENT, "결석"]: return "❌ 결석"
                        return f"❓ {val}"
    
                    display_df = pivot_df.copy()
                    for d in target_dates_str:
                        display_df[d] = display_df[d].apply(get_status_icon)
                    
                    # 4. 출석률 산출
                    def calc_rate(row_idx):
                        attended = 0
                        for d in target_dates_str:
                            val = pivot_df.iloc[row_idx][d]
                            if val in [ATTENDANCE_STATUS_PRESENT, ATTENDANCE_STATUS_LATE, "출석", "지각"]:
                                attended += 1
                        return f"{(attended / 4) * 100:.0f}% ({attended}/4)"
    
                    display_df['최종 이수율'] = [calc_rate(i) for i in range(len(pivot_df))]
                    
                    # 5. 반(Group) 정보 매칭
                    if not df_student_groups.empty and not df_groups.empty:
                        name_to_group = {}
                        for _, sg in df_student_groups.iterrows():
                            g_info = df_groups[df_groups['group_id'] == sg['group_id']]
                            if not g_info.empty:
                                name_to_group[sg['student_name']] = g_info.iloc[0]['group_name']
                        
                        display_df.insert(1, '소속 반', display_df['student_name'].map(name_to_group))
                    
                    # 컬럼 순서 조정
                    cols = ['student_name']
                    if '소속 반' in display_df.columns: cols.append('소속 반')
                    cols.extend(target_dates_str)
                    cols.append('최종 이수율')
                    
                    # 6. 출력
                    st.dataframe(
                        display_df[cols].rename(columns={'student_name': '학생 성함'}),
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # 7. 다운로드 버튼
                    csv = display_df[cols].to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        "📥 강좌 이수 리포트 다운로드 (CSV)",
                        csv,
                        "course_completion_report.csv",
                        "text/csv",
                        use_container_width=True,
                        key="download_course_completion_csv"
                    )
                else:
                    st.warning("⚠️ 대상 날짜(4/4~4/25)의 출석 데이터가 없습니다.")
                    
            except Exception as e:
                st.error(f"리포트 생성 오류: {e}")
                logger.error(f"Course report error: {e}")
    
    # ==========================================
    # 🔐 사용자 관리
    # ==========================================
    elif tab == "🔐 사용자 관리":
        st.header("🔐 사용자 관리")
        
        if not check_permission(user['role'], 'can_manage_users'):
            st.error("⚠️ 사용자 관리 권한이 없습니다.")
            st.stop()
        
        # df_users = auth.load_users() # 상단 공통 로드로 대체
        
        st.subheader(f"👥 전체 사용자 ({len(df_users)}명)")
        
        for idx, row in df_users.iterrows():
            role = row['role']
            badge_class = f"badge-{role}"
            
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                st.markdown(f"""
                <div style="background: white; padding: 15px; border-radius: 10px; margin: 5px 0;">
                    <div style="font-weight: bold; font-size: 16px;">
                        {row['name']}
                        <span class="user-badge {badge_class}">{get_role_display_name(role)}</span>
                    </div>
                    <div style="color: #666; font-size: 14px; margin-top: 5px;">
                        🆔 {row['username']} | 📧 {row.get('email', 'N/A')}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.caption(f"전화: {row.get('phone', 'N/A')}")
                if row.get('student_id'):
                    st.caption(f"학생: {row['student_id']}")
            
            with col3:
                if row['role'] != 'admin':
                    if st.button("🗑️", key=f"del_user_{idx}", help="삭제", use_container_width=True):
                        if delete_user(row['user_id']):
                            st.success("사용자가 삭제되었습니다.")
                            st.rerun()
        
        st.markdown("###")
        
        with st.expander("➕ 새 사용자 추가"):
            st.markdown("### 사용자 생성")
            
            new_username = st.text_input("아이디", key="new_user_id")
            new_password = st.text_input("비밀번호", type="password", key="new_user_pw")
            new_role = st.selectbox("역할", ["admin", "teacher", "parent", "student"], key="new_user_role_select")
            new_name = st.text_input("이름", key="new_user_name")
            new_phone = st.text_input("전화번호 (선택)", key="new_user_phone")
            new_email = st.text_input("이메일 (선택)", key="new_user_email")
            
            if new_role in ['parent', 'student']:
                new_student_id = st.selectbox("연결할 학생", st.session_state.attendees, key="new_user_student_connect")
            else:
                new_student_id = ""
            
            if st.button("➕ 사용자 생성", use_container_width=True, key="btn_create_user_final"):
                if new_username and new_password and new_name:
                    result = create_user(
                        username=new_username,
                        password=new_password,
                        role=new_role,
                        name=new_name,
                        phone=normalize_phone(new_phone),
                        student_id=new_student_id,
                        email=new_email
                    )
                    
                    if result:
                        st.success("✅ 사용자가 생성되었습니다!")
                        st.rerun()
                    else:
                        st.error("이미 존재하는 아이디입니다.")
                else:
                    st.error("필수 정보를 모두 입력해주세요.")
    
    # 푸터
    st.markdown("---")
    st.caption("© 2025 온라인아카데미 QR 전자출석시스템 | 관리자 버전 v3.7 (완전판)")

if __name__ == "__main__":
    main()

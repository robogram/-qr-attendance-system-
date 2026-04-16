"""
학생 앱 - 완전한 최종 버전 (수업 상태 표시 수정)
수업 그룹 연동 + 수료증 발급 + 교육시간 계산 + 시간 기반 상태 판단
"""
import streamlit as st
# 페이지 설정 (포털 통합 시 중복 호출 방지)
try:
    st.set_page_config(
        page_title="학생 앱 - 온라인아카데미",
        page_icon="🎒",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
except st.errors.StreamlitAPIException:
    pass

import pandas as pd

# -- Supabase Proxy Helpers --
from supabase_client import supabase_mgr
import pandas as pd
import unicodedata
import os
import logging
from functools import lru_cache
import re

# 로그 설정 (초기화)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def normalize_text(text):
    """한글 정규화 (NFC) 및 공백 제거"""
    if text is None: return ""
    return unicodedata.normalize('NFC', str(text)).strip()

def get_students_df():
    try:
        students = supabase_mgr.get_all_students()
        df = pd.DataFrame(students)
        if not df.empty:
            df = df.rename(columns={'student_name': 'name', 'qr_code_data': 'qr_code', 'parent_contact': 'phone'})
        return df if not df.empty else pd.DataFrame(columns=['name', 'qr_code', 'phone'])
    except Exception as e:
        logger.error(f"Error fetching students: {e}")
        return pd.DataFrame(columns=['name', 'qr_code', 'phone'])

def get_schedule_df():
    try:
        schedules = supabase_mgr.get_all_schedules()
        if not schedules:
            logger.warning("No schedules returned from Supabase")
            return pd.DataFrame(columns=['date', 'start', 'end', 'session'])
        data = []
        for s in schedules:
            # 🆕 타임존 고려 (UTC -> KST 변환)
            st_dt = pd.to_datetime(s['start_time'])
            en_dt = pd.to_datetime(s['end_time'])
            
            # 타임존 정보가 없으면 UTC로 가정하고 KST(+09:00)로 변환
            if st_dt.tzinfo is None:
                st_dt = st_dt.replace(tzinfo=pd.Timestamp.now(tz='UTC').tzinfo)
                en_dt = en_dt.replace(tzinfo=pd.Timestamp.now(tz='UTC').tzinfo)
            
            st_dt = st_dt.astimezone(pd.Timestamp.now(tz='Asia/Seoul').tzinfo)
            en_dt = en_dt.astimezone(pd.Timestamp.now(tz='Asia/Seoul').tzinfo)
            
            # 🆕 이름 정규화 (NFC 적용)
            c_name = normalize_text(s.get('class_name', 'Unknown'))
            data.append({
                'date': st_dt.strftime('%Y-%m-%d'),
                'start': st_dt.strftime('%H:%M'),
                'end': en_dt.strftime('%H:%M'),
                'session': c_name,
                'id': s['id']
            })
        return pd.DataFrame(data)
    except Exception as e:
        logger.error(f"Error fetching schedules: {e}")
        return pd.DataFrame(columns=['date', 'start', 'end', 'session'])

def get_attendance_df():
    """
    Supabase의 출석 데이터를 관리자 앱 스타일로 가져옵니다.
    관계형 쿼리(select)를 사용하여 학생과 일정 정보를 한 번에 조인하여 가져옵니다.
    """
    try:
        # students 및 schedule 테이블과의 관계를 활용하여 필요한 모든 데이터 일괄 조회
        response = supabase_mgr.client.table('attendance')\
            .select('id, check_in_time, status, type, remark, students!student_id(id, student_name, qr_code_data), schedule(id, class_name, start_time)')\
            .execute()
        
        data = []
        if response.data:
            for r in response.data:
                # 단일 객체 또는 리스트 형태로 반환될 수 있는 중첩 데이터 추출
                student_data = r.get('students', {}) or {}
                if isinstance(student_data, list) and len(student_data) > 0:
                    student_data = student_data[0]
                
                schedule_data = r.get('schedule', {}) or {}
                if isinstance(schedule_data, list) and len(schedule_data) > 0:
                    schedule_data = schedule_data[0]
                
                # 정규화 및 데이터 추출
                s_id = student_data.get('id')
                s_name = normalize_text(student_data.get('student_name', 'Unknown'))
                s_qr = normalize_text(student_data.get('qr_code_data', 'Unknown'))
                
                sched_id = schedule_data.get('id')
                session = normalize_text(schedule_data.get('class_name', 'Unknown'))
                
                check_in_time = r.get('check_in_time')
                
                # 한국 시간(KST)으로 변환하여 날짜 정보 생성
                dt_obj = pd.to_datetime(check_in_time) if check_in_time else None
                date_obj = dt_obj.date() if dt_obj else None
                
                data.append({
                    'id': r.get('id'),
                    'student_id': s_id,
                    'schedule_id': sched_id,
                    'student_name': s_name,
                    'qr_code': s_qr,
                    'session': session,
                    'status': r.get('status', ATTENDANCE_STATUS_PRESENT),
                    'type': r.get('type', 'QR'),
                    'timestamp': str(check_in_time) if check_in_time else '',
                    'date': date_obj
                })
        
        if not data:
            return pd.DataFrame(columns=['id', 'student_id', 'schedule_id', 'date', 'session', 'student_name', 'qr_code', 'timestamp', 'status', 'type'])
        
        df_res = pd.DataFrame(data)
        # 중복 기록 방지 (동일 시간, 동일 학생, 동일 세션)
        df_res = df_res.drop_duplicates(subset=['timestamp', 'student_id', 'schedule_id'])
        return df_res
    except Exception as e:
        logger.error(f"Error fetching attendance (Relational): {e}")
        return pd.DataFrame(columns=['id', 'student_id', 'schedule_id', 'date', 'session', 'student_name', 'qr_code', 'timestamp', 'status', 'type'])

def robust_match(target, candidate):
    """유연한 문자열 매칭 (정규화, 공백 무시, 대소문자 무시, 정규식 기반 클래스 문자 추출)"""
    if not target or not candidate: return False
    
    # 1. 완전 일치 (NFC 정규화 후 대소문자 무관)
    target = normalize_text(target).upper()
    candidate = normalize_text(candidate).upper()
    if target == candidate: return True
    
    # 2. 포함 관계 확인 (유연한 매칭)
    if target in candidate or candidate in target: return True
    
    # 3. 특수 문자 제거 후 숫자/영문/한글 핵심 단어 비교
    t_letter = re.sub(r'[^A-Z0-9가-힣]', '', target)
    c_letter = re.sub(r'[^A-Z0-9가-힣]', '', candidate)
    
    if t_letter and c_letter and (t_letter in c_letter or c_letter in t_letter):
        return True
    
    # 4. Super-Fuzzy: 맨 앞 한 글자만 같아도 매칭 (A, B, C 등 식별자 위주)
    if len(target) > 0 and len(candidate) > 0:
        if target[0] == candidate[0]: return True

    # 5. '반' 글자 제외 비교
    t_clean = target.replace("반", "").strip()
    c_clean = candidate.replace("반", "").strip()
    if t_clean == c_clean and t_clean != "": return True
    
    return False
# ----------------------------

from datetime import datetime, date, timedelta, time
import qrcode
import io
from utils import load_csv_safe, save_csv_safe
from config import (
    STUDENTS_CSV,
    ATTENDANCE_LOG_CSV,
    SCHEDULE_CSV,
    FLASK_PORT,                    # ← 🆕 추가
    # 🆕 출석 상태 상수 추가
    ATTENDANCE_STATUS_PRESENT,
    ATTENDANCE_STATUS_LATE,
    ATTENDANCE_STATUS_ABSENT,
)

from PIL import Image, ImageDraw, ImageFont
import base64

from auth import (
    authenticate_user,
    # 기타 필요한 imports...
)    

# 로거 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 수업 그룹 관련 파일
CLASS_GROUPS_CSV = "class_groups.csv"
STUDENT_GROUPS_CSV = "student_groups.csv"

# ⭐ 상수 정의
ATTENDANCE_BUFFER_MINUTES = 30  # 출석 체크 시간 버퍼
MAX_IMAGE_SIZE_MB = 5
MAX_IMAGE_DIMENSIONS = (1200, 1600)
IMAGE_QUALITY = 85

# 페이지 설정
st.set_page_config(
    page_title="학생 앱 - 온라인아카데미",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 세션 초기화
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'selected_group_id' not in st.session_state:
    st.session_state.selected_group_id = None

# 로그인 체크
if not st.session_state.authenticated or st.session_state.user is None:
    st.error("🔒 로그인이 필요합니다.")
    with st.form("quick_login"):
        st.markdown("### 🎮 학생 로그인")
        username = st.text_input("아이디")
        password = st.text_input("비밀번호", type="password")
        
        if st.form_submit_button("로그인", use_container_width=True):
            from auth import authenticate_user
            user = authenticate_user(username, password)
            
            if user:
                st.session_state.user = user
                st.session_state.authenticated = True
                st.success("로그인 성공!")
                st.balloons()
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
    st.stop()

# --- 🆕 사이드바 새로고침 버튼 ---
if st.sidebar.button("🔄 데이터 새로고침", use_container_width=True):
    st.cache_data.clear()
    st.success("데이터를 새로 불러옵니다.")
    st.rerun()

user = st.session_state.user

# 학생 권한 체크
if user.get('role') != 'student':
    st.error("⚠️ 학생만 접근 가능한 페이지입니다.")
    if st.button("🚪 로그아웃", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user = None
        st.rerun()
    st.stop()


# ==================== CSS 스타일 ====================
st.markdown("""
<style>
    .main { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .student-header {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white; padding: 30px; border-radius: 20px; text-align: center;
        margin-bottom: 30px; box-shadow: 0 8px 20px rgba(0,0,0,0.3);
    }
    
    /* 🔥 모바일 최적화 */
    @media (max-width: 768px) {
        .student-header {
            padding: 20px 15px;
        }
        .student-header h1 {
            font-size: 24px !important;
            line-height: 1.3;
            word-wrap: break-word;
        }
        .stat-card {
            padding: 15px !important;
            margin: 5px 0 !important;
        }
        .stat-number {
            font-size: 28px !important;
        }
        .mission-card {
            padding: 15px !important;
            margin: 10px 0 !important;
        }
        .progress-container {
            height: 30px !important;
        }
        .progress-bar {
            font-size: 14px !important;
        }
    }
    
    .stat-card {
        background: white; border-radius: 20px; padding: 25px; text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2); margin: 10px 0;
        transition: transform 0.2s;
    }
    .stat-card:hover {
        transform: translateY(-2px);
    }
    .stat-number { 
        font-size: 36px; font-weight: bold; color: #667eea; margin: 10px 0;
        word-wrap: break-word;
    }
    .mission-card {
        background: white; border-left: 5px solid #4CAF50; border-radius: 10px;
        padding: 20px; margin: 15px 0; box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        transition: all 0.2s;
    }
    .mission-card:hover {
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .mission-complete { border-left-color: #4CAF50; background: #e8f5e9; }
    .mission-progress { border-left-color: #FF9800; background: #fff3e0; }
    .progress-container {
        background: #e0e0e0; border-radius: 20px; height: 40px; overflow: hidden; margin: 20px 0;
    }
    .progress-bar {
        height: 100%; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        display: flex; align-items: center; justify-content: center; color: white;
        font-weight: bold; font-size: 18px; transition: width 1s ease;
    }
    .certificate-card {
        background: white; border-radius: 20px; padding: 30px; text-align: center;
        box-shadow: 0 8px 20px rgba(0,0,0,0.2); margin: 20px 0;
    }
    
    /* 텍스트 줄바꿈 처리 */
    h1, h2, h3, p {
        word-wrap: break-word;
        overflow-wrap: break-word;
    }
    
    /* 로딩 스피너 */
    .loading-spinner {
        border: 4px solid #f3f3f3;
        border-top: 4px solid #667eea;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
        margin: 20px auto;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
</style>
""", unsafe_allow_html=True)


# ==================== 캐싱된 데이터 로드 함수 ====================
@st.cache_data(ttl=60)
def load_class_groups_cached():
    """수업 그룹 정보 로드 (캐싱)"""
    if not os.path.exists(CLASS_GROUPS_CSV):
        return pd.DataFrame(columns=['group_id', 'group_name', 'weekdays', 'start_time', 'end_time', 'start_date', 'end_date', 'total_hours'])
    try:
        df = pd.read_csv(CLASS_GROUPS_CSV, encoding='utf-8-sig')
        if 'total_hours' not in df.columns:
            df['total_hours'] = 1.0
        return df
    except Exception as e:
        logger.error(f"Error loading class groups: {e}")
        return pd.DataFrame(columns=['group_id', 'group_name', 'weekdays', 'start_time', 'end_time', 'start_date', 'end_date', 'total_hours'])

@st.cache_data(ttl=60)
def load_student_groups_cached():
    """학생-그룹 매핑 로드 (캐싱)"""
    if not os.path.exists(STUDENT_GROUPS_CSV):
        return pd.DataFrame(columns=['student_name', 'group_id'])
    try:
        df = pd.read_csv(STUDENT_GROUPS_CSV, encoding='utf-8-sig')
        return df
    except Exception as e:
        logger.error(f"Error loading student groups: {e}")
        return pd.DataFrame(columns=['student_name', 'group_id'])

@st.cache_data(ttl=30)
def load_attendance_cached():
    """출석 기록 로드 (캐싱 적용)"""
    return get_attendance_df()


# ==================== 핵심 비즈니스 로직 ====================
def get_student_groups(student_name):
    """학생이 속한 그룹 ID 목록"""
    df_student_groups = load_student_groups_cached()
    if df_student_groups.empty:
        return []
    
    group_ids = df_student_groups[df_student_groups['student_name'] == student_name]['group_id'].tolist()
    return group_ids


def calculate_total_education_hours(student_name, group_id=None):
    """학생의 총 교육시간 계산 (특정 그룹 또는 전체)"""
    try:
        student_group_ids = get_student_groups(student_name)
        
        if not student_group_ids:
            return 1.0
        
        # 특정 그룹만 계산
        if group_id:
            student_group_ids = [group_id]
        
        df_groups = load_class_groups_cached()
        if df_groups.empty:
            return 1.0
        
        student_groups = df_groups[df_groups['group_id'].isin(student_group_ids)]
        if student_groups.empty:
            return 1.0
        
        # total_hours 컬럼이 있으면 그대로 사용
        if 'total_hours' in student_groups.columns:
            total_hours = student_groups['total_hours'].sum()
            return round(total_hours, 1)
        
        # 없으면 계산
        total_hours = 0
        for _, group in student_groups.iterrows():
            try:
                start_time = datetime.strptime(group['start_time'], '%H:%M').time()
                end_time = datetime.strptime(group['end_time'], '%H:%M').time()
                start_dt = datetime.combine(date.today(), start_time)
                end_dt = datetime.combine(date.today(), end_time)
                duration_hours = (end_dt - start_dt).total_seconds() / 3600
                
                weekdays = [int(x) for x in str(group['weekdays']).split(',')]
                start_date = pd.to_datetime(group['start_date']).date()
                end_date = pd.to_datetime(group['end_date']).date()
                
                # 수업 횟수 계산
                classes_count = 0
                current_date = start_date
                while current_date <= end_date:
                    if current_date.weekday() in weekdays:
                        classes_count += 1
                    current_date += timedelta(days=1)
                
                group_hours = duration_hours * classes_count
                if group_hours < 1:
                    group_hours = 1.0
                
                total_hours += group_hours
            except Exception as e:
                logger.warning(f"Error calculating hours for group {group.get('group_id')}: {e}")
                total_hours += 1.0
        
        return round(total_hours, 1)
    
    except Exception as e:
        logger.error(f"Error calculating total education hours: {e}")
        return 1.0


def get_student_attendance_for_group(student_name, group_id):
    """
    특정 학생의 특정 그룹에 대한 출결 현황을 ID 기반으로 정확히 조회 (관리자 리포트 방식)
    """
    try:
        # 1. 관리 대상 학생의 DB ID 찾기
        df_students_db = get_students_df()
        s_norm = normalize_text(student_name).upper()
        s_row = df_students_db[df_students_db['name'].apply(normalize_text).str.upper() == s_norm]
        
        if s_row.empty:
            # 학생 이름으로 못 찾을 경우 QR 코드로 재시도 (사용자 이름이 QR 코드인 경우 대비)
            s_row = df_students_db[df_students_db['qr_code'].fillna('').apply(normalize_text).str.upper() == s_norm]
            
        if s_row.empty:
            return pd.DataFrame(), {}
        
        db_student_id = s_row.iloc[0].get('id')
        
        # 2. 수업 그룹 정보 로드
        df_groups = load_class_groups_cached()
        df_groups['group_id_str'] = df_groups['group_id'].astype(str)
        group_row = df_groups[df_groups['group_id_str'] == str(group_id)]
        if group_row.empty:
            return pd.DataFrame(), {}
        
        group_info = group_row.iloc[0].to_dict()
        group_name = normalize_text(group_info['group_name'])
        
        # 3. 해당 그룹의 모든 일정(ID) 가져오기
        df_schedule_all = get_schedule_df()
        # 그룹 이름이 포함된 일정들 필터링 (robust_match 활용)
        group_schedules = df_schedule_all[df_schedule_all['session'].apply(lambda x: robust_match(group_name, x))].copy()
        target_schedule_ids = group_schedules['id'].tolist()
        
        # 4. 출석 데이터 전체 로드
        df_attendance_all = load_attendance_cached()
        if df_attendance_all.empty:
            group_attendance = pd.DataFrame()
        else:
            # 🆕 [하이브리드 매칭] 관리자 앱과 동일한 수준의 데이터 확보
            # 방법 A: 정확한 ID 기반 매칭 (Supabase 관계형)
            match_id = (df_attendance_all['student_id'] == db_student_id) & \
                        (df_attendance_all['schedule_id'].isin(target_schedule_ids))
            
            # 방법 B: 이름 + 세션 + 날짜 기반 매칭 (ID 링크가 없거나 유실된 과거 데이터 복구용)
            # 관리자 앱 리포트가 사용하는 방식과 동일함
            s_name_norm = normalize_text(student_name).upper()
            match_name = (df_attendance_all['student_name'].apply(normalize_text).str.upper() == s_name_norm) & \
                         (df_attendance_all['session'].apply(lambda x: robust_match(group_name, x)))
            
            group_attendance = df_attendance_all[match_id | match_name].copy()
        
        # 5. 시각화 데이터 구성 (일정 기준 루프)
        full_history = []
        today_date = date.today()
        
        if not group_schedules.empty:
            # 일정을 최신순으로 정렬
            group_schedules = group_schedules.sort_values('date', ascending=False)
            
            for _, sch in group_schedules.iterrows():
                sch_id = sch['id']
                sch_date = pd.to_datetime(sch['date']).date()
                
                # 해당 일정에 맞는 출석 기록 찾기 (ID 또는 날짜/세션으로 대조)
                date_records = group_attendance[
                    (group_attendance['schedule_id'] == sch_id) | 
                    (group_attendance['date'] == sch_date)
                ]
                
                if not date_records.empty:
                    # 출석 기록이 있는 경우 (중복 제거 후 추가)
                    for _, r in date_records.drop_duplicates(subset=['timestamp', 'status']).iterrows():
                        full_history.append(r.to_dict())
                else:
                    # 출석 기록이 없는 경우 -> '결석' 또는 '수업 예정' 처리
                    # 🆕 오늘 날짜 기준으로 과거면 결석, 오늘이거나 미래면 예정
                    if sch_date < today_date:
                        status_label = "❌ 결석 (미출석)"
                    else:
                        status_label = "⏳ 수업 예정"
                    
                    iso_timestamp = f"{sch['date']}T{sch.get('start', '09:30')}:00+09:00"
                    
                    full_history.append({
                        'timestamp': iso_timestamp,
                        'date': sch_date,
                        'student_name': student_name,
                        'session': group_name,
                        'status': status_label,
                        'type': '-',
                        'schedule_id': sch_id,
                        'student_id': db_student_id
                    })
        
        result_df = pd.DataFrame(full_history)
        if not result_df.empty:
            # 날짜순 정렬
            result_df['date_dt'] = pd.to_datetime(result_df['date'])
            result_df = result_df.sort_values('date_dt', ascending=False).drop(columns=['date_dt'])
            
        return result_df, group_info
        
    except Exception as e:
        logger.error(f"Error in ID-based attendance matching: {e}")
        return pd.DataFrame(), {}


def calculate_group_statistics(attendance_df, group_info):
    """그룹별 통계 계산"""
    try:
        # 기본값
        stats = {
            'total_attendance': 0,
            'present': 0,
            'late': 0,
            'absent': 0,
            'total_classes': 0,
            'attendance_rate': 0,
            'level': 0,
            'consecutive_classes': 0,
            'streak': 0
        }
        
        # 스케줄에서 이 수업 수 계산 (날짜 기준으로 중복 제거하여 실제 수업 일수 계산)
        df_schedule = get_schedule_df()
        if not df_schedule.empty and group_info:
            group_name = group_info.get('group_name', '')
            df_schedule['date'] = pd.to_datetime(df_schedule['date'], errors='coerce').dt.date
            # 🆕 유연한 매칭 적용
            group_schedule = df_schedule[df_schedule['session'].apply(lambda x: robust_match(group_name, x))]
            # [🆕 핵심 수정] 일정 개수가 아닌 '수업 날짜 수'를 전체 수업으로 인정
            stats['total_classes'] = group_schedule['date'].nunique()
            logger.info(f"calculate_group_statistics: {group_name} -> total_classes={stats['total_classes']}")
        
        # 🆕 출석 통계 (실제 출석/지각만 집계)
        if not attendance_df.empty:
            # 출석 인정 범위: '출석' 또는 '지각'만 인정 (수업 예정이나 결석 제외)
            is_present_mask = attendance_df['status'].isin([
                ATTENDANCE_STATUS_PRESENT, "출석", 
                ATTENDANCE_STATUS_LATE, "지각"
            ])
            stats['total_attendance'] = is_present_mask.sum()
            
            stats['present'] = len(attendance_df[attendance_df['status'].isin([ATTENDANCE_STATUS_PRESENT, "출석"])])
            stats['late'] = len(attendance_df[attendance_df['status'].isin([ATTENDANCE_STATUS_LATE, "지각"])])
            
            # 🆕 결석 수 = 실제 결석 기록 + 기록 없는 지난 수업
            # 결석 판정은 '수업 예정'이 아닌 것 중 '출석/지각'이 아닌 것
            is_absent_mask = attendance_df['status'].isin([ATTENDANCE_STATUS_ABSENT, "결석"]) | \
                             attendance_df['status'].str.contains("결석", na=False)
            stats['absent'] = is_absent_mask.sum()
            
            # 🆕 출석률 계산 (출석 + 지각만 / 전체 수업)
            if stats['total_classes'] > 0:
                stats['attendance_rate'] = (stats['total_attendance'] / stats['total_classes']) * 100
            
            # 레벨, 연속 출석 계산
            stats['level'] = calculate_level(stats['total_attendance'])
            stats['consecutive_classes'] = calculate_consecutive_classes(attendance_df)
            stats['streak'] = calculate_streak(attendance_df)
        else:
            # 🆕 attendance_df가 비어있으면 = 모든 수업 결석
            if stats['total_classes'] > 0:
                stats['absent'] = stats['total_classes']
                stats['attendance_rate'] = 0
        
        return stats
    
    except Exception as e:
        logger.error(f"Error calculating group statistics: {e}")
        return {
            'total_attendance': 0,
            'present': 0,
            'late': 0,
            'absent': 0,
            'total_classes': 0,
            'attendance_rate': 0,
            'level': 0,
            'consecutive_classes': 0,
            'streak': 0
        }


def calculate_level(total_attendance):
    """레벨 계산"""
    if total_attendance >= 50:
        return 10
    elif total_attendance >= 40:
        return 9
    elif total_attendance >= 30:
        return 8
    elif total_attendance >= 25:
        return 7
    elif total_attendance >= 20:
        return 6
    elif total_attendance >= 15:
        return 5
    elif total_attendance >= 10:
        return 4
    elif total_attendance >= 7:
        return 3
    elif total_attendance >= 5:
        return 2
    elif total_attendance >= 1:
        return 1
    else:
        return 0


def calculate_consecutive_classes(records):
    """연속 출석 수업 횟수 계산 (개선)"""
    try:
        if isinstance(records, pd.DataFrame):
            if records.empty:
                return 0
            records = records.to_dict('records')
        elif not records:
            return 0
        
        if not records:
            return 0
        
        # 날짜별로 정렬 (최신순)
        sorted_records = sorted(records, key=lambda x: x.get('date', date.today()), reverse=True)
        
        consecutive = 0
        for record in sorted_records:
            # 출석 또는 지각만 카운트
            if record.get('status') in [ATTENDANCE_STATUS_PRESENT, ATTENDANCE_STATUS_LATE]:
                consecutive += 1
            else:
                break
        
        return consecutive
    
    except Exception as e:
        logger.warning(f"Error calculating consecutive classes: {e}")
        return 0


def calculate_streak(records):
    """연속 출석 일수 계산"""
    try:
        if isinstance(records, pd.DataFrame):
            if records.empty:
                return 0
            records = records.to_dict('records')
        elif not records:
            return 0
        
        if not records:
            return 0
        
        # 유니크한 날짜만 추출
        sorted_dates = sorted(
            list(set([r['date'] for r in records if 'date' in r and r.get('status') in [ATTENDANCE_STATUS_PRESENT, ATTENDANCE_STATUS_LATE]])),
            reverse=True
        )
        
        if not sorted_dates:
            return 0
        
        streak = 0
        today = date.today()
        expected_date = today
        
        for record_date in sorted_dates:
            # 오늘이거나 바로 전날이면 연속
            if record_date == expected_date or record_date == expected_date - timedelta(days=1):
                streak += 1
                expected_date = record_date - timedelta(days=1)
            else:
                break
        
        return streak
    
    except Exception as e:
        logger.warning(f"Error calculating streak: {e}")
        return 0


def get_missions(stats, group_info):
    """미션 목록 생성"""
    missions = []
    
    total = stats.get('total_attendance', 0)
    consecutive_classes = stats.get('consecutive_classes', 0)
    level = stats.get('level', 0)
    total_classes = stats.get('total_classes', 1)
    attendance_rate = stats.get('attendance_rate', 0)
    
    # 미션 1: 첫 출석
    missions.append({
        "name": "🎯 첫 출석 달성",
        "progress": min(total, 1),
        "target": 1,
        "reward": "신입생 배지",
        "completed": total >= 1
    })
    
    # 미션 2: 절반 출석
    half_target = max(1, total_classes // 2)
    missions.append({
        "name": f"📚 {half_target}회 출석 달성",
        "progress": min(total, half_target),
        "target": half_target,
        "reward": "동메달 배지",
        "completed": total >= half_target
    })
    
    # 미션 3: 연속 출석
    consecutive_target = min(5, max(3, total_classes // 4))
    missions.append({
        "name": f"🔥 {consecutive_target}회 연속 출석",
        "progress": min(consecutive_classes, consecutive_target),
        "target": consecutive_target,
        "reward": "꾸준이 배지",
        "completed": consecutive_classes >= consecutive_target
    })
    
    # 미션 4: 출석률 100%
    missions.append({
        "name": "💯 출석률 100% 달성",
        "progress": min(attendance_rate, 100),
        "target": 100,
        "reward": "수료증 발급!",
        "completed": attendance_rate >= 100 and total >= total_classes
    })
    
    # 미션 5: 레벨업
    missions.append({
        "name": "⭐ 레벨 5 달성",
        "progress": level,
        "target": 5,
        "reward": "레벨업 보너스",
        "completed": level >= 5
    })
    
    return missions


def get_badges(stats):
    """획득한 배지"""
    badges = []
    
    total = stats.get('total_attendance', 0)
    present = stats.get('present', 0)
    consecutive = stats.get('consecutive_classes', 0)
    
    # 출석 횟수 배지
    if total >= 50:
        badges.append({"icon": "🏆", "name": "출석왕", "desc": "50회 출석"})
    elif total >= 30:
        badges.append({"icon": "🥇", "name": "금메달", "desc": "30회 출석"})
    elif total >= 20:
        badges.append({"icon": "🥈", "name": "은메달", "desc": "20회 출석"})
    elif total >= 10:
        badges.append({"icon": "🥉", "name": "동메달", "desc": "10회 출석"})
    elif total >= 5:
        badges.append({"icon": "🎖️", "name": "신입생", "desc": "5회 출석"})
    
    # 연속 출석 배지
    if consecutive >= 10:
        badges.append({"icon": "🔥", "name": "열정맨", "desc": "10회 연속"})
    elif consecutive >= 5:
        badges.append({"icon": "⚡", "name": "꾸준이", "desc": "5회 연속"})
    elif consecutive >= 3:
        badges.append({"icon": "✨", "name": "시작", "desc": "3회 연속"})
    
    # 완벽 출석 배지
    if total > 0 and present == total:
        badges.append({"icon": "💯", "name": "완벽", "desc": "지각 없음"})
    
    return badges


def generate_qr_code(data):
    """QR 코드 생성"""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return buf
    except Exception as e:
        logger.error(f"Error generating QR code: {e}")
        return None


def process_certificate_photo(uploaded_file):
    """수료증 사진 처리 및 최적화"""
    try:
        from PIL import ImageOps
        
        # 파일 크기 체크
        file_size_mb = uploaded_file.size / (1024 * 1024)
        if file_size_mb > MAX_IMAGE_SIZE_MB:
            st.warning(f"⚠️ 파일 크기가 {MAX_IMAGE_SIZE_MB}MB를 초과합니다. 자동으로 최적화합니다.")
        
        # 이미지 열기 및 EXIF 회전 보정
        img = Image.open(uploaded_file)
        img = ImageOps.exif_transpose(img)
        
        # 크기 조정
        if img.size[0] > MAX_IMAGE_DIMENSIONS[0] or img.size[1] > MAX_IMAGE_DIMENSIONS[1]:
            img.thumbnail(MAX_IMAGE_DIMENSIONS, Image.Resampling.LANCZOS)
        
        # RGB 변환
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        
        # 버퍼에 저장
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG', quality=IMAGE_QUALITY, optimize=True)
        img_buffer.seek(0)
        
        return img_buffer, img
    
    except Exception as e:
        logger.error(f"Error processing certificate photo: {e}")
        st.error(f"❌ 사진 처리 실패: {str(e)}")
        return None, None


def generate_certificate(student_name, school_name, course_name, start_date, end_date, total_hours, photo_buffer=None):
    """수료증 이미지 생성"""
    try:
        width, height = 800, 1000
        certificate = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(certificate)
        
        # 테두리
        border_color = '#DAA520'
        draw.rectangle([20, 20, width-20, height-20], outline=border_color, width=10)
        draw.rectangle([30, 30, width-30, height-30], outline=border_color, width=3)
        
        # 폰트 설정
        try:
            title_font = ImageFont.truetype("malgun.ttf", 60)
            subtitle_font = ImageFont.truetype("malgun.ttf", 30)
            body_font = ImageFont.truetype("malgun.ttf", 24)
        except:
            try:
                title_font = ImageFont.truetype("Arial.ttf", 60)
                subtitle_font = ImageFont.truetype("Arial.ttf", 30)
                body_font = ImageFont.truetype("Arial.ttf", 24)
            except:
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
                body_font = ImageFont.load_default()
        
        # 제목
        title = "수 료 증"
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        draw.text(((width - title_width) / 2, 100), title, fill='black', font=title_font)
        
        subtitle = "Certificate of Completion"
        subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
        draw.text(((width - subtitle_width) / 2, 180), subtitle, fill='gray', font=subtitle_font)
        
        # 사진 추가
        if photo_buffer:
            try:
                photo_img = Image.open(photo_buffer)
                photo_img.thumbnail((150, 200), Image.Resampling.LANCZOS)
                photo_x = width - 200
                photo_y = 250
                certificate.paste(photo_img, (photo_x, photo_y))
            except Exception as e:
                logger.warning(f"Failed to add photo to certificate: {e}")
        
        # 내용
        y_pos = 300
        lines = [
            f"• 성명 : {student_name}",
            f"• 학교명 : {school_name}",
            f"• 과정명 : {course_name}",
            f"• 교육기간 : {start_date} ~ {end_date}",
            f"• 교육시간 : {total_hours}시간"
        ]
        
        for line in lines:
            draw.text((100, y_pos), line, fill='black', font=body_font)
            y_pos += 50
        
        # 증명 문구
        y_pos += 30
        cert_text = "귀하는 (주)로보그램에서 주관하는 소정의\n과정을 수료하였음을 증명합니다."
        for text_line in cert_text.split('\n'):
            text_bbox = draw.textbbox((0, 0), text_line, font=body_font)
            text_width = text_bbox[2] - text_bbox[0]
            draw.text(((width - text_width) / 2, y_pos), text_line, fill='black', font=body_font)
            y_pos += 40
        
        # 발급일
        y_pos += 30
        issue_date = f"{date.today().year}년 {date.today().month:02d}월 {date.today().day:02d}일"
        date_bbox = draw.textbbox((0, 0), issue_date, font=body_font)
        date_width = date_bbox[2] - date_bbox[0]
        draw.text(((width - date_width) / 2, y_pos), issue_date, fill='black', font=body_font)
        
        # 발급 기관
        y_pos += 60
        issuer = "(주)로보그램"
        issuer_bbox = draw.textbbox((0, 0), issuer, font=title_font)
        issuer_width = issuer_bbox[2] - issuer_bbox[0]
        draw.text(((width - issuer_width) / 2, y_pos), issuer, fill='#667eea', font=title_font)
        
        # 직인 (있으면)
        try:
            if os.path.exists('seal.png'):
                seal_img = Image.open('seal.png')
                seal_img = seal_img.resize((150, 150), Image.Resampling.LANCZOS)
                if seal_img.mode == 'RGBA':
                    certificate.paste(seal_img, (width - 250, y_pos - 30), seal_img)
                else:
                    certificate.paste(seal_img, (width - 250, y_pos - 30))
        except Exception as e:
            logger.info("Seal image not found or failed to load")
        
        return certificate
    
    except Exception as e:
        logger.error(f"Error generating certificate: {e}")
        st.error(f"수료증 생성 오류: {e}")
        return None


# ==================== 메인 앱 ====================
def main():
    # 🆕 로그인 사용자 이름 정규화
    student_name = normalize_text(user.get('name', '학생'))
    
    # ========== 0. 시스템 진단 (디버그 모드) ==========
    # 진단 상태 초기화
    if 'diag_show_students' not in st.session_state: st.session_state.diag_show_students = False
    if 'diag_trace_student' not in st.session_state: st.session_state.diag_trace_student = False
    
    # 진단 도구 사용 중이면 익스팬더를 열어둠
    diag_expanded = st.session_state.diag_show_students or st.session_state.diag_trace_student or ('diag_logs' in st.session_state)
    # ✅ 데이터 새로고침 (간결한 관리 도구)
    with st.expander("🛠️ 시스템 관리", expanded=False):
        if st.button("🔄 모든 데이터 강제 새로고침", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.write(f"📡 서버 연결 상태: ✅ 정상")
    
    # ========== 1. 학생의 모든 그룹 가져오기 ==========
    student_group_ids = get_student_groups(student_name)
    df_groups = load_class_groups_cached()
    
    group_options = {}
    
    if student_group_ids and not df_groups.empty:
        student_groups = df_groups[df_groups['group_id'].isin(student_group_ids)]
        
        for _, group in student_groups.iterrows():
            group_name = group['group_name']
            start_date = group.get('start_date', '')
            end_date = group.get('end_date', '')
            
            # ⭐ 상태 판단 (날짜 + 시간 고려)
            try:
                end_dt = pd.to_datetime(end_date).date()
                end_time_str = group.get('end_time', '23:59')
                
                # 종료 일시 계산
                end_time = datetime.strptime(end_time_str, '%H:%M').time()
                end_datetime = datetime.combine(end_dt, end_time)
                now = datetime.now()
                
                # 상태 결정
                if end_datetime < now:
                    # 종료 시간이 현재보다 과거
                    status = "🔴 종료"
                elif end_dt == date.today():
                    # 오늘 수업 (아직 끝나지 않음)
                    status = "🟡 오늘 수업"
                elif end_dt < date.today():
                    # 과거 날짜
                    status = "🔴 종료"
                else:
                    # 미래 날짜
                    status = "🟢 진행중"
            except Exception as e:
                logger.warning(f"Error determining group status: {e}")
                status = "🟢 진행중"
            
            group_display = f"{group_name} ({group['start_time']}~{group['end_time']}) {status}"
            
            group_options[group_display] = {
                'group_id': group['group_id'],
                'group_name': group_name,
                'start_date': start_date,
                'end_date': end_date,
                'start_time': group['start_time'],
                'end_time': group['end_time'],
                'total_hours': group.get('total_hours', 1.0),
                'status': status
            }
    
    has_multiple_groups = len(group_options) > 1
    
    # ========== 2. 수업 선택 UI ==========
    selected_group_info = None
    
    if has_multiple_groups:
        # 이전 선택 유지
        default_index = 0
        if st.session_state.selected_group_id:
            for idx, (display, info) in enumerate(group_options.items()):
                if info['group_id'] == st.session_state.selected_group_id:
                    default_index = idx
                    break
        
        selected_group_display = st.selectbox(
            "🎓 수업 선택",
            list(group_options.keys()),
            index=default_index,
            key="group_selector"
        )
        
        selected_group_info = group_options[selected_group_display]
        st.session_state.selected_group_id = selected_group_info['group_id']
        
        # ⭐ 상태별 메시지 표시
        if "종료" in selected_group_info['status'] and "오늘" not in selected_group_info['status']:
            st.info(f"🔴 **종료된 수업**: {selected_group_info['group_name']} ({selected_group_info['start_date']} ~ {selected_group_info['end_date']})")
        elif "오늘" in selected_group_info['status']:
            st.success(f"🟡 **오늘 수업**: {selected_group_info['group_name']} ({selected_group_info['start_time']} ~ {selected_group_info['end_time']})")
        else:
            st.success(f"🟢 **진행중인 수업**: {selected_group_info['group_name']}")
        
        st.markdown("---")
    
    elif group_options:
        selected_group_info = list(group_options.values())[0]
        st.session_state.selected_group_id = selected_group_info['group_id']
    
    # ========== 3. 선택된 수업의 데이터 계산 ==========
    if selected_group_info:
        with st.spinner("데이터 로딩 중..."):
            group_id = selected_group_info['group_id']
            
            # 최적화된 함수 사용
            attendance_df, group_info = get_student_attendance_for_group(student_name, group_id)
            stats = calculate_group_statistics(attendance_df, group_info)
            
            # 교육시간 계산
            total_hours = calculate_total_education_hours(student_name, group_id)
    
    else:
        st.warning("⚠️ 등록된 수업이 없습니다. 관리자에게 문의하세요.")
        
        # 로그아웃 버튼
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🚪 로그아웃", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.user = None
                st.rerun()
        
        st.stop()
    
    # ========== 4. 헤더 표시 ==========
    if selected_group_info:
        # 상태에 따른 이모지와 텍스트
        if "종료" in selected_group_info['status'] and "오늘" not in selected_group_info['status']:
            status_emoji = "🔴"
            status_text = "종료된 수업"
        elif "오늘" in selected_group_info['status']:
            status_emoji = "🟡"
            status_text = "오늘 수업"
        else:
            status_emoji = "🟢"
            status_text = "진행중"
        
        group_info_html = f"<p style='margin-top: 10px; font-size: 18px;'>{status_emoji} {status_text}: {selected_group_info['group_name']} <span style='font-size: 14px; opacity: 0.8;'>({selected_group_info['start_date']} ~ {selected_group_info['end_date']})</span></p>"
    else:
        group_info_html = ""
    
    st.markdown(f"""
    <div class="student-header">
        <h1>🎮 {student_name}님의 출석 레벨업!</h1>
        {group_info_html}
        <div style="background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%); 
                    color: white; padding: 15px 30px; border-radius: 30px; 
                    font-size: 28px; font-weight: bold; display: inline-block; 
                    margin-top: 15px;">
            ⭐ Level {stats['level']}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ========== 5. 탭 UI ==========
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📱 내 QR", "🏆 미션", "🎖️ 배지", "📊 기록", "🎓 수료증"])
    
    # ==================== 탭 1: QR 코드 ====================
    with tab1:
        st.markdown("### 📱 내 QR 코드")
        st.info("학원 도착 시 이 QR을 제시하세요!")
        
        df_students = get_students_df()
        student_row = df_students[df_students['name'] == student_name]
        
        if not student_row.empty:
            qr_data = student_row.iloc[0]['qr_code']
            qr_buf = generate_qr_code(qr_data)
            
            if qr_buf:
                # 모바일: QR 중앙 정렬
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.image(qr_buf, use_container_width=True)
                
                st.download_button(
                    "📥 QR 코드 다운로드",
                    qr_buf.getvalue(),
                    file_name=f"{student_name}_QR.png",
                    mime="image/png",
                    use_container_width=True
                )
            else:
                st.error("QR 코드 생성 실패")
        
        st.markdown("---")
        st.markdown("### 📊 나의 출석 현황")
        
        # ⭐ 수업 정보 (상태별 메시지)
        if selected_group_info:
            # 상태별 메시지
            if "종료" in selected_group_info['status'] and "오늘" not in selected_group_info['status']:
                st.warning(f"""
                🔴 **종료된 수업**  
                🎓 {selected_group_info['group_name']}  
                📅 {selected_group_info['start_date']} ~ {selected_group_info['end_date']}  
                📚 전체 수업: {stats['total_classes']}회  
                🕐 총 교육시간: {total_hours}시간
                """)
            elif "오늘" in selected_group_info['status']:
                st.success(f"""
                🟡 **오늘 수업**  
                🎓 {selected_group_info['group_name']}  
                ⏰ {selected_group_info['start_time']} ~ {selected_group_info['end_time']}  
                📚 전체 수업: {stats['total_classes']}회  
                🕐 총 교육시간: {total_hours}시간
                """)
            else:
                st.info(f"""
                🟢 **진행중인 수업**  
                🎓 {selected_group_info['group_name']}  
                📚 전체 수업: {stats['total_classes']}회  
                🕐 총 교육시간: {total_hours}시간
                """)
        
        # 통계 카드 (모바일 최적화: 2열 레이아웃)
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown(f"""
            <div class="stat-card">
                <div style="font-size: 48px;">📚</div>
                <div class="stat-number">{stats['total_attendance']}</div>
                <div style="font-size: 16px; color: #666;">출석 횟수</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_b:
            st.markdown(f"""
            <div class="stat-card">
                <div style="font-size: 48px;">🔥</div>
                <div class="stat-number">{stats['consecutive_classes']}</div>
                <div style="font-size: 16px; color: #666;">연속 출석</div>
            </div>
            """, unsafe_allow_html=True)
        
        # 출석률
        st.markdown(f"""
        <div class="stat-card">
            <div style="font-size: 48px;">💯</div>
            <div class="stat-number">{stats['attendance_rate']:.0f}%</div>
            <div style="font-size: 16px; color: #666;">출석률</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("###")
        
        # 다음 레벨까지 진행률
        next_level_attendance = [1, 5, 7, 10, 15, 20, 25, 30, 40, 50]
        next_target = None
        
        for target in next_level_attendance:
            if stats['total_attendance'] < target:
                next_target = target
                break
        
        if next_target:
            progress = (stats['total_attendance'] / next_target) * 100
            remaining = next_target - stats['total_attendance']
            
            st.markdown(f"### 🎯 다음 레벨까지")
            st.markdown(f"""
            <div class="progress-container">
                <div class="progress-bar" style="width: {progress}%;">
                    {stats['total_attendance']} / {next_target}
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.info(f"⭐ 앞으로 {remaining}회 출석하면 레벨업!")
        else:
            st.success("🏆 최고 레벨 달성! 당신은 출석왕입니다!")
    
    # ==================== 탭 2: 미션 ====================
    with tab2:
        st.markdown("## 🎯 오늘의 미션")
        
        missions = get_missions(stats, selected_group_info)
        
        for mission in missions:
            progress_pct = (mission['progress'] / mission['target']) * 100 if mission['target'] > 0 else 0
            
            if mission['completed']:
                card_class = "mission-complete"
                status_icon = "✅"
            else:
                card_class = "mission-progress"
                status_icon = "⏳"
            
            st.markdown(f"""
            <div class="mission-card {card_class}">
                <div>
                    <h3>{status_icon} {mission['name']}</h3>
                    <p style="color: #666; margin: 10px 0;">
                        진행: {mission['progress']:.0f} / {mission['target']}
                    </p>
                    <p style="color: #4CAF50; font-weight: bold;">
                        보상: {mission['reward']}
                    </p>
                </div>
                <div class="progress-container" style="height: 20px; margin-top: 10px;">
                    <div class="progress-bar" style="width: {progress_pct}%; font-size: 14px;">
                        {progress_pct:.0f}%
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # ==================== 탭 3: 배지 ====================
    with tab3:
        st.markdown("## 🎖️ 내 배지 컬렉션")
        
        badges = get_badges(stats)
        
        if badges:
            # 모바일 최적화: 2열 레이아웃
            cols = st.columns(2)
            for idx, badge in enumerate(badges):
                with cols[idx % 2]:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                color: white; padding: 15px 20px; border-radius: 15px; margin: 10px 5px;
                                font-size: 24px; box-shadow: 0 4px 10px rgba(0,0,0,0.2); text-align: center;">
                        <div style="font-size: 48px;">{badge['icon']}</div>
                        <div style="font-size: 18px; font-weight: bold; margin-top: 10px;">
                            {badge['name']}
                        </div>
                        <div style="font-size: 14px; margin-top: 5px;">
                            {badge['desc']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.success(f"🏆 이 수업에서 {len(badges)}개의 배지를 획득했습니다!")
        else:
            st.info("아직 획득한 배지가 없습니다. 열심히 출석해서 배지를 모아보세요!")
    
    # ==================== 탭 4: 기록 ====================
    with tab4:
        st.markdown("## 📊 출석 기록")
        
        # 🆕 [추가] 매칭 진단 센터 (기록이 없을 때만 표시)
        if attendance_df.empty and 'diag_trace_student' in st.session_state and st.session_state.diag_trace_student:
            with st.warning("⚠️ **매칭 진단 센터**"):
                st.write(f"현재 선택된 수업: **{group_info.get('group_name', 'Unknown')}**")
                df_all_raw = load_attendance_cached()
                s_norm = normalize_text(student_name).upper()
                raw_hits = df_all_raw[df_all_raw['student_name'].fillna('').str.upper() == s_norm]
                if not raw_hits.empty:
                    st.write(f"💡 시스템이 전체 DB에서 학생의 기록을 **{len(raw_hits)}건** 찾았으나, 현재 수업명과 일치하지 않아 표시되지 않고 있습니다.")
                    st.write("DB에 기록된 수업명들:")
                    st.code(raw_hits['session'].unique().tolist())
                else:
                    st.write("💡 전체 DB에서도 해당 학생의 이름으로 기록된 데이터가 없습니다.")

        if not attendance_df.empty:
            records_df = attendance_df.copy()
            # 🆕 다양한 시간 형식을 안전하게 처리 (ISO8601 및 일반 형식 혼합 대응)
            records_df['dt'] = pd.to_datetime(records_df['timestamp'], errors='coerce', utc=True).dt.tz_convert('Asia/Seoul')
            records_df['날짜'] = records_df['dt'].dt.strftime('%Y-%m-%d')
            records_df['시간'] = records_df['dt'].dt.strftime('%H:%M')
            
            # 🆕 출석 수단 (QR/줌) 병기 -> 사용자의 요청으로 QR 표시 제거 및 줌 강조
            def get_display_status(row):
                is_zoom = (row.get('type') in ['온라인', 'Zoom', '줌'] or 'Zoom' in str(row['status']))
                att_type_label = "(줌)" if is_zoom else "" # QR은 삭제
                
                # 🆕 줌 출석은 지각이어도 무조건 "출석"으로 표시 (사용자 요청)
                status = row['status']
                if is_zoom and status in [ATTENDANCE_STATUS_LATE, "지각"]:
                    status = ATTENDANCE_STATUS_PRESENT
                
                # 아이콘 설정
                if status in [ATTENDANCE_STATUS_PRESENT, "출석"]:
                    icon = "✅"
                elif status in [ATTENDANCE_STATUS_LATE, "지각"]:
                    icon = "⏰"
                elif "수업 예정" in str(status):
                    icon = "⏳"
                else:
                    icon = "❌"
                
                # "결석 (미출석)" 등에서 불필요한 태그 제거
                clean_status = str(status).replace("(미출석)", "").strip()
                
                if att_type_label:
                    return f"{icon} {clean_status} {att_type_label}"
                return f"{icon} {clean_status}"

            records_df['상태'] = records_df.apply(get_display_status, axis=1)
            
            display_df = records_df[['날짜', '시간', '상태']].sort_values('날짜', ascending=False)
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # 통계
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("✅ 출석", stats['present'])
            with col2:
                st.metric("⏰ 지각", stats['late'])
            with col3:
                st.metric("❌ 결석", stats['absent'])
            with col4:
                st.metric("📚 총 수업", stats['total_classes'])
            
            st.markdown("###")
            
            # CSV 다운로드
            csv = display_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                "📥 출석 기록 다운로드",
                csv,
                file_name=f"{student_name}_{selected_group_info['group_name']}_출석기록.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("아직 이 수업의 출석 기록이 없습니다.")
    
    
    # ==================== 탭 5: 수료증 ====================
    with tab5:
        st.markdown("## 🎓 수료증 발급")
        
        # 🆕 수료 자격 확인 (강화된 조건)
        is_eligible = False
        
        if stats['total_classes'] > 0:
            # 🆕 결석이 하나라도 있으면 수료증 발급 불가
            has_no_absence = (stats['absent'] == 0)
            
            # 🆕 출석률 100% (출석 + 지각 = 전체 수업)
            perfect_attendance = (stats['total_attendance'] >= stats['total_classes'])
            
            # 🆕 실제 attendance_df에 결석 기록이 없는지 확인
            no_absence_records = True
            if not attendance_df.empty:
                absence_count = len(attendance_df[attendance_df['status'] == ATTENDANCE_STATUS_ABSENT])
                no_absence_records = (absence_count == 0)
            
            # 🆕 모든 조건을 만족해야 수료증 발급
            is_eligible = has_no_absence and perfect_attendance and no_absence_records
        
        # 디버깅 정보 (선택사항)
        with st.expander("🔍 수료 조건 확인 (디버깅)", expanded=False):
            st.write(f"전체 수업: {stats['total_classes']}회")
            st.write(f"출석: {stats['present']}회")
            st.write(f"지각: {stats['late']}회")
            st.write(f"결석(계산): {stats['absent']}회")
            if not attendance_df.empty:
                absence_count = len(attendance_df[attendance_df['status'] == ATTENDANCE_STATUS_ABSENT])
                st.write(f"결석(실제): {absence_count}회")
            st.write(f"출석+지각: {stats['total_attendance']}회")
            st.write(f"출석률: {stats['attendance_rate']:.1f}%")
            st.write(f"---")
            if stats['total_classes'] > 0:
                has_no_absence = (stats['absent'] == 0)
                perfect_attendance = (stats['total_attendance'] >= stats['total_classes'])
                no_absence_records = True
                if not attendance_df.empty:
                    absence_count = len(attendance_df[attendance_df['status'] == ATTENDANCE_STATUS_ABSENT])
                    no_absence_records = (absence_count == 0)
                st.write(f"조건1 (결석=0): {'✅' if has_no_absence else '❌'}")
                st.write(f"조건2 (출석+지각=전체): {'✅' if perfect_attendance else '❌'}")
                st.write(f"조건3 (결석기록=0): {'✅' if no_absence_records else '❌'}")
                st.write(f"**최종 판정: {'✅ 수료증 발급 가능' if is_eligible else '❌ 수료증 발급 불가'}**")
        
        if is_eligible:
            st.success("🎉 축하합니다! 이 수업의 수료증 발급 자격을 획득하셨습니다!")
            
            st.markdown("### 📸 사진 업로드")
            st.info("수료증에 들어갈 사진을 업로드해주세요. (선택사항)")
            
            with st.expander("💡 사진 업로드 팁"):
                st.markdown("""
                **iPhone 사용자:**
                - 설정 → 카메라 → 포맷 → "호환성 우선" 선택
                
                **Android 사용자:**
                - 대부분 자동으로 JPG 형식
                
                **권장 사항:**
                - 정면 사진 (증명사진 스타일)
                - 밝은 배경
                - 파일 크기 5MB 이하
                """)
            
            uploaded_photo = st.file_uploader(
                "사진 선택",
                type=['png', 'jpg', 'jpeg'],
                help="📸 사진이 자동으로 회전 보정되고 최적화됩니다"
            )
            
            photo_buffer = None
            preview_img = None
            
            if uploaded_photo:
                photo_buffer, preview_img = process_certificate_photo(uploaded_photo)
                
                if photo_buffer and preview_img:
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.image(preview_img, caption="업로드된 사진", width=150)
                    with col2:
                        st.success("✅ 사진이 성공적으로 업로드되었습니다!")
            
            st.markdown("###")
            
            # 학생 정보
            df_students = get_students_df()
            student_row = df_students[df_students['name'] == student_name]
            school_name = student_row.iloc[0]['school'] if not student_row.empty and 'school' in student_row.columns else ""
            
            course_name = f"{selected_group_info['group_name']} 과정"
            
            # 수료증 발급 버튼
            if st.button("🎓 수료증 발급", use_container_width=True, type="primary"):
                with st.spinner("수료증 생성 중..."):
                    certificate_img = generate_certificate(
                        student_name=student_name,
                        school_name=school_name,
                        course_name=course_name,
                        start_date=str(selected_group_info['start_date']),
                        end_date=str(selected_group_info['end_date']),
                        total_hours=total_hours,
                        photo_buffer=photo_buffer
                    )
                    
                    if certificate_img:
                        buf = io.BytesIO()
                        certificate_img.save(buf, format='PNG')
                        buf.seek(0)
                        
                        st.markdown("###")
                        st.markdown("### 🎓 당신의 수료증")
                        st.image(buf, use_container_width=True)
                        
                        st.download_button(
                            "📥 수료증 다운로드 (PNG)",
                            buf.getvalue(),
                            file_name=f"{student_name}_{selected_group_info['group_name']}_수료증.png",
                            mime="image/png",
                            use_container_width=True
                        )
                        st.balloons()
        
        else:
            st.warning("🎯 이 수업의 수료증 발급 조건을 아직 충족하지 못했습니다.")
            
            remaining_classes = max(0, stats['total_classes'] - stats['total_attendance'])
            
            # 조건부 아이콘 미리 계산
            icon_attendance = '✅' if stats['total_attendance'] >= stats['total_classes'] else '❌'
            icon_absent = '✅' if stats['absent'] == 0 else '❌'
            icon_rate = '✅' if stats['attendance_rate'] >= 100 else '❌'
            
            # 메시지 생성
            if remaining_classes > 0 and stats['absent'] == 0:
                message = f"앞으로 {remaining_classes}회 더 출석하면 수료증을 받을 수 있습니다!"
            elif stats['absent'] > 0:
                message = "결석이 있어 수료증을 받을 수 없습니다. 😢"
            else:
                message = "수료 조건을 충족하지 못했습니다."
            
            st.markdown(f"""
            <div class="certificate-card">
                <h3>📋 수료 조건</h3>
                <div style="text-align: left; margin: 20px 0;">
                    <p>✅ 전체 수업 횟수: {stats['total_classes']}회</p>
                    <p>{icon_attendance} 
                       현재 출석: {stats['total_attendance']}회 (출석 {stats['present']} + 지각 {stats['late']})</p>
                    <p>{icon_absent} 
                       결석: {stats['absent']}회 (필요: 0회)</p>
                    <p>{icon_rate} 
                       출석률: {stats['attendance_rate']:.0f}% (필요: 100%)</p>
                </div>
                <p style="color: #667eea; font-weight: bold; margin-top: 20px;">
                    {message}
                </p>
            </div>
            """, unsafe_allow_html=True)
                    
    # ========== 로그아웃 ==========
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🚪 로그아웃", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.selected_group_id = None
            st.rerun()


if __name__ == "__main__":
    main()

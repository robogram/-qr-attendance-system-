"""
학부모 앱 - 최종 완성 버전
오류 수정 완료 + 모든 기능 완전 구현 + 모바일/PC 최적화
"""
import streamlit as st

# 페이지 설정 (포털 통합 시 중복 호출 방지)
try:
    st.set_page_config(
        page_title="학부모 앱 - 온라인아카데미",
        page_icon="👨‍👩‍👧",
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
import re
import os
from datetime import datetime, timedelta, time, date, timezone
from utils import load_csv_safe, save_csv_safe, get_now_kst, get_today_kst
import calendar
import logging

def normalize_text(text):
    """한글 정규화 (NFC) 및 공력 제거"""
    if text is None: return ""
    return unicodedata.normalize('NFC', str(text)).strip()

def robust_match(target, candidate):
    """유연한 문자열 매칭 (정규화, 공백 무시, 대소문자 무시)"""
    if not target or not candidate: return False
    target = normalize_text(target).upper()
    candidate = normalize_text(candidate).upper()
    if target == candidate: return True
    if target in candidate or candidate in target: return True
    t_letter = re.sub(r'[^A-Z0-9가-힣]', '', target)
    c_letter = re.sub(r'[^A-Z0-9가-힣]', '', candidate)
    if t_letter and c_letter and (t_letter in c_letter or c_letter in t_letter):
        return True
    return False

def get_students_df():
    students = supabase_mgr.get_all_students()
    df = pd.DataFrame(students)
    if not df.empty:
        df = df.rename(columns={'student_name': 'name', 'qr_code_data': 'qr_code', 'parent_contact': 'phone'})
    return df if not df.empty else pd.DataFrame(columns=['name', 'qr_code', 'phone'])

def get_schedule_df():
    try:
        schedules = supabase_mgr.get_all_schedules()
        if not schedules:
            logger.warning("No schedules returned from Supabase")
            return pd.DataFrame(columns=['date', 'start', 'end', 'session', 'id'])
        
        data = []
        for s in schedules:
            # 🆕 KST 표준화 유틸리티 사용 (UTC -> KST 변환은 내부에서 처리)
            # s['start_time']과 s['end_time']은 ISO 포맷임
            st_dt = pd.to_datetime(s['start_time'])
            en_dt = pd.to_datetime(s['end_time'])
            
            # UTC로 명시되어 있으면 KST로 변환, 없으면 KST로 간주
            if st_dt.tzinfo is not None:
                st_dt = st_dt.tz_convert('Asia/Seoul')
                en_dt = en_dt.tz_convert('Asia/Seoul')
            else:
                st_dt = st_dt.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=9)))
                en_dt = en_dt.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=9)))
            
            data.append({
                'date': st_dt.strftime('%Y-%m-%d'),
                'start': st_dt.strftime('%H:%M'),
                'end': en_dt.strftime('%H:%M'),
                'session': s.get('class_name', 'Unknown'),
                'id': s['id']
            })
        return pd.DataFrame(data)
    except Exception as e:
        logger.error(f"Error fetching schedules: {e}")
        return pd.DataFrame(columns=['date', 'start', 'end', 'session', 'id'])

def get_attendance_df():
    """Supabase 출석 데이터를 관계형 쿼리로 정밀하게 가져옵니다."""
    try:
        response = supabase_mgr.client.table('attendance')\
            .select('id, check_in_time, status, type, students!student_id(id, student_name, qr_code_data), schedule(id, class_name, start_time)')\
            .execute()
        
        data = []
        if response.data:
            for r in response.data:
                student_data = r.get('students', {}) or {}
                if isinstance(student_data, list) and len(student_data) > 0:
                    student_data = student_data[0]
                
                schedule_data = r.get('schedule', {}) or {}
                if isinstance(schedule_data, list) and len(schedule_data) > 0:
                    schedule_data = schedule_data[0]
                
                s_id = student_data.get('id')
                s_name = student_data.get('student_name', 'Unknown')
                qr_code = student_data.get('qr_code_data', 'Unknown')
                
                sched_id = schedule_data.get('id')
                session = schedule_data.get('class_name', 'Unknown')
                
                check_in_time = r.get('check_in_time')
                dt_obj = pd.to_datetime(check_in_time) if check_in_time else None
                date_obj = dt_obj.date() if dt_obj else None
                
                data.append({
                    'id': r['id'],
                    'student_id': s_id,
                    'schedule_id': sched_id,
                    'date': date_obj,
                    'session': session,
                    'student_name': s_name,
                    'qr_code': qr_code,
                    'status': r['status'],
                    'type': r.get('type', 'QR'),
                    'timestamp': str(check_in_time) if check_in_time else ''
                })
        
        if not data:
            return pd.DataFrame(columns=['id', 'student_id', 'schedule_id', 'date', 'session', 'student_name', 'qr_code', 'timestamp', 'status', 'type'])
        
        df_res = pd.DataFrame(data)
        # 중복 제거
        df_res = df_res.drop_duplicates(subset=['timestamp', 'student_id', 'schedule_id'])
        return df_res
    except Exception as e:
        logger.error(f"Error fetching attendance: {e}")
        return pd.DataFrame(columns=['id', 'student_id', 'schedule_id', 'date', 'session', 'student_name', 'qr_code', 'timestamp', 'status', 'type'])
# ----------------------------

# ----------------------------

# Auth 모듈 선택적 import
try:
    from auth import authenticate_user, get_students_by_parent
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False
    logger.warning("auth 모듈을 찾을 수 없습니다. 테스트 모드로 실행됩니다.")

# ==========================================
# Config import 추가 (🆕)
# ==========================================
from config import (
    FLASK_PORT,
    ATTENDANCE_BUFFER_BEFORE,
    ATTENDANCE_BUFFER_AFTER,
    ATTENDANCE_STATUS_PRESENT,
    ATTENDANCE_STATUS_LATE,
    ATTENDANCE_STATUS_ABSENT
)

# ==================== CSS 스타일 (화사한 프리미엄 바이올렛 디자인) ====================
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Noto+Sans+KR:wght@400;700;900&display=swap');

        /* 글로벌 배경 및 폰트 */
        .stApp {
            background: linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%);
            color: #2d1a3a;
            font-family: 'Inter', 'Noto Sans KR', sans-serif !important;
        }
        
        [data-testid="stAppViewContainer"] {
            background: transparent !important;
        }

        /* 부모용 헤더 (화사한 화이트 글래스) */
        .parent-header {
            background: rgba(255, 255, 255, 0.2);
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255, 255, 255, 0.4);
            padding: 35px;
            border-radius: 24px;
            text-align: center;
            margin-bottom: 35px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.08);
        }
        
        .parent-header h1 {
            font-size: 34px !important;
            font-weight: 900 !important;
            color: #ffffff !important;
            text-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        /* 자녀 정보 카드 (브라이트 글래스) */
        .child-card {
            background: rgba(255, 255, 255, 0.88);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.6);
            border-radius: 28px;
            padding: 35px;
            box-shadow: 0 20px 45px rgba(0,0,0,0.08);
            margin-bottom: 25px;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            color: #1e293b !important;
        }
        .child-card:hover { 
            transform: translateY(-8px); 
            background: #ffffff;
            box-shadow: 0 25px 55px rgba(0,0,0,0.12);
        }

        /* 상태 배지 */
        .status-badge {
            display: inline-block;
            padding: 8px 20px;
            border-radius: 50px;
            font-weight: 800;
            font-size: 15px;
            margin: 5px;
        }
        .status-present { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
        .status-late { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
        .status-absent { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }

        /* 통계 위젯 */
        .stat-card {
            background: rgba(255, 255, 255, 0.9);
            border-radius: 20px;
            padding: 24px;
            text-align: center;
            border: 1px solid #e2e8f0;
            box-shadow: 0 8px 15px rgba(0,0,0,0.05);
        }
        .stat-number { 
            font-size: 48px; 
            font-weight: 900; 
            background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .stat-label { font-size: 15px; color: #64748b; font-weight: 600; }

        /* 캘린더 스타일 */
        .calendar-day {
            display: inline-block;
            width: 42px;
            height: 42px;
            line-height: 42px;
            text-align: center;
            margin: 3px;
            border-radius: 12px;
            font-weight: 800;
            font-size: 14px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        }
        .day-present { background: #10b981; color: white; }
        .day-late { background: #f59e0b; color: white; }
        .day-absent { background: #ef4444; color: white; }
        .day-future { background: #f1f5f9; color: #cbd5e1; }
        .day-today { border: 3px solid #7c3aed; box-shadow: 0 0 15px rgba(124, 58, 237, 0.3); }

        /* 익스팬더 & 프로그레스 */
        .stExpander {
            background: rgba(255, 255, 255, 0.7) !important;
            border: 1px solid rgba(255, 255, 255, 0.5) !important;
            border-radius: 20px !important;
            color: #1e293b !important;
        }
        .progress-bar {
            height: 35px;
            background: linear-gradient(90deg, #7c3aed 0%, #4f46e5 100%);
            border-radius: 50px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 800;
            font-size: 16px;
            box-shadow: 0 5px 15px rgba(124, 58, 237, 0.2);
        }

        /* 사이드바 스타일링 */
        [data-testid="stSidebar"] {
            background-color: rgba(255, 255, 255, 0.95) !important;
            border-right: 1px solid #e2e8f0;
        }
        [data-testid="stSidebar"] * {
            color: #2d1a3a !important;
        }
        
        /* 스크롤바 커스텀 */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: rgba(0,0,0,0.05); }
        ::-webkit-scrollbar-thumb { background: #7c3aed; border-radius: 10px; }

        /* 모바일 최적화 */
        @media (max-width: 768px) {
            .parent-header h1 { font-size: 26px !important; }
            .calendar-day { width: 34px; height: 34px; line-height: 34px; font-size: 12px; }
            .stat-number { font-size: 36px !important; }
        }
    </style>
, 42, 0.95) !important;
            border-right: 1px solid rgba(255, 255, 255, 0.1);
        }
        [data-testid="stSidebar"] * {
            color: #cbd5e1 !important;
        }
        
        /* 스크롤바 커스텀 */
        ::-webkit-scrollbar { width: 10px; height: 10px; }
        ::-webkit-scrollbar-track { background: rgba(255, 255, 255, 0.05); }
        ::-webkit-scrollbar-thumb { background: rgba(99, 102, 241, 0.3); border-radius: 5px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(99, 102, 241, 0.5); }
    </style>
    """, unsafe_allow_html=True)

ATTENDANCE_CSV = 'attendance.csv'
STUDENTS_CSV = 'students.csv'
CLASS_GROUPS_CSV = 'class_groups.csv'
STUDENT_GROUPS_CSV = 'student_groups.csv'
SCHEDULE_CSV = 'schedule.csv'
PARENTS_CSV = 'parents.csv'
INQUIRIES_CSV = 'inquiries.csv'

# 캐시된 데이터 로딩 함수들
@st.cache_data(ttl=60)
def load_students_cached():
    return get_students_df()

    try:
        if os.path.exists(STUDENTS_CSV):
            df = pd.read_csv(STUDENTS_CSV, encoding='utf-8-sig')
            df = df.fillna('')
            return df
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"학생 데이터 로드 실패: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_class_groups_cached():
    try:
        if os.path.exists(CLASS_GROUPS_CSV):
            df = pd.read_csv(CLASS_GROUPS_CSV, encoding='utf-8-sig')
            df = df.fillna('')
            return df
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"그룹 데이터 로드 실패: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_student_groups_cached():
    try:
        if os.path.exists(STUDENT_GROUPS_CSV):
            df = pd.read_csv(STUDENT_GROUPS_CSV, encoding='utf-8-sig')
            df = df.fillna('')
            return df
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"학생-그룹 매핑 데이터 로드 실패: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_schedule_cached():
    return get_schedule_df()

    try:
        if os.path.exists(SCHEDULE_CSV):
            df = pd.read_csv(SCHEDULE_CSV, encoding='utf-8-sig')
            df = df.fillna('')
            return df
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"일정 데이터 로드 실패: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_attendance_cached():
    return get_attendance_df()

    try:
        if os.path.exists(ATTENDANCE_CSV):
            df = pd.read_csv(ATTENDANCE_CSV, encoding='utf-8-sig')
            df = df.fillna('')
            return df
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"출석 데이터 로드 실패: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_parents_cached():
    try:
        if os.path.exists(PARENTS_CSV):
            df = pd.read_csv(PARENTS_CSV, encoding='utf-8-sig')
            df = df.fillna('')
            return df
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"학부모 데이터 로드 실패: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_inquiries_cached():
    try:
        if os.path.exists(INQUIRIES_CSV):
            df = pd.read_csv(INQUIRIES_CSV, encoding='utf-8-sig')
            df = df.fillna('')
            
            # 컬럼명 표준화: inquiry_text와 content 모두 지원
            if 'inquiry_text' in df.columns and 'content' not in df.columns:
                df = df.rename(columns={'inquiry_text': 'content'})
            
            # parent_name 컬럼이 없으면 추가
            if 'parent_name' not in df.columns:
                df['parent_name'] = df.get('student_name', '')
            
            return df
        return pd.DataFrame(columns=['timestamp', 'student_name', 'parent_name', 'inquiry_type', 'content', 'status', 'response', 'response_time'])
    except Exception as e:
        logger.error(f"문의 데이터 로드 실패: {e}")
        return pd.DataFrame(columns=['timestamp', 'student_name', 'parent_name', 'inquiry_type', 'content', 'status', 'response', 'response_time'])

def get_students_by_parent_direct(parent_name):
    """parents.csv에서 직접 학생 찾기"""
    try:
        df_parents = load_parents_cached()
        
        if df_parents.empty:
            return []
        
        parent_students = df_parents[
            (df_parents['parent_name'].str.strip() == parent_name.strip()) |
            (df_parents['parent_name'].str.lower().str.strip() == parent_name.lower().strip())
        ]
        
        if parent_students.empty:
            return []
        
        student_names = parent_students['student'].str.strip().unique().tolist()
        
        return student_names
    except Exception as e:
        logger.error(f"학부모-학생 매핑 실패: {e}")
        return []

def get_student_all_groups(student_name):
    """학생의 모든 그룹 정보 가져오기"""
    try:
        df_student_groups = load_student_groups_cached()
        df_groups = load_class_groups_cached()
        
        if df_student_groups.empty or df_groups.empty:
            return []
        
        student_groups = df_student_groups[df_student_groups['student_name'].str.strip() == student_name.strip()]
        
        if student_groups.empty:
            return []
        
        group_ids = student_groups['group_id'].unique()
        
        groups = []
        for group_id in group_ids:
            group = df_groups[df_groups['group_id'] == group_id]
            if not group.empty:
                groups.append(group.iloc[0].to_dict())
        
        return groups
    except Exception as e:
        logger.error(f"학생 그룹 정보 조회 실패: {e}")
        return []

def get_child_attendance_data_all_groups(student_name):
    """
    학생의 모든 그룹 출결 현황을 하이브리드(ID+이름) 방식으로 조회 (Student App 동합 로직)
    """
    try:
        # 1. 학생 정보 및 그룹 정보 로드
        df_students_db = get_students_df()
        s_norm = normalize_text(student_name).upper()
        s_row = df_students_db[df_students_db['name'].apply(normalize_text).str.upper() == s_norm]
        
        if s_row.empty:
            return [], pd.DataFrame()
        
        db_student_id = s_row.iloc[0].get('id')
        
        # 학생이 속한 그룹 ID들 (parents.csv 또는 student_groups.csv 기반)
        groups_info = get_student_all_groups(student_name)
        if not groups_info:
            return [], pd.DataFrame()
            
        group_ids = [str(g.get('group_id')) for g in groups_info]
        
        # 2. 수업 일정 로드
        df_schedule_all = get_schedule_df()
        # 해당 그룹들에 속하는 모든 일정 필터링
        all_group_schedules = []
        for g_info in groups_info:
            g_name = normalize_text(g_info['group_name'])
            # 유연한 매칭으로 해당 그룹의 모든 세션 확보
            g_sch = df_schedule_all[df_schedule_all['session'].apply(lambda x: robust_match(g_name, x))].copy()
            all_group_schedules.append(g_sch)
            
        if not all_group_schedules:
            return groups_info, pd.DataFrame()
            
        student_schedule = pd.concat(all_group_schedules, ignore_index=True).drop_duplicates(subset=['id'])
        target_schedule_ids = student_schedule['id'].tolist()
        
        # 3. 출석 데이터 로드 및 하이브리드 필터링
        df_attendance_all = get_attendance_df()
        if df_attendance_all.empty:
            group_attendance = pd.DataFrame()
        else:
            # ID 기반 매칭 + 이름/세션 기반 Fallback 매칭 (관리자/학생 앱 로직과 동일)
            match_id = (df_attendance_all['student_id'] == db_student_id) & \
                        (df_attendance_all['schedule_id'].isin(target_schedule_ids))
            
            match_name = (df_attendance_all['student_name'].apply(normalize_text).str.upper() == s_norm) & \
                         (df_attendance_all['session'].apply(lambda x: any(robust_match(normalize_text(g['group_name']), x) for g in groups_info)))
            
            group_attendance = df_attendance_all[match_id | match_name].copy()
            
        # 4. 시각화 데이터 구성 (일정 기준 루프)
        full_history = []
        today_date = get_today_kst()
        
        if not student_schedule.empty:
            # 최신순 정렬
            student_schedule = student_schedule.sort_values('date', ascending=False)
            
            for _, sch in student_schedule.iterrows():
                sch_id = sch['id']
                sch_date = pd.to_datetime(sch['date']).date()
                
                # 해당 일정에 맞는 출석 기록 찾기
                date_records = group_attendance[
                    (group_attendance['schedule_id'] == sch_id) | 
                    (group_attendance['date'] == sch_date)
                ]
                
                if not date_records.empty:
                    # 기록 발견 시 추가 (중복 방지)
                    for _, r in date_records.drop_duplicates(subset=['timestamp', 'status']).iterrows():
                        full_history.append({
                            'date': str(sch_date),
                            'time': sch['start'],
                            'session': sch['session'],
                            'status': r['status'],
                            'check_time': pd.to_datetime(r['timestamp'], errors='coerce')
                        })
                else:
                    # 기록 미발견 시 상태 결정
                    if sch_date < today_date:
                        status_label = ATTENDANCE_STATUS_ABSENT
                    else:
                        status_label = "수업 예정"
                        
                    full_history.append({
                        'date': str(sch_date),
                        'time': sch['start'],
                        'session': sch['session'],
                        'status': status_label,
                        'check_time': None
                    })
        
        attendance_df = pd.DataFrame(full_history)
        return groups_info, attendance_df
        
    except Exception as e:
        logger.error(f"Error in hybrid child attendance fetching: {e}")
        return [], pd.DataFrame()
        
    
    except Exception as e:
        logger.error(f"출석 데이터 조회 실패: {e}")
        return [], pd.DataFrame()

def save_inquiry(student_name, parent_name, inquiry_type, content):
    """새 문의 저장"""
    try:
        df = load_inquiries_cached()
        
        new_inquiry = {
            'timestamp': get_now_kst().strftime('%Y-%m-%d %H:%M:%S'),
            'student_name': student_name,
            'parent_name': parent_name,
            'inquiry_type': inquiry_type,
            'content': content,
            'status': '접수',
            'response': '',
            'response_time': ''
        }
        
        df = pd.concat([df, pd.DataFrame([new_inquiry])], ignore_index=True)
        df.to_csv(INQUIRIES_CSV, index=False, encoding='utf-8-sig')
        
        st.cache_data.clear()
        
        return True
    except Exception as e:
        logger.error(f"문의 저장 실패: {e}")
        return False

def delete_inquiry(timestamp, student_name):
    """개별 문의 삭제 - student_name 기준"""
    try:
        df = load_inquiries_cached()
        if df.empty:
            return False
        
        # timestamp가 일치하고, student_name이 일치하는 행 삭제
        df = df[
            ~(
                (df['timestamp'] == timestamp) & 
                (df['student_name'].str.strip() == student_name.strip())
            )
        ]
        
        df.to_csv(INQUIRIES_CSV, index=False, encoding='utf-8-sig')
        st.cache_data.clear()
        
        return True
    except Exception as e:
        logger.error(f"문의 삭제 실패: {e}")
        return False

def get_my_inquiries(student_name):
    """내 문의 내역 가져오기 - student_name 기준"""
    try:
        df_inquiries = load_inquiries_cached()
        if df_inquiries.empty:
            return []
        
        # 컬럼명 표준화 확인
        if 'inquiry_text' in df_inquiries.columns and 'content' not in df_inquiries.columns:
            df_inquiries = df_inquiries.rename(columns={'inquiry_text': 'content'})
        
        # student_name이 일치하는 모든 문의 찾기 (자녀 기준)
        my_inquiries = df_inquiries[
            df_inquiries['student_name'].str.strip() == student_name.strip()
        ]
        
        return my_inquiries.to_dict('records')
    except Exception as e:
        logger.error(f"문의 조회 실패: {e}")
        return []

def show_monthly_calendar(attendance_df, year, month):
    """월별 캘린더 표시"""
    st.markdown(f"## 📅 {year}년 {month}월 출석 현황")
    
    # 해당 월의 출석 기록 추출
    month_records = {}
    for _, record in attendance_df.iterrows():
        try:
            record_date = pd.to_datetime(record['date']).date()
            if record_date.year == year and record_date.month == month:
                month_records[record_date.day] = record['status']
        except:
            continue
    
    # 달력 생성
    cal = calendar.monthcalendar(year, month)
    
    # 요일 헤더
    st.markdown("""
    <div style="display: flex; justify-content: space-around; margin-bottom: 10px;">
        <div style="width: 40px; text-align: center; font-weight: bold;">월</div>
        <div style="width: 40px; text-align: center; font-weight: bold;">화</div>
        <div style="width: 40px; text-align: center; font-weight: bold;">수</div>
        <div style="width: 40px; text-align: center; font-weight: bold;">목</div>
        <div style="width: 40px; text-align: center; font-weight: bold;">금</div>
        <div style="width: 40px; text-align: center; font-weight: bold;">토</div>
        <div style="width: 40px; text-align: center; font-weight: bold;">일</div>
    </div>
    """, unsafe_allow_html=True)
    
    today = get_today_kst()
    
    # 각 주별 표시
    for week in cal:
        week_html = '<div style="display: flex; justify-content: space-around; margin-bottom: 5px;">'
        
        for day in week:
            if day == 0:
                week_html += '<div class="calendar-day"></div>'
            else:
                day_class = "calendar-day"
                day_date = date(year, month, day)
                
                if day_date == today:
                    day_class += " day-today"
                
                if day in month_records:
                    status = month_records[day]
                    if status == ATTENDANCE_STATUS_PRESENT:
                        day_class += " day-present"
                    elif status == ATTENDANCE_STATUS_LATE:
                        day_class += " day-late"
                    elif status == ATTENDANCE_STATUS_ABSENT: 
                        day_class += " day-absent"
                elif day_date > today:
                    day_class += " day-future"
                
                week_html += f'<div class="{day_class}">{day}</div>'
        
        week_html += '</div>'
        st.markdown(week_html, unsafe_allow_html=True)
    
    # 범례
    st.markdown("""
    <div style="display: flex; justify-content: center; gap: 20px; margin-top: 20px;">
        <div><span class="calendar-day day-present">1</span> 출석</div>
        <div><span class="calendar-day day-late">2</span> 지각</div>
        <div><span class="calendar-day day-absent">3</span> 결석</div>
        <div><span class="calendar-day day-future">4</span> 예정</div>
    </div>
    """, unsafe_allow_html=True)

def main():
    # 🆕 세션 초기화 (포털 통합 대응)
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None

    # 1. 페이지 설정 (중복 호출 방지)
    try:
        st.set_page_config(
            page_title="학부모 앱 - 온라인아카데미",
            page_icon="👨‍👩‍👧",
            layout="wide",
            initial_sidebar_state="collapsed"
        )
    except:
        pass

    # 2. ⭐ 반응형 CSS (매 세션 적용)
    st.markdown("""
    <style>
        .main { background: #f8f9fa; margin: 0 auto; }
        .parent-header { background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%); color: white; padding: 30px; border-radius: 15px; text-align: center; margin-bottom: 30px; }
        .child-card { background: white; border-radius: 15px; padding: 25px; margin: 15px 0; box-shadow: 0 2px 10px rgba(0,0,0,0.1); border-left: 5px solid #4CAF50; }
        .status-badge { display: inline-block; padding: 10px 20px; border-radius: 25px; font-weight: bold; font-size: 18px; margin: 10px 5px; }
        .status-present { background: #d4edda; color: #155724; border: 2px solid #28a745; }
        .status-late { background: #fff3cd; color: #856404; border: 2px solid #ffc107; }
        .status-absent { background: #f8d7da; color: #721c24; border: 2px solid #dc3545; }
        .stat-card { background: white; border-radius: 12px; padding: 25px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin: 10px 0; }
        .stat-number { font-size: 48px; font-weight: bold; margin: 15px 0; }
        .stat-green { color: #4CAF50; }
        .stat-orange { color: #FF9800; }
        .stat-red { color: #f44336; }
        .calendar-day { aspect-ratio: 1; display: flex; align-items: center; justify-content: center; border-radius: 50%; font-weight: bold; font-size: 14px; background: #f8f9fa; }
        .day-present { background: #d4edda; color: #155724; }
        .day-late { background: #fff3cd; color: #856404; }
        .day-absent { background: #f8d7da; color: #721c24; }
        .day-today { border: 2px solid #4CAF50; }
        @media (max-width: 768px) {
            .stat-number { font-size: 32px; }
            .parent-header h1 { font-size: 24px !important; }
            .child-card { padding: 15px !important; }
        }
    </style>
    """, unsafe_allow_html=True)

    # 3. 로그인 체크
    if not st.session_state.authenticated or st.session_state.user is None:
        st.error("🔒 로그인이 필요합니다.")

        st.info("""
        학부모 앱을 사용하려면 먼저 로그인해주세요.
        
        **테스트 계정:**
        - 아이디: `parent1`
        - 비밀번호: `parent123`
        """)
        
        with st.form("quick_login"):
            st.markdown("### 👨‍👩‍👧 학부모 로그인")
            username = st.text_input("아이디", key="parent_auto_799")
            password = st.text_input("비밀번호", type="password", key="parent_auto_800")
            
            if st.form_submit_button("로그인", use_container_width=True, key="parent_auto_802"):
                if AUTH_AVAILABLE:
                    user = authenticate_user(username, password)
                    
                    if user:
                        st.session_state.user = user
                        st.session_state.authenticated = True
                        st.success("로그인 성공!")
                        st.rerun()
                    else:
                        st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
                else:
                    if username == "parent1" and password == "parent123":
                        st.session_state.user = {'name': 'parent1', 'role': 'parent', 'username': 'parent1'}
                        st.session_state.authenticated = True
                        st.success("로그인 성공!")
                        st.rerun()
                    else:
                        st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
        st.stop()
    
    user = st.session_state.get('user')
    
    # 세션 복구 및 안전장치
    if user is None:
        st.warning("⚠️ 세션이 만료되었습니다. 다시 로그인해 주세요.")
        st.session_state.authenticated = False
        st.rerun()
        st.stop()
    
    # 역할 확인
    if user.get('role') != 'parent':
        st.error("⚠️ 학부모만 접근 가능한 페이지입니다.")
        st.info(f"현재 로그인: {user.get('name', '알 수 없음')} ({user.get('role', '권한 없음')})")
        
        if st.button("🚪 로그아웃", use_container_width=True, key="logout_role_check"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()
        st.stop()
    
    # 헤더
    st.markdown(f"""
    <div class="parent-header">
        <h1>👨‍👩‍👧 {user['name']}님, 안녕하세요!</h1>
        <p style="font-size: 18px; margin-top: 10px;">자녀의 출석 현황을 확인하세요</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 자녀 목록 가져오기 (5단계 fallback)
    with st.spinner("데이터 로딩 중..."):
        children = []
        
        # 1단계: auth 모듈 사용
        if AUTH_AVAILABLE:
            try:
                children = get_students_by_parent(user['name'])
            except:
                pass
        
        # 2단계: parents.csv에서 name으로 찾기
        if not children:
            children = get_students_by_parent_direct(user['name'])
        
        # 3단계: parents.csv에서 username으로 찾기
        if not children and user.get('username'):
            children = get_students_by_parent_direct(user['username'])
        
        # 4단계: users.csv의 student_id 사용
        if not children and user.get('student_id'):
            children = [user['student_id']]
        
        # 5단계: 기본값 (테스트용)
        if not children:
            children = ['성소영']
    
    if not children:
        st.warning("⚠️ 등록된 자녀를 찾을 수 없습니다.")
        
        with st.expander("🔍 디버깅 정보"):
            st.write("**사용자 정보:**")
            st.json(user)
            
            st.write("**parents.csv:**")
            df_parents = load_parents_cached()
            if not df_parents.empty:
                st.dataframe(df_parents)
            else:
                st.error("parents.csv가 비어있음")
        
        st.stop()
    
    # 자녀 선택
    if len(children) > 1:
        selected_child = st.selectbox("자녀 선택", children, key="child_selector")
    else:
        selected_child = children[0]
        st.info(f"👦 {selected_child}")
    
    st.markdown("---")
    
    # 출석 데이터 가져오기
    with st.spinner("출석 데이터 로딩 중..."):
        groups_info, attendance_df = get_child_attendance_data_all_groups(selected_child)
    
    if not groups_info and attendance_df.empty:
        st.error("❌ 자녀 정보를 찾을 수 없습니다.")
        
        with st.expander("🔍 상세 정보"):
            st.write(f"**선택된 자녀:** {selected_child}")
            
            df_students = load_students_cached()
            if not df_students.empty:
                student_match = df_students[df_students['name'].str.strip() == selected_child.strip()]
                if not student_match.empty:
                    st.success(f"✅ 학생 발견")
                    st.dataframe(student_match)
                else:
                    st.error(f"❌ students.csv에서 '{selected_child}' 없음")
                    st.dataframe(df_students[['name']])
            
            df_student_groups = load_student_groups_cached()
            if not df_student_groups.empty:
                group_match = df_student_groups[df_student_groups['student_name'].str.strip() == selected_child.strip()]
                if not group_match.empty:
                    st.success(f"✅ 그룹 배정 발견")
                    st.dataframe(group_match)
                else:
                    st.error(f"❌ student_groups.csv에서 '{selected_child}' 없음")
        
        return
    
    # 자녀 이름 표시
    st.markdown(f"### 👦 {selected_child}")
    
    # 그룹 정보 표시
    if groups_info:
        st.markdown(f"### 🎓 수강 중인 그룹 ({len(groups_info)}개)")
        
        group_badges = ""
        for group in groups_info:
            group_badges += f'<span class="group-badge">{group["group_name"]}</span>'
        
        st.markdown(f'<div style="margin-bottom: 1rem;">{group_badges}</div>', unsafe_allow_html=True)
        
        total_hours = sum([float(g.get('total_hours', 0) or 0) for g in groups_info])
        st.markdown(f"📚 **총 교육시간:** {total_hours}시간")
    
    st.markdown("---")
    
    # 출석 통계
    if not attendance_df.empty:
        # 실제 수업이 진행된 데이터만 통계에 반영 (수업 예정 제외)
        total_sessions = len(attendance_df[attendance_df['status'] != "수업 예정"])
        
        present = len(attendance_df[attendance_df['status'].isin([ATTENDANCE_STATUS_PRESENT, "출석"])])
        late = len(attendance_df[attendance_df['status'].isin([ATTENDANCE_STATUS_LATE, "지각"])])
        absent = len(attendance_df[attendance_df['status'].isin([ATTENDANCE_STATUS_ABSENT, "결석"])])
        
        # 출석 인정 수 (출석 + 지각)
        verified_attendance = present + late
        attendance_rate = (verified_attendance / total_sessions * 100) if total_sessions > 0 else 0
        
        st.markdown("### 📊 출석 통계")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.markdown(f"""
            <div class="stat-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                <div class="stat-label" style="color: white;">진행 수업</div>
                <div class="stat-number" style="color: white;">{total_sessions}</div>
                <div style="color: white;">/ {len(attendance_df)} 회</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="stat-card" style="background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);">
                <div class="stat-label" style="color: white;">출석</div>
                <div class="stat-number" style="color: white;">{present}</div>
                <div style="color: white;">회</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="stat-card" style="background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);">
                <div class="stat-label" style="color: white;">지각</div>
                <div class="stat-number" style="color: white;">{late}</div>
                <div style="color: white;">회</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="stat-card" style="background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);">
                <div class="stat-label" style="color: white;">결석</div>
                <div class="stat-number" style="color: white;">{absent}</div>
                <div style="color: white;">회</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col5:
            st.markdown(f"""
            <div class="stat-card" style="background: linear-gradient(135deg, #a1c4fd 0%, #c2e9fb 100%);">
                <div class="stat-label" style="color: white;">출석률</div>
                <div class="stat-number" style="color: white;">{attendance_rate:.1f}</div>
                <div style="color: white;">%</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("📊 아직 출석 기록이 없습니다.")
    
    st.markdown("---")
    
    # 탭 상태 초기화
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = 0
    
    # 탭 메뉴
    tab_names = ["📅 월별 캘린더", "📋 출석 기록", "🎓 수업 정보", "📞 문의하기"]
    
    # 탭 선택 (라디오 버튼으로 변경하여 상태 유지)
    st.session_state.active_tab = st.radio(
        "메뉴",
        range(len(tab_names)),
        format_func=lambda x: tab_names[x],
        horizontal=True,
        key="tab_selector",
        index=st.session_state.active_tab
    )
    
    st.markdown("---")
    
    active_tab = st.session_state.active_tab
    
    # 탭 1: 월별 캘린더
    if active_tab == 0:
        if not attendance_df.empty:
            attendance_df['date'] = pd.to_datetime(attendance_df['date'], errors='coerce')
            attendance_df_clean = attendance_df.dropna(subset=['date'])
            
            if not attendance_df_clean.empty:
                years = sorted(attendance_df_clean['date'].dt.year.unique(), reverse=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    selected_year = st.selectbox("연도", years, index=0, key="year_select")
                
                months_in_year = sorted(attendance_df_clean[attendance_df_clean['date'].dt.year == selected_year]['date'].dt.month.unique())
                
                with col2:
                    if months_in_year:
                        current_month = get_today_kst().month
                        default_index = months_in_year.index(current_month) if current_month in months_in_year else 0
                        selected_month = st.selectbox("월", months_in_year, index=default_index, key="month_select")
                    else:
                        selected_month = get_today_kst().month
                        st.info("선택된 연도에 출석 기록이 없습니다.")
                
                show_monthly_calendar(attendance_df_clean, selected_year, selected_month)
            else:
                st.info("📅 출석 기록이 없습니다.")
        else:
            st.info("📅 아직 출석 기록이 없습니다.")
    
    # 탭 2: 출석 기록
    elif active_tab == 1:
        st.markdown("### 📋 최근 출석 기록")
        
        if not attendance_df.empty:
            attendance_df_sorted = attendance_df.sort_values('date', ascending=False)
            
            for _, row in attendance_df_sorted.iterrows():
                status = row['status']
                is_zoom = "Zoom" in str(status) or "줌" in str(status)
                
                # 라벨 정규화
                status_clean = str(status).replace(" (미출석)", "").replace(" (줌)", "").strip()
                
                if status_clean in [ATTENDANCE_STATUS_PRESENT, "출석"]:
                    status_html = f'<span class="status-present">✅ 출석 {"(줌)" if is_zoom else ""}</span>'
                    emoji = '✅'
                elif status_clean in [ATTENDANCE_STATUS_LATE, "지각"]:
                    # 줌 수업은 지각도 출석으로 간주 (학생 앱과 동일)
                    if is_zoom:
                        status_html = '<span class="status-present">✅ 출석 (줌)</span>'
                        emoji = '✅'
                    else:
                        status_html = '<span class="status-late">⏰ 지각</span>'
                        emoji = '⏰'
                elif "수업 예정" in status_clean:
                    status_html = '<span style="color: #666;">⏳ 수업 예정</span>'
                    emoji = '⏳'
                else:
                    status_html = '<span class="status-absent">❌ 결석</span>'
                    emoji = '❌'
                
                with st.expander(f"{emoji} {row['date']} {row['time']} - {row['session']}", expanded=False):
                    st.markdown(f"**수업:** {row['session']}")
                    st.markdown(f"**날짜:** {row['date']}")
                    st.markdown(f"**시간:** {row['time']}")
                    st.markdown(f"**상태:** {status_html}", unsafe_allow_html=True)
                    
                    if row['check_time'] and pd.notna(row['check_time']):
                        # KST 변환된 시간 표시
                        c_time = pd.to_datetime(row['check_time'])
                        st.markdown(f"**체크 시간:** {c_time.strftime('%H:%M:%S')}")
        else:
            st.info("📋 아직 출석 기록이 없습니다.")
        
        if not attendance_df.empty:
            st.markdown("---")
            
            info_text = f"자녀: {selected_child}\n진행 수업: {total_sessions}회\n출석: {present}회\n지각: {late}회\n결석: {absent}회\n출석률: {attendance_rate:.1f}%"
            
            st.download_button(
                "📥 출석 기록 다운로드",
                info_text,
                file_name=f"{selected_child}_출석기록_{get_now_kst().strftime('%Y%m%d')}.txt",
                mime="text/plain",
                use_container_width=True
            , key="parent_auto_1113")
    
    # 탭 3: 수업 정보
    elif active_tab == 2:
        st.markdown("### 🎓 수업 정보")
        
        if groups_info:
            for i, group in enumerate(groups_info, 1):
                with st.expander(f"📚 {i}. {group['group_name']}", expanded=(i==1)):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        weekdays = group.get('weekdays', 'N/A')
                        if weekdays != 'N/A':
                            try:
                                weekdays_list = [['월', '화', '수', '목', '금', '토', '일'][int(d)] for d in str(weekdays).split(',')]
                                weekdays_str = ', '.join(weekdays_list)
                            except:
                                weekdays_str = str(weekdays)
                        else:
                            weekdays_str = 'N/A'
                        
                        st.markdown(f"**📅 수업 요일:** {weekdays_str}")
                        st.markdown(f"**⏰ 수업 시간:** {group.get('start_time', 'N/A')} ~ {group.get('end_time', 'N/A')}")
                    
                    with col2:
                        st.markdown(f"**📆 수업 기간:** {group.get('start_date', 'N/A')} ~ {group.get('end_date', 'N/A')}")
                        st.markdown(f"**🕐 총 교육시간:** {group.get('total_hours', 'N/A')}시간")
        else:
            st.info("🎓 수강 중인 그룹이 없습니다.")
    
   # 탭 4: 문의하기
    elif active_tab == 3:
        st.markdown("### 📞 로보그램 연락처") 
        st.markdown("""
        **전화:** 1833-4086  
        **이메일:** kr.support@robogram.org  
        **카카오톡:** http://pf.kakao.com/_vxivLn
        """)
        
        st.markdown("---")
        
        col_refresh, col_space = st.columns([1, 3])
        with col_refresh:
            if st.button("🔄 새로고침", use_container_width=True, key="refresh_inquiry"):
                st.cache_data.clear()
                st.rerun()
        
        st.markdown("### 💬 자주 묻는 질문")
        
        with st.expander("❓ Q: 출석 체크는 언제까지 가능한가요?"):
            st.markdown("""
            **A:** 수업 시작 **30분 전**부터 수업 종료 **15분 후**까지 가능합니다.
            
            **세부 일정:**
            - ✅ 수업 시작 30분 전: 출석 체크 시작
            - ✅ 수업 시작 ~ 10분 후: **출석** 인정
            - ⏰ 수업 시작 10분 후: **지각** 처리
            """)
        
        with st.expander("❓ Q: 결석이나 지각 사유는 어떻게 알리나요?"):
            st.markdown("""
            **A:** 아래 방법으로 연락주세요:
            
            - 📞 전화: 1833-4086
            - 💬 카카오톡: http://pf.kakao.com/_vxivLn
            - 📧 이메일: kr.support@robogram.org
            """)
        
        with st.expander("❓ Q: 수료증은 언제 발급되나요?"):
            st.markdown("""
            **A:** 전체 수업의 **100% 출석** 시 수료증이 발급됩니다.
            
            **발급 방법:**
            - 학생 앱 → 수료증 탭에서 자동 발급
            - 사진 업로드 후 다운로드 가능
            """)
        
        with st.expander("❓ Q: 결과물은 무엇이고 어디로 제출하나요?"):
            st.markdown("""
            **A:** 특강 수업 종료 후 정해진 기간 내에 제출하시면 됩니다.
            
            **제출 기간:** 수업 종료 후 일주일 이내
            
            **제출 내용:**
            1. 게임 제작물 (JemS 또는 로블록스)
            2. 작품 설명 PPT
            
            **제출 방법:** 카카오톡으로 공지되는 사이트에 업로드
            """)
        
        with st.expander("❓ Q: 수업 종료 후 추가 수업을 들을 수 있나요?"):
            st.markdown("""
            **A:** 네! 로보그램은 다양한 심화 과정을 운영하고 있습니다.
            
            **1. 오프라인 특강:** 판교 오프라인 특강
            **2. 온라인 실시간 강의:** 방학 특강 프로그램
            **3. AI 맞춤형 강의:** 곧 출시 예정
            
            **문의:** 1833-4086
            """)
        
        st.markdown("---")
        
        st.markdown("### 📋 내 문의 내역")
        my_inquiries = get_my_inquiries(selected_child)
        
        # 디버깅 정보
        with st.expander("🔍 문의 조회 디버깅", expanded=False):
            st.write(f"**조회 기준:** student_name = '{selected_child}'")
            st.write(f"**조회된 문의 수:** {len(my_inquiries)}건")
            
            # 현재 로그인한 학부모 정보
            st.write(f"**로그인 계정:** {user.get('username', 'N/A')}")
            st.write(f"**로그인 이름:** {user.get('name', 'N/A')}")
            
            # parents.csv에서 실제 학부모 이름 확인
            correct_parent_name = None
            df_parents = load_parents_cached()
            if not df_parents.empty:
                parent_record = df_parents[df_parents['student'] == selected_child]
                if not parent_record.empty:
                    correct_parent_name = parent_record.iloc[0]['parent_name']
                    st.write(f"**parents.csv 학부모:** {correct_parent_name}")
            
            if os.path.exists(INQUIRIES_CSV):
                df_all = pd.read_csv(INQUIRIES_CSV, encoding='utf-8-sig')
                st.write(f"**전체 문의 수:** {len(df_all)}건")
                st.write(f"**CSV 컬럼:** {list(df_all.columns)}")
                
                if not df_all.empty:
                    st.write("**전체 문의 목록:**")
                    display_cols = ['timestamp', 'student_name', 'parent_name', 'inquiry_type', 'status']
                    st.dataframe(df_all[display_cols] if all(col in df_all.columns for col in display_cols) else df_all)
                    
                    # student_name으로 필터링된 결과
                    filtered = df_all[df_all['student_name'] == selected_child]
                    st.write(f"**student_name='{selected_child}' 문의:** {len(filtered)}건")
                    
                    # parent_name 오류 확인
                    if 'parent_name' in df_all.columns and correct_parent_name:
                        wrong_parent = filtered[
                            (filtered['parent_name'] != correct_parent_name) &
                            (filtered['parent_name'].notna()) &
                            (filtered['parent_name'] != '')
                        ]
                        if not wrong_parent.empty:
                            st.warning(f"⚠️ 잘못된 parent_name이 있는 문의: {len(wrong_parent)}건")
                            
                            # 수정 버튼
                            if st.button("🔧 parent_name 일괄 수정", key="fix_parent_names"):
                                try:
                                    df_all.loc[df_all['student_name'] == selected_child, 'parent_name'] = correct_parent_name
                                    df_all.to_csv(INQUIRIES_CSV, index=False, encoding='utf-8-sig')
                                    st.cache_data.clear()
                                    st.success(f"✅ {selected_child}의 parent_name을 '{correct_parent_name}'으로 수정했습니다!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ 수정 실패: {e}")
            else:
                st.error("❌ inquiries.csv 파일이 없습니다!")
        
        if my_inquiries:
            total_count = len(my_inquiries)
            status_counts = {}
            for inq in my_inquiries:
                status = inq['status']
                status_counts[status] = status_counts.get(status, 0) + 1
            
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                st.metric("전체", f"{total_count}건")
            with col_stat2:
                st.metric("접수/처리중", f"{status_counts.get('접수', 0) + status_counts.get('처리중', 0)}건")
            with col_stat3:
                st.metric("완료", f"{status_counts.get('완료', 0)}건")
            
            st.markdown("###")
            
            filter_option = st.radio(
                "표시 옵션",
                ["전체 보기", "접수/처리중만", "완료만"],
                horizontal=True
            , key="parent_auto_1298")
            
            filtered_inquiries = my_inquiries.copy()
            if filter_option == "접수/처리중만":
                filtered_inquiries = [inq for inq in my_inquiries if inq['status'] in ['접수', '처리중']]
            elif filter_option == "완료만":
                filtered_inquiries = [inq for inq in my_inquiries if inq['status'] == '완료']
            
            for idx, inquiry in enumerate(reversed(filtered_inquiries[-10:])):
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
                
                # 변경 후
                expander_title = f"{status_emoji} [{inquiry['inquiry_type']}] {inquiry['timestamp'][:16]}"
                
                # 삭제 확인 중이면 expander를 열린 상태로 유지
                delete_key = f"delete_confirm_{inquiry['timestamp']}"
                is_deleting = st.session_state.get(delete_key, False)
                
                with st.expander(expander_title, expanded=is_deleting):
                    st.markdown(f"""
                    <div style="display: inline-block; background: {status_color}; 
                                color: white; padding: 5px 15px; border-radius: 20px; 
                                font-size: 13px; margin-bottom: 15px;">
                        {inquiry['status']}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    **문의 시간:** {inquiry['timestamp']}  
                    **문의 유형:** {inquiry['inquiry_type']}
                    
                    ---
                    
                    **문의 내용:**
                    
                    {inquiry['content']}
                    """)
                    
                    has_reply = (
                        inquiry.get('response') is not None and 
                        not pd.isna(inquiry.get('response')) and 
                        str(inquiry['response']).strip() != ''
                    )
                    
                    if has_reply:
                        reply_time = inquiry.get('response_time', '시간 미상')
                        if pd.isna(reply_time) or reply_time == '':
                            reply_time = '시간 미상'
                        
                        st.markdown(f"""
                        <div style="background: #f0f7ff; padding: 15px; border-radius: 10px; 
                                    border-left: 4px solid #2196F3; margin-top: 15px;">
                            <div style="color: #1976D2; font-weight: bold; margin-bottom: 10px;">
                                💬 관리자 답변
                            </div>
                            <div style="color: #666; font-size: 13px; margin-bottom: 10px;">
                                📅 {reply_time}
                            </div>
                            <div style="color: #333; line-height: 1.6; white-space: pre-wrap;">
                                {str(inquiry['response'])}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.info("⏳ 답변 대기 중입니다.")
                    
                    st.markdown("---")
                    
                    # 삭제 버튼 (간단하게)
                    col_del1, col_del2, col_del3 = st.columns([2, 1, 2])
                    
                    with col_del2:
                        # 삭제 확인 상태를 session_state에 저장 (timestamp만 사용)
                        delete_key = f"delete_confirm_{inquiry['timestamp']}"
                        
                        if delete_key not in st.session_state:
                            st.session_state[delete_key] = False
                        
                        if not st.session_state[delete_key]:
                            # 첫 번째 클릭: 확인 요청
                            if st.button(
                                "🗑️ 삭제", 
                                key=f"delete_btn_{inquiry['timestamp']}",
                                use_container_width=True,
                                type="secondary"
                            ):
                                st.session_state[delete_key] = True
                                st.rerun()
                        else:
                            # 두 번째 단계: 확인 또는 취소
                            st.warning("⚠️ 정말 삭제하시겠습니까?")
                            
                            col_confirm, col_cancel = st.columns(2)
                            
                            with col_confirm:
                                if st.button(
                                    "✅ 확인",
                                    key=f"confirm_{inquiry['timestamp']}",
                                    use_container_width=True,
                                    type="primary"
                                ):
                                    if delete_inquiry(inquiry['timestamp'], selected_child):
                                        # 삭제 성공 시 해당 키 제거
                                        if delete_key in st.session_state:
                                            del st.session_state[delete_key]
                                        st.success("✅ 삭제되었습니다.")
                                        st.rerun()
                                    else:
                                        st.error("❌ 삭제 실패")
                            
                            with col_cancel:
                                if st.button(
                                    "❌ 취소",
                                    key=f"cancel_{inquiry['timestamp']}",
                                    use_container_width=True
                                ):
                                    st.session_state[delete_key] = False
                                    st.rerun()
            
            if total_count > 10:
                st.info(f"💡 최근 10개의 문의만 표시됩니다. (전체: {total_count}건)")
            
            completed_inquiries = [inq for inq in my_inquiries if inq['status'] == '완료']
            if len(completed_inquiries) >= 3:
                st.markdown("---")
                with st.expander("⚡ 완료된 문의 일괄 삭제"):
                    st.info(f"완료된 문의 {len(completed_inquiries)}건을 한번에 삭제할 수 있습니다.")
                    
                    bulk_delete_confirm = st.checkbox(
                        f"완료된 문의 {len(completed_inquiries)}건을 모두 삭제하시겠습니까?",
                        key="bulk_delete_confirm"
                    )
                    
                    if bulk_delete_confirm:
                        st.warning("⚠️ 삭제된 문의는 복구할 수 없습니다!")
                        
                        if st.button("🗑️ 일괄 삭제 확정", use_container_width=True, type="secondary", key="parent_auto_1448"):
                            deleted_count = 0
                            for inq in completed_inquiries:
                                if delete_inquiry(inq['timestamp'], selected_child):
                                    deleted_count += 1
                            
                            if deleted_count > 0:
                                st.success(f"✅ {deleted_count}건의 문의가 삭제되었습니다.")
                                st.rerun()
                            else:
                                st.error("❌ 삭제 중 오류가 발생했습니다.")
        
        else:
            st.info("아직 문의 내역이 없습니다.")
        
        st.markdown("---")
        
        if st.session_state.get('inquiry_sent', False):
            st.markdown("""
            <div class="success-message">
                <h3 style="margin: 0 0 10px 0; font-size: 20px;">✅ 문의가 접수되었습니다!</h3>
                <p style="margin: 0; opacity: 0.95; font-size: 15px;">
                    빠른 시일 내에 답변드리겠습니다.<br>
                    아래에서 문의 내역을 확인하실 수 있습니다.
                </p>
            </div>
            """, unsafe_allow_html=True)
            st.balloons()
            st.session_state['inquiry_sent'] = False
        
        st.markdown("### ✉️ 새 문의하기")
        
        if 'form_reset_counter' not in st.session_state:
            st.session_state['form_reset_counter'] = 0
        
        form_key = f"inquiry_form_{st.session_state['form_reset_counter']}"
        
        with st.form(form_key):
            inquiry_type = st.selectbox(
                "문의 유형",
                ["일반 문의", "결석 사유", "상담 요청", "그룹 변경 요청", "기타"],
                help="문의 유형을 선택해주세요"
            , key="parent_auto_1486")
            
            inquiry_text = st.text_area(
                "문의 내용", 
                height=150,
                placeholder="문의하실 내용을 자세히 작성해주세요...\n\n예시:\n- 결석 사유: 내일 병원 진료로 결석합니다.\n- 상담 요청: 자녀의 학습 진도에 대해 상담하고 싶습니다.",
                help="구체적으로 작성하실수록 빠른 답변이 가능합니다"
            , key="parent_auto_1492")
            
            submitted = st.form_submit_button("📨 문의 전송", use_container_width=True, type="primary", key="parent_auto_1499")
            
            st.caption("💡 문의 전송 후 입력 내용이 자동으로 초기화됩니다.")
            
            if submitted:
                if inquiry_text and len(inquiry_text.strip()) >= 10:
                    # 학부모의 실제 이름 가져오기
                    parent_real_name = user.get('name', 'parent1')
                    
                    # parents.csv에서 실제 이름 확인
                    df_parents = load_parents_cached()
                    if not df_parents.empty:
                        parent_record = df_parents[df_parents['student'] == selected_child]
                        if not parent_record.empty:
                            parent_real_name = parent_record.iloc[0]['parent_name']
                    
                    if save_inquiry(selected_child, parent_real_name, inquiry_type, inquiry_text.strip()):
                        st.session_state['form_reset_counter'] += 1
                        st.session_state['inquiry_sent'] = True
                        
                        # 디버깅: 저장 확인
                        with st.expander("🔍 저장 확인 (디버깅)", expanded=False):
                            st.success(f"✅ 문의가 저장되었습니다!")
                            st.write(f"- 자녀: {selected_child}")
                            st.write(f"- 학부모: {parent_real_name}")
                            st.write(f"- 유형: {inquiry_type}")
                            st.write(f"- 내용 길이: {len(inquiry_text.strip())}자")
                            
                            # inquiries.csv 확인
                            if os.path.exists(INQUIRIES_CSV):
                                st.write(f"- inquiries.csv 존재: ✅")
                                df_check = pd.read_csv(INQUIRIES_CSV, encoding='utf-8-sig')
                                st.write(f"- 전체 문의 수: {len(df_check)}건")
                                st.write(f"- 최근 저장된 문의:")
                                if not df_check.empty:
                                    last_inquiry = df_check.iloc[-1]
                                    st.json(last_inquiry.to_dict())
                            else:
                                st.error("❌ inquiries.csv 파일이 없습니다!")
                        
                        st.rerun()
                    else:
                        st.error("❌ 문의 저장 중 오류가 발생했습니다.")
                elif inquiry_text:
                    st.error("❌ 문의 내용을 10자 이상 입력해주세요.")
                else:
                    st.error("❌ 문의 내용을 입력해주세요.")
    
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("🔄 새로고침", use_container_width=True, key="refresh_main"):
            st.cache_data.clear()
            st.rerun()
    
    with col2:
        if groups_info and not attendance_df.empty:
            info_text = f"자녀: {selected_child}\n진행 수업: {total_sessions}회\n출석: {present}회\n지각: {late}회\n결석: {absent}회\n출석률: {attendance_rate:.1f}%"
            st.download_button(
                "📥 수업 정보",
                info_text,
                file_name=f"{selected_child}_수업정보_{get_now_kst().strftime('%Y%m%d')}.txt",
                mime="text/plain",
                use_container_width=True
            , key="parent_auto_1558")
    
    with col3:
        if st.button("🚪 로그아웃", use_container_width=True, key="logout_main"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()
    
    st.markdown("<br><br>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()

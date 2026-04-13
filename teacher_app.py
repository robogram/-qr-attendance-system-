"""
선생님 앱 - 완전 업데이트 버전
수업 그룹 연동 + 정확한 출석체크 + 교육시간 표시
모바일/PC 완전 최적화 + 호환성 완벽
✨ 출석수정 + 메모 + 알림 + 통계 그래프
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, time
import requests
import streamlit.components.v1 as components
from utils import load_csv_safe
from config import (
    STUDENTS_CSV, 
    ATTENDANCE_LOG_CSV, 
    SCHEDULE_CSV, 
    FLASK_PORT, 
    TEACHER_GROUPS_CSV,
    # 🆕 아래 추가
    ATTENDANCE_BUFFER_BEFORE,
    ATTENDANCE_BUFFER_AFTER,
    ATTENDANCE_STATUS_PRESENT,
    ATTENDANCE_STATUS_LATE,
    ATTENDANCE_STATUS_ABSENT,
    AUTO_ABSENCE_MINUTES,
    LATE_THRESHOLD_MINUTES
)


import os
import plotly.express as px
import plotly.graph_objects as go

# 수업 그룹 관련 파일
CLASS_GROUPS_CSV = "class_groups.csv"
STUDENT_GROUPS_CSV = "student_groups.csv"
ATTENDANCE_NOTES_CSV = "attendance_notes.csv"  # 🆕 메모 저장

# 페이지 설정
st.set_page_config(
    page_title="선생님 앱 - 온라인아카데미",
    page_icon="👩‍🏫",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 세션 초기화
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'flask_connected' not in st.session_state:
    st.session_state.flask_connected = False

# 로그인 체크
if not st.session_state.authenticated or st.session_state.user is None:
    st.error("🔒 로그인이 필요합니다.")
    st.info("""
    선생님 앱을 사용하려면 먼저 로그인해주세요.
    
    **선생님 계정:**
    - 아이디: `teacher1`
    - 비밀번호: `teacher123`
    """)
    
    with st.form("quick_login"):
        st.markdown("### 👩‍🏫 선생님 로그인")
        username = st.text_input("아이디")
        password = st.text_input("비밀번호", type="password")
        
        if st.form_submit_button("로그인", use_container_width=True):
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

# 선생님/관리자 권한 체크
if user.get('role') not in ['teacher', 'admin']:
    st.error("⚠️ 선생님 또는 관리자만 접근 가능한 페이지입니다.")
    st.info(f"현재 로그인: {user.get('name')} ({user.get('role')})")
    
    if st.button("🚪 로그아웃", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user = None
        st.rerun()
    st.stop()

# ⭐ 반응형 CSS - 모바일/PC 완전 최적화
st.markdown("""
<style>
    /* PC 레이아웃 최적화 */
    .main { 
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        max-width: 1400px;
        margin: 0 auto;
        padding: 2rem;
    }
    
    .block-container {
        max-width: 1400px;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    
    /* 큰 화면 */
    @media (min-width: 1920px) {
        .main {
            max-width: 1600px;
        }
    }
    
    /* 중간 화면 */
    @media (max-width: 1400px) {
        .main {
            max-width: 100%;
            padding: 1.5rem;
        }
        .block-container {
            padding-left: 1.5rem;
            padding-right: 1.5rem;
        }
    }
    
    /* 태블릿 */
    @media (max-width: 1024px) {
        .main {
            padding: 1rem;
        }
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
    }
    
    .teacher-header {
        background: white; color: #333; padding: 30px; border-radius: 15px;
        text-align: center; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .teacher-title { font-size: 32px; font-weight: bold; color: #4CAF50; margin-bottom: 10px; }
    .stat-card-large {
        background: white; border-radius: 20px; padding: 40px; text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2); margin: 15px 0;
    }
    .stat-icon-large { font-size: 72px; margin-bottom: 20px; }
    .stat-number-large { font-size: 64px; font-weight: bold; margin: 20px 0; }
    .stat-label-large { font-size: 24px; color: #666; font-weight: 600; }
    .stat-present { color: #4CAF50; }
    .stat-late { color: #FF9800; }
    .stat-absent { color: #f44336; }
    .student-list-item {
        background: white; border-radius: 12px; padding: 20px; margin: 10px 0;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1); display: flex;
        justify-content: space-between; align-items: center;
    }
    .student-name { font-size: 20px; font-weight: bold; color: #333; }
    .student-status { padding: 10px 20px; border-radius: 20px; font-weight: bold; font-size: 18px; }
    .status-present { background: #d4edda; color: #155724; }
    .status-late { background: #fff3cd; color: #856404; }
    .status-absent { background: #f8d7da; color: #721c24; }
    .progress-container {
        background: #e0e0e0; border-radius: 20px; height: 50px; overflow: hidden; margin: 20px 0;
    }
    .progress-bar {
        height: 100%; background: linear-gradient(90deg, #4CAF50 0%, #45a049 100%);
        display: flex; align-items: center; justify-content: center;
        color: white; font-weight: bold; font-size: 24px; transition: width 1s ease;
    }
    .time-display {
        background: white; border-radius: 15px; padding: 20px; text-align: center;
        margin: 20px 0; box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    .time-value { font-size: 48px; font-weight: bold; color: #4CAF50; }
    .time-label { font-size: 18px; color: #666; margin-top: 10px; }
    .group-badge {
        display: inline-block; padding: 8px 16px; border-radius: 20px;
        background: #667eea; color: white; font-weight: bold; margin: 5px;
    }
    
    /* 선택 수업 카드 */
    .schedule-card {
        background: #d4edda;
        border-left: 5px solid #28a745;
        padding: 15px;
        border-radius: 10px;
        margin: 15px 0;
    }
    
    /* ⭐ QR 스캔 컨테이너 */
    .qr-container {
        width: 100%;
        max-width: 800px;
        margin: 0 auto;
    }
    
    /* ⭐ 모바일 최적화 */
    @media (max-width: 768px) {
        .main {
            padding: 10px !important;
        }
        
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        
        /* 헤더 */
        .teacher-header {
            padding: 20px 15px !important;
        }
        
        .teacher-title {
            font-size: 24px !important;
        }
        
        /* 통계 카드 */
        .stat-card-large {
            padding: 20px !important;
            margin: 10px 0 !important;
        }
        
        .stat-icon-large {
            font-size: 48px !important;
        }
        
        .stat-number-large {
            font-size: 42px !important;
        }
        
        .stat-label-large {
            font-size: 16px !important;
        }
        
        /* 학생 목록 */
        .student-list-item {
            padding: 12px !important;
            flex-direction: column !important;
            align-items: flex-start !important;
        }
        
        .student-name {
            font-size: 16px !important;
            margin-bottom: 8px;
        }
        
        .student-status {
            padding: 8px 16px !important;
            font-size: 14px !important;
        }
        
        /* 시간 표시 */
        .time-display {
            padding: 15px !important;
        }
        
        .time-value {
            font-size: 36px !important;
        }
        
        .time-label {
            font-size: 14px !important;
        }
        
        /* 진행률 바 */
        .progress-container {
            height: 40px !important;
        }
        
        .progress-bar {
            font-size: 18px !important;
        }
        
        /* 그룹 뱃지 */
        .group-badge {
            display: block !important;
            margin: 8px 0 !important;
            text-align: center !important;
        }
        
        /* 선택 수업 모바일 최적화 */
        .schedule-card {
            padding: 12px !important;
        }
        
        .schedule-card div {
            font-size: 14px !important;
            line-height: 1.6 !important;
        }
        
        /* 버튼 */
        .stButton > button {
            min-height: 48px !important;
            font-size: 16px !important;
            padding: 12px 20px !important;
        }
        
        /* 선택 박스 */
        .stSelectbox {
            font-size: 16px !important;
        }
        
        /* ⭐ 탭 모바일 최적화 */
        .stTabs [data-baseweb="tab"] {
            font-size: 13px !important;
            padding: 10px 6px !important;
            white-space: nowrap !important;
        }
        
        /* Metric */
        .stMetric {
            font-size: 14px !important;
        }
        
        /* ⭐ QR 스캔 모바일 */
        .qr-container {
            max-width: 100% !important;
        }
    }
    
    /* 작은 모바일 */
    @media (max-width: 375px) {
        .teacher-title {
            font-size: 20px !important;
        }
        
        .stat-number-large {
            font-size: 36px !important;
        }
        
        .time-value {
            font-size: 28px !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            font-size: 11px !important;
            padding: 8px 4px !important;
        }
    }
    
    /* 가로 모드 */
    @media (max-height: 500px) and (orientation: landscape) {
        .teacher-header {
            padding: 15px !important;
        }
        
        .stat-card-large {
            padding: 20px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# ⭐ 수업 그룹 관련 함수
def load_class_groups():
    """수업 그룹 정보 로드"""
    if not os.path.exists(CLASS_GROUPS_CSV):
        return pd.DataFrame(columns=['group_id', 'group_name', 'weekdays', 'start_time', 'end_time', 'start_date', 'end_date', 'total_hours'])
    try:
        df = pd.read_csv(CLASS_GROUPS_CSV, encoding='utf-8-sig')
        if 'total_hours' not in df.columns:
            df['total_hours'] = 1.0
        return df
    except:
        return pd.DataFrame(columns=['group_id', 'group_name', 'weekdays', 'start_time', 'end_time', 'start_date', 'end_date', 'total_hours'])

def load_student_groups():
    """학생-그룹 매핑 로드"""
    if not os.path.exists(STUDENT_GROUPS_CSV):
        return pd.DataFrame(columns=['student_name', 'group_id'])
    try:
        return pd.read_csv(STUDENT_GROUPS_CSV, encoding='utf-8-sig')
    except:
        return pd.DataFrame(columns=['student_name', 'group_id'])

# ⭐ 선생님-그룹 관련 함수
def load_teacher_groups():
    """선생님-그룹 매핑 로드 (날짜 지원)"""
    if not os.path.exists(TEACHER_GROUPS_CSV):
        df = pd.DataFrame(columns=['teacher_username', 'group_id', 'date'])
        df.to_csv(TEACHER_GROUPS_CSV, index=False, encoding='utf-8-sig')
        return df
    try:
        df = pd.read_csv(TEACHER_GROUPS_CSV, encoding='utf-8-sig')
        if 'date' not in df.columns:
            df['date'] = ''
        return df
    except:
        return pd.DataFrame(columns=['teacher_username', 'group_id', 'date'])

def get_teacher_groups(username, check_date=None):
    """
    선생님이 담당하는 그룹 ID 목록 (날짜 고려)
    """
    if check_date is None:
        check_date = date.today()
    
    df_teacher_groups = load_teacher_groups()
    
    if df_teacher_groups.empty:
        # 매핑 파일 없으면 모든 그룹 반환 (하위 호환)
        df_groups = load_class_groups()
        return df_groups['group_id'].tolist() if not df_groups.empty else []
    
    teacher_assignments = df_teacher_groups[df_teacher_groups['teacher_username'] == username]
    
    if teacher_assignments.empty:
        return []
    
    assigned_groups = []
    
    for _, assignment in teacher_assignments.iterrows():
        group_id = assignment['group_id']
        assigned_date = assignment['date']
        
        if pd.isna(assigned_date) or assigned_date == '':
            assigned_groups.append(group_id)
        else:
            try:
                assigned_date = pd.to_datetime(assigned_date).date()
                if assigned_date == check_date:
                    assigned_groups.append(group_id)
            except:
                assigned_groups.append(group_id)
    
    return list(set(assigned_groups))

def get_teacher_schedule(username, check_date=None):
    """(Supabase 연동) 선생님의 담당 수업 일정 반환"""
    if check_date is None:
        check_date = date.today()
    
    try:
        from supabase_client import supabase_mgr
        target_date_str = check_date.isoformat()
        
        all_schedules = supabase_mgr.get_schedule_for_date(target_date_str)
        user_name = st.session_state.user.get('name', username)
        
        teacher_schedules = []
        for sched in all_schedules:
            # 시간 파싱 및 KST 변환
            st_dt = pd.to_datetime(sched['start_time'])
            en_dt = pd.to_datetime(sched['end_time'])
            
            # 타임존 정보가 있으면 KST로 변환
            from datetime import timezone, timedelta
            kst = timezone(timedelta(hours=9))
            if st_dt.tzinfo:
                st_dt = st_dt.astimezone(kst)
            if en_dt.tzinfo:
                en_dt = en_dt.astimezone(kst)
                
            start_time = st_dt.strftime('%H:%M') if sched['start_time'] else "00:00"
            end_time = en_dt.strftime('%H:%M') if sched['end_time'] else "23:59"
            
            # 교육 시간 계산 (시간 단위)
            duration_hours = (en_dt - st_dt).total_seconds() / 3600
            
            schedule_info = {
                'id': sched['id'],
                'session': sched['class_name'],
                'start': start_time,
                'end': end_time,
                'start_dt': st_dt,
                'end_dt': en_dt,
                'teacher_name': sched['teacher_name'],
                'zoom_meeting_id': sched.get('zoom_meeting_id'),
                'total_hours': round(duration_hours, 1),
                'group_name': sched['class_name'],
                'group_id': sched.get('group_id')
            }
            # 선생님 혹은 관리자 필터링
            user_role = st.session_state.user.get('role', '') if 'user' in st.session_state and st.session_state.user else ''
            
            if user_role == 'admin':
                teacher_schedules.append(schedule_info)
            else:
                if sched['teacher_name'] and user_name in sched['teacher_name']:
                    teacher_schedules.append(schedule_info)
                
        return teacher_schedules
    except Exception as e:
        print(f"Schedule load error: {e}")
        return []

def get_group_students_by_id(group_id):
    """그룹 ID로 학생 목록 조회"""
    df_student_groups = load_student_groups()
    if df_student_groups.empty:
        return []
    
    students = df_student_groups[df_student_groups['group_id'] == group_id]['student_name'].tolist()
    return students

def get_student_group_name(student_name):
    """학생이 속한 그룹명 반환"""
    df_student_groups = load_student_groups()
    if df_student_groups.empty:
        return "미배정"
    
    student_groups = df_student_groups[df_student_groups['student_name'] == student_name]
    if student_groups.empty:
        return "미배정"
    
    group_id = student_groups.iloc[0]['group_id']
    df_groups = load_class_groups()
    
    if df_groups.empty:
        return "미배정"
    
    group = df_groups[df_groups['group_id'] == group_id]
    if group.empty:
        return "미배정"
    
    return group.iloc[0]['group_name']

def check_flask_connection():
    """Flask 서버 연결 상태 확인"""
    try:
        response = requests.get(f"http://localhost:{FLASK_PORT}/status", timeout=2)
        if response.status_code == 200:
            st.session_state['flask_connected'] = True
            return True
    except Exception:
        st.session_state['flask_connected'] = False
    return False

def get_students_for_schedule(schedule_info):
    """스케줄 정보에 맞는 학생 목록(dict 리스트) 반환"""
    from supabase_client import supabase_mgr
    import pandas as pd
    
    # 1. 명시적인 group_id 가 있는 경우 (Supabase에서 가져옴)
    if schedule_info.get('group_id'):
        students = supabase_mgr.get_students_by_group(schedule_info['group_id'])
        if students: return students
        
    # 2. group_id 가 없는 경우 (과거에 생성된 일정 등) - CSV 폴백
    session_name = schedule_info.get('session', '')
    if not session_name:
        session_name = schedule_info.get('group_name', '')
    
    df_classes = load_class_groups()
    df_std_groups = load_student_groups()
    
    valid_student_names = set()
    
    if not df_classes.empty and not df_std_groups.empty and session_name:
        matched_group_id = None
        for _, grp in df_classes.iterrows():
            g_name = str(grp['group_name']).strip()
            # session_name(예: "C-4") 와 group_name(예: "A", "B", "C") 매칭
            # 공백이나 특수기호 없이 첫 글자로 매칭하거나 정확히 포함되는지 확인
            if pd.notna(g_name) and g_name and g_name in session_name.split('-')[0]:
                matched_group_id = grp['group_id']
                break
                
        if pd.notna(matched_group_id):
            group_students_df = df_std_groups[df_std_groups['group_id'] == matched_group_id]
            valid_student_names = set(group_students_df['student_name'].dropna().tolist())

    all_db_students = supabase_mgr.get_all_students()
    
    if valid_student_names:
        return [s for s in all_db_students if s['student_name'] in valid_student_names]
    else:
        # 그룹을 식별할 수 없는 경우, 모든 학생을 반환하면 타반 학생이 출석되는 대참사 발생!
        # 따라서 안전하게 빈 배열을 리턴하도록 처리합니다.
        return []

def get_today_attendance():
    """⭐ (Supabase) 선택된 수업의 출석현황만 표시 (해당 반 학생만 필터링)"""
    try:
        from supabase_client import supabase_mgr
        
        selected_schedule = st.session_state.get('selected_schedule')
        if not selected_schedule: 
            return None
            
        schedule_id = selected_schedule.get('id')
        group_id = selected_schedule.get('group_id')
        if not schedule_id: return None
        
        # 1. 수업 그룹의 학생 목록 가져오기 (지정된 함수 사용)
        target_students = get_students_for_schedule(selected_schedule)
        group_student_names = {s['student_name'] for s in target_students}
        total_students = len(group_student_names)
            
        # 2. 스케줄에 따른 출석 로그 가져오기
        # ⭐ 'students!student_id' 명시적 조인 사용하여 별칭 오류 해결
        response = supabase_mgr.client.table('attendance') \
            .select('*, students!student_id(student_name)') \
            .eq('schedule_id', schedule_id) \
            .execute()
            
        all_logs = response.data
        
        # 3. 해당 그룹에 속한 학생들만 로그 필터링
        logs = []
        for log in all_logs:
            student_name = log.get('students', {}).get('student_name', '알수없음')
            # ⭐ 조건 엄밀히 적용: 학생이 해당 수업 명단에 있어야만 화면에 표시
            if total_students > 0 and student_name not in group_student_names:
                continue
            logs.append(log)
        
        # ⭐ 3-1. 학생별 중복 제거 (같은 학생이 여러 번 기록된 경우 최신 기록만 유지)
        seen_students = {}
        deduplicated_logs = []
        for log in logs:
            student_name = log.get('students', {}).get('student_name', '알수없음')
            check_in = log.get('check_in_time', '')
            
            if student_name in seen_students:
                # 기존 기록과 비교하여 최신 기록으로 교체
                existing_idx, existing_time = seen_students[student_name]
                if check_in > existing_time:
                    deduplicated_logs[existing_idx] = log
                    seen_students[student_name] = (existing_idx, check_in)
            else:
                seen_students[student_name] = (len(deduplicated_logs), check_in)
                deduplicated_logs.append(log)
        
        logs = deduplicated_logs
        
        if total_students == 0 and not group_id:
            total_students = max(len(logs), 1)

        # 4. 통계 계산
        present = sum(1 for log in logs if log['status'] == ATTENDANCE_STATUS_PRESENT)
        late = sum(1 for log in logs if log['status'] == ATTENDANCE_STATUS_LATE)
        # 중요: 결석자는 총원에서 현재 출결한 학생을 뺀 나머지 (데이터가 중복되지 않도록 주의)
        absent = max(0, total_students - present - late)
        
        # 5. 리스트 형식 만들기
        records_with_group = []
        for log in logs:
            check_in = log.get('check_in_time', '')
            if check_in:
                try:
                    time_part = check_in.split('T')[1] if 'T' in check_in else check_in
                    dt_str = time_part[:8]
                except:
                    dt_str = check_in[:8]
            else:
                dt_str = "00:00:00"
                
            student_name = log['students']['student_name'] if log.get('students') else '알수없음'
            
            records_with_group.append({
                'id': log['id'],
                '학생': student_name,
                '시간': dt_str,
                'status': log['status'],
                '그룹': selected_schedule.get('group_name', '기본')
            })
            
        return {
            'total': total_students,
            'present': present,
            'late': late,
            'absent': absent,
            'records': records_with_group
        }
    
    except Exception as e:
        import traceback
        st.error(f"출석 데이터 로드 오류: {e}")
        return None


def get_group_students(group_name):
    """특정 그룹의 학생 목록"""
    df_groups = load_class_groups()
    if df_groups.empty:
        return []
    
    group = df_groups[df_groups['group_name'] == group_name]
    if group.empty:
        return []
    
    group_id = group.iloc[0]['group_id']
    
    df_student_groups = load_student_groups()
    if df_student_groups.empty:
        return []
    
    students = df_student_groups[df_student_groups['group_id'] == group_id]['student_name'].tolist()
    return students

# 🆕 메모 관련 함수
def load_attendance_notes():
    """출석 메모 로드"""
    if not os.path.exists(ATTENDANCE_NOTES_CSV):
        return pd.DataFrame(columns=['timestamp', 'student_name', 'session', 'date', 'note', 'created_by', 'created_at'])
    try:
        return pd.read_csv(ATTENDANCE_NOTES_CSV, encoding='utf-8-sig')
    except:
        return pd.DataFrame(columns=['timestamp', 'student_name', 'session', 'date', 'note', 'created_by', 'created_at'])

def save_attendance_note(student_name, session, note_text, created_by, target_date=None):
    """출석 메모 저장"""
    try:
        df_notes = load_attendance_notes()
        
        if target_date is None:
            target_date = date.today()
        
        new_note = pd.DataFrame([{
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'student_name': student_name,
            'session': session,
            'date': target_date.isoformat() if isinstance(target_date, date) else target_date,
            'note': note_text,
            'created_by': created_by,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }])
        
        df_notes = pd.concat([df_notes, new_note], ignore_index=True)
        df_notes.to_csv(ATTENDANCE_NOTES_CSV, index=False, encoding='utf-8-sig')
        return True
    except Exception as e:
        print(f"메모 저장 오류: {e}")
        return False

def get_student_notes(student_name, target_date=None):
    """특정 학생의 메모 조회"""
    df_notes = load_attendance_notes()
    if df_notes.empty:
        return []
    
    if target_date:
        target_date_str = target_date.isoformat() if isinstance(target_date, date) else target_date
        student_notes = df_notes[
            (df_notes['student_name'] == student_name) & 
            (df_notes['date'] == target_date_str)
        ]
    else:
        student_notes = df_notes[df_notes['student_name'] == student_name]
    
    return student_notes.to_dict('records')

# 🆕 출석 수정 함수
def update_attendance_status(timestamp, student_name, new_status, session_name=None):
    """출석 상태 수정"""
    try:
        if not os.path.exists(ATTENDANCE_LOG_CSV):
            return False
        
        df_log = pd.read_csv(ATTENDANCE_LOG_CSV, encoding='utf-8-sig')
        
        # 타임스탬프와 학생명으로 찾기
        mask = (df_log['timestamp'] == timestamp) & (df_log['student_name'] == student_name)
        
        if not df_log[mask].empty:
            df_log.loc[mask, 'status'] = new_status
            df_log.to_csv(ATTENDANCE_LOG_CSV, index=False, encoding='utf-8-sig')
            return True
        
        return False
    except Exception as e:
        print(f"출석 수정 오류: {e}")
        return False

def delete_attendance_record(timestamp, student_name):
    """출석 기록 삭제"""
    try:
        if not os.path.exists(ATTENDANCE_LOG_CSV):
            return False
        
        df_log = pd.read_csv(ATTENDANCE_LOG_CSV, encoding='utf-8-sig')
        df_log = df_log[~((df_log['timestamp'] == timestamp) & (df_log['student_name'] == student_name))]
        df_log.to_csv(ATTENDANCE_LOG_CSV, index=False, encoding='utf-8-sig')
        return True
    except Exception as e:
        print(f"출석 삭제 오류: {e}")
        return False

# 🆕 통계 관련 함수
def get_weekly_attendance_stats(teacher_username):
    """주간 출석통계"""
    try:
        if not os.path.exists(ATTENDANCE_LOG_CSV):
            return None
        
        df_log = pd.read_csv(ATTENDANCE_LOG_CSV, encoding='utf-8-sig')
        if df_log.empty:
            return None
        
        df_log['date'] = pd.to_datetime(df_log['date']).dt.date
        
        # 최근 7일
        today = date.today()
        week_ago = today - timedelta(days=7)
        
        df_week = df_log[(df_log['date'] >= week_ago) & (df_log['date'] <= today)]
        
        if df_week.empty:
            return None
        
        # 날짜별 통계
        daily_stats = []
        for d in range(7):
            target_date = today - timedelta(days=6-d)
            day_data = df_week[df_week['date'] == target_date]
            
            total = len(day_data)
            present = len(day_data[day_data['status'] == ATTENDANCE_STATUS_PRESENT])
            late = len(day_data[day_data['status'] == ATTENDANCE_STATUS_LATE])
            absent = len(day_data[day_data['status'] == ATTENDANCE_STATUS_ABSENT])
            
            daily_stats.append({
                'date': target_date.strftime('%m/%d'),
                'total': total,
                'present': present,
                'late': late,
                'absent': absent,
                'rate': (present + late) / total * 100 if total > 0 else 0
            })
        
        return pd.DataFrame(daily_stats)
    
    except Exception as e:
        print(f"주간 통계 오류: {e}")
        return None

def get_monthly_attendance_stats():
    """월간 출석통계"""
    try:
        if not os.path.exists(ATTENDANCE_LOG_CSV):
            return None
        
        df_log = pd.read_csv(ATTENDANCE_LOG_CSV, encoding='utf-8-sig')
        if df_log.empty:
            return None
        
        df_log['date'] = pd.to_datetime(df_log['date']).dt.date
        
        # 최근 30일
        today = date.today()
        month_ago = today - timedelta(days=30)
        
        df_month = df_log[(df_log['date'] >= month_ago) & (df_log['date'] <= today)]
        
        if df_month.empty:
            return None
        
        # 주별 통계 (4주)
        weekly_stats = []
        for w in range(4):
            week_end = today - timedelta(days=w*7)
            week_start = week_end - timedelta(days=6)
            
            week_data = df_month[(df_month['date'] >= week_start) & (df_month['date'] <= week_end)]
            
            total = len(week_data)
            present = len(week_data[week_data['status'] == ATTENDANCE_STATUS_PRESENT])
            late = len(week_data[week_data['status'] == ATTENDANCE_STATUS_LATE])
            absent = len(week_data[week_data['status'] == ATTENDANCE_STATUS_ABSENT])
            
            weekly_stats.append({
                'week': f"{week_start.strftime('%m/%d')}-{week_end.strftime('%m/%d')}",
                'total': total,
                'present': present,
                'late': late,
                'absent': absent,
                'rate': (present + late) / total * 100 if total > 0 else 0
            })
        
        return pd.DataFrame(weekly_stats[::-1])  # 시간순 정렬
    
    except Exception as e:
        print(f"월간 통계 오류: {e}")
        return None
# 🆕 자동 결석 처리 함수 추가
def auto_process_absences():
    """
    자동 결석 처리: 수업 종료 후 미출석 학생을 자동으로 결석 처리
    앱 실행 시 자동으로 호출됨
    """
    try:
        from config import SCHEDULE_CSV, ATTENDANCE_LOG_CSV
        from utils import load_csv_safe, save_csv_safe
        import logging
        
        logger = logging.getLogger(__name__)
        
        df_schedule = load_csv_safe(SCHEDULE_CSV, ['date', 'start', 'end', 'session'])
        
        if df_schedule.empty:
            return 0, 0
        
        df_schedule['date'] = pd.to_datetime(df_schedule['date']).dt.date
        
        # 오늘 이전의 수업만 (어제까지)
        yesterday = date.today() - timedelta(days=1)
        past_schedules = df_schedule[df_schedule['date'] <= yesterday]
        
        if past_schedules.empty:
            return 0, 0
        
        # 최근 7일 이내만 처리
        week_ago = date.today() - timedelta(days=7)
        recent_schedules = past_schedules[past_schedules['date'] >= week_ago]
        
        if recent_schedules.empty:
            return 0, 0
        
        processed_count = 0
        total_absences = 0
        
        # 학생 데이터 로드
        from config import STUDENTS_CSV
        df_students = load_csv_safe(STUDENTS_CSV, ['name', 'qr_code', 'phone'])
        
        # 출석 데이터 로드
        df_attendance = load_csv_safe(ATTENDANCE_LOG_CSV, 
            ['date', 'session', 'student_name', 'qr_code', 'timestamp', 'status'])
        
        if df_students.empty:
            return 0, 0
        
        for _, sched in recent_schedules.iterrows():
            session_name = sched['session']
            target_date = sched['date']
            
            # 그룹명 추출
            df_groups = load_class_groups()
            df_student_groups = load_student_groups()
            
            group_name = session_name.split()[0] if ' ' in session_name else session_name
            matching_groups = df_groups[df_groups['group_name'].str.contains(group_name, na=False)]
            
            if matching_groups.empty:
                all_students = set(df_students['name'].tolist())
            else:
                group_ids = matching_groups['group_id'].tolist()
                students_in_groups = df_student_groups[df_student_groups['group_id'].isin(group_ids)]
                all_students = set(students_in_groups['student_name'].tolist())
            
            if not all_students:
                continue
            
            # 해당 날짜/세션의 출석 기록 확인
            if not df_attendance.empty:
                df_attendance['date'] = pd.to_datetime(df_attendance['date']).dt.date
                today_attendance = df_attendance[
                    (df_attendance['date'] == target_date) &
                    (df_attendance['session'] == session_name)
                ]
                attended_students = set(today_attendance['student_name'].tolist())
            else:
                attended_students = set()
            
            # 결석 대상 학생
            absent_students = all_students - attended_students
            
            if not absent_students:
                continue
            
            # 결석 처리
            class_end_str = sched['end']
            absence_time = datetime.combine(target_date, datetime.strptime(class_end_str, '%H:%M').time())
            
            new_records = []
            for student_name in absent_students:
                new_records.append({
                    'date': target_date.isoformat(),
                    'session': session_name,
                    'student_name': student_name,
                    'qr_code': student_name,
                    'timestamp': absence_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'status': ATTENDANCE_STATUS_ABSENT
                })
            
            if new_records:
                if os.path.exists(ATTENDANCE_LOG_CSV) and os.path.getsize(ATTENDANCE_LOG_CSV) > 0:
                    df_existing = pd.read_csv(ATTENDANCE_LOG_CSV, encoding='utf-8-sig')
                    df_new = pd.DataFrame(new_records)
                    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                    df_combined.to_csv(ATTENDANCE_LOG_CSV, index=False, encoding='utf-8-sig')
                else:
                    df_new = pd.DataFrame(new_records)
                    df_new.to_csv(ATTENDANCE_LOG_CSV, index=False, encoding='utf-8-sig')
                
                processed_count += 1
                total_absences += len(absent_students)
        
        return processed_count, total_absences
    
    except Exception as e:
        print(f"자동 결석 처리 오류: {e}")
        return 0, 0





# 메인 앱
def main():
    # 🆕 자동 결석 처리 (조용히 백그라운드에서 실행)
    if 'auto_absence_processed' not in st.session_state:
        try:
            processed_count, total_absences = auto_process_absences()
            
            # 결과를 세션에 저장 (한 번만 실행)
            st.session_state['auto_absence_processed'] = True
            st.session_state['auto_absence_count'] = processed_count
            st.session_state['auto_absence_total'] = total_absences
        except Exception as e:
            print(f"자동 결석 처리 실패: {e}")
            st.session_state['auto_absence_processed'] = True


    
    # 헤더
    st.markdown(f"""
    <div class="teacher-header">
        <div class="teacher-title">👩‍🏫 {user['name']} 선생님</div>
        <p style="font-size: 18px; color: #666;">
            오늘도 수고하십니다!
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 현재 시간
    now = datetime.now()
    st.markdown(f"""
    <div class="time-display">
        <div class="time-value">{now.strftime('%H:%M')}</div>
        <div class="time-label">{now.strftime('%Y년 %m월 %d일 (%A)')}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # ⭐ 선생님의 담당 수업만 표시 (대타 포함)
    schedules = get_teacher_schedule(user['username'])
    
    if schedules:
        st.markdown("### 📅 내 담당 수업")
        
        if len(schedules) > 1:
            schedule_options = [
                f"{s['start']}-{s['end']} | {s.get('group_name', s['session'])}"
                for s in schedules
            ]
            
            selected_idx = st.selectbox(
                "담당 수업 선택",
                range(len(schedules)),
                format_func=lambda i: schedule_options[i],
                key="schedule_selector"
            )
            
            selected_schedule = schedules[selected_idx]
        else:
            selected_schedule = schedules[0]
        
        # 선택된 수업 정보 표시
        st.markdown(f"""
        <div class="schedule-card">
            <div style="font-size: 18px; font-weight: bold; color: #155724; margin-bottom: 10px;">
                📅 선택 수업
            </div>
            <div style="font-size: 16px; color: #333; margin: 8px 0;">
                ⏰ <strong>{selected_schedule['start']} ~ {selected_schedule['end']}</strong>
            </div>
            <div style="font-size: 15px; color: #666; margin: 8px 0;">
                📚 {selected_schedule['session']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col_badge1, col_badge2 = st.columns(2)
        
        with col_badge1:
            if 'group_name' in selected_schedule:
                st.markdown(f"""
                <div style="background: #667eea; color: white; 
                            padding: 10px; border-radius: 10px; text-align: center; font-weight: bold;">
                    🎓 {selected_schedule['group_name']}
                </div>
                """, unsafe_allow_html=True)
        
        with col_badge2:
            if 'total_hours' in selected_schedule:
                st.markdown(f"""
                <div style="background: #4CAF50; color: white; 
                            padding: 10px; border-radius: 10px; text-align: center; font-weight: bold;">
                    🕐 총 {selected_schedule['total_hours']}시간
                </div>
                """, unsafe_allow_html=True)
        
        # 대타 여부 표시
        is_substitute = False
        df_teacher_groups = load_teacher_groups()
        if not df_teacher_groups.empty:
            teacher_assign = df_teacher_groups[
                (df_teacher_groups['teacher_username'] == user['username']) & 
                (df_teacher_groups['group_id'] == selected_schedule.get('group_id', -1))
            ]
            if not teacher_assign.empty:
                assign_date = teacher_assign.iloc[0]['date']
                if not pd.isna(assign_date) and assign_date != '':
                    is_substitute = True
        
        if is_substitute:
            st.info("🔄 대타 수업입니다.")
        
        st.session_state['selected_schedule'] = selected_schedule
    else:
        st.info("🔭 오늘은 담당 수업이 없습니다.")
        st.session_state['selected_schedule'] = None
    
    st.markdown("###")
    
    # 🆕 실시간 알림 배너 (지각/결석 학생)
    selected_schedule = st.session_state.get('selected_schedule')
    if selected_schedule:
        attendance_data = get_today_attendance()
        
        if attendance_data:
            # 지각 학생 알림
            if attendance_data['late'] > 0:
                late_students = [r['학생'] for r in attendance_data['records'] if r['status'] == ATTENDANCE_STATUS_LATE]
                st.warning(f"⏰ **지각 학생:** {', '.join(late_students[:3])}{'...' if len(late_students) > 3 else ''} (이 {attendance_data['late']}명)")
            
            # 결석 학생 알림 (예상)
            if attendance_data['absent'] > 0:
                if selected_schedule and 'group_id' in selected_schedule:
                    group_students = get_group_students_by_id(selected_schedule['group_id'])
                    attended_students = set([r['학생'] for r in attendance_data['records']])
                    absent_students = [s for s in group_students if s not in attended_students]
                    
                    if absent_students:
                        st.error(f"❌ **미출석 학생:** {', '.join(absent_students[:3])}{'...' if len(absent_students) > 3 else ''} (총 {len(absent_students)}명)")
    
    st.markdown("###")
    
    # ⭐ 탭 (모바일 최적화) - 🆕 탭 추가
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📹 출석", "📊 현황", "👥 그룹", "📋 목록", "✏️ 수정", "📈 통계", "📝 메모"
    ])
    
    # 탭 1: 출석 체크
    with tab1:
        st.markdown("## 📹 QR 출석 체크")
        
        if not check_flask_connection():
            st.error("⚠️ Flask 서버에 연결할 수 없습니다.")
            st.info("""
            **Flask 서버를 먼저 실행해주세요:**
            ```bash
            python flask_qr_attendance_app.py
            ```
            """)
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🔄 다시 연결 시도", use_container_width=True, key="reconnect_flask_tab1"):
                    st.rerun()
        else:
            col_status, col_stop = st.columns([4, 1])
            with col_status:
                st.success("✅ Flask 서버 연결됨 - 출석 체크 준비 완료!")
            with col_stop:
                if st.button("🛑 서버 끄기", use_container_width=True, help="QR 카메라 서버를 완전히 종료합니다."):
                    try:
                        requests.post(f"http://localhost:{FLASK_PORT}/api/shutdown", timeout=1)
                        st.session_state['flask_connected'] = False
                        st.success("✅ 서버 종료 신호를 보냈습니다.")
                        import time as _time
                        # Give it a moment then refresh
                        _time.sleep(1)
                        st.rerun()
                    except:
                        st.session_state['flask_connected'] = False
                        st.success("✅ 서버 종료 완료 (연결 오프라인)")
                        st.rerun()
            
            import socket
            
            def get_local_ip():
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    ip = s.getsockname()[0]
                    s.close()
                    return ip
                except:
                    return "127.0.0.1"
            
            local_ip = get_local_ip()
            stream_url_local = f"http://127.0.0.1:{FLASK_PORT}/video_feed"
            stream_url_network = f"http://{local_ip}:{FLASK_PORT}/video_feed"
            
            stream_url = stream_url_local
            
            # 모바일 접속 안내
            with st.expander("📱 모바일에서 접속하기", expanded=False):
                st.info(f"""
                **PC IP 주소:** `{local_ip}`
                
                **모바일 스트림 주소:**
                ```
                {stream_url_network}
                ```
                
                **모바일 접속 방법:**
                1. 📶 모바일과 PC가 **같은 Wi-Fi**에 연결되어 있어야 합니다
                2. 🌐 위 주소를 모바일 브라우저에 직접 입력하세요
                3. 🔗 또는 아래 버튼을 눌러 새 창에서 여세요
                """)
                
                st.link_button("📹 새 창에서 카메라 열기", stream_url_network)
            
            # ⭐ 반응형 iframe 높이
            # 모바일: 400px, PC: 700px
            iframe_height = 700
            
            html_code = f"""
            <div class="qr-container">
                <img src="{stream_url}"
                     style="width:100%; height:auto; max-height:{iframe_height}px;
                            border:5px solid #4CAF50; border-radius:20px;
                            box-shadow: 0 8px 20px rgba(0,0,0,0.2);"
                     alt="QR 출석 스트림"
                     onerror="this.style.display='none'; document.getElementById('error-msg').style.display='block';" />
                <div id="error-msg" style="display:none; padding:20px; background:#fff3cd; 
                     border-radius:10px; margin-top:20px; border-left:5px solid #ffc107;">
                    <h3 style="color:#856404; margin-bottom:15px;">📱 카메라를 불러올 수 없습니다</h3>
                    <p style="color:#856404; margin:15px 0; line-height:1.6;">
                        모바일에서는 같은 Wi-Fi에 연결된 상태에서<br>
                        아래 주소로 직접 접속해주세요:
                    </p>
                    <code style="background:#fff; padding:10px; display:block; margin:10px 0; 
                                 border-radius:5px; color:#333; word-break:break-all;">
                        {stream_url_network}
                    </code>
                    <a href="{stream_url_network}" target="_blank" 
                       style="background:#4CAF50; color:white; padding:12px 24px; 
                              border-radius:5px; text-decoration:none; display:inline-block; 
                              margin-top:15px; font-weight:bold;">
                        📹 새 창에서 카메라 열기
                    </a>
                </div>
            </div>
            """
            
            # ⭐ 모바일에서는 높이 줄임
            components.html(html_code, height=iframe_height, scrolling=False)
            
            st.markdown("###")
            
        # ==========================================
        # 🌐 Zoom 출석 연동 로직
        # ==========================================
        st.markdown("---")
        st.markdown("### 🌐 Zoom 온라인 출석 동기화")
        selected_schedule = st.session_state.get('selected_schedule')
        
        # Flask 관련 통계 (따로 분리)
        if check_flask_connection():
            col1, col2, col3 = st.columns(3)
            try:
                response = requests.get(f"http://localhost:{FLASK_PORT}/status", timeout=2)
                if response.status_code == 200:
                    status_data = response.json()
                    col1.metric("📊 총 출석", status_data.get('total_scanned', 0), delta="명")
                    col2.metric("📝 기록 수", status_data.get('total_records', 0), delta="건")
                    available = status_data.get('attendance_available', False)
                    col3.metric("🎯 출석 상태", "✅ 가능" if available else "❌ 불가")
            except:
                pass

        # Zoom 연동 버튼
        zoom_id = selected_schedule.get('zoom_meeting_id') if selected_schedule else None
        if zoom_id:
            st.info(f"현재 연결된 Zoom 회의 ID: **{zoom_id}**")
            if st.button("🔄 Zoom 출석 가져오기", use_container_width=True, type="primary", key="zoom_sync_btn"):
                with st.spinner("Zoom 서버에서 참가자 정보를 가져오는 중..."):
                    try:
                        from zoom_integration import zoom_mgr
                        from supabase_client import supabase_mgr
                        participants = zoom_mgr.get_meeting_participants(
                            zoom_id, 
                            start_time=selected_schedule.get('start_dt'),
                            end_time=selected_schedule.get('end_dt')
                        )
                        
                        if not participants:
                            st.warning("Zoom 회의 참가자를 찾을 수 없거나 회의가 아직 시작되지 않았습니다.")
                        else:
                            # ⭐ 수업에 해당하는 학생 명단만 가져오기 
                            all_students = get_students_for_schedule(selected_schedule)
                            
                            if not all_students:
                                st.warning("⚠️ 이 수업(C-4 등)에 연결된 학생 명단을 찾을 수 없어 보호 조치로 동기화를 중단합니다. (전체 학생이 출석 처리되는 것을 방지합니다)")
                            else:
                                student_map = {s['student_name']: s['id'] for s in all_students}
                                
                                sync_count = 0
                            for p in participants:
                                # 🔍 Zoom API 버전에 따라 'name' 또는 'user_name' 사용
                                zoom_name = p.get('name') or p.get('user_name') or ""
                                if not zoom_name: continue
                                
                                # ⭐ 유연한 이름 매칭 (공백 제거 후 비교)
                                matched_student_id = None
                                zoom_name_clean = zoom_name.replace(" ", "")
                                for system_name, student_id in student_map.items():
                                    system_name_clean = system_name.replace(" ", "")
                                    # ⭐ 유연한 매칭 로직: 1.완전일치 2.시작함 3.포함됨(2자이상)
                                    if (system_name_clean == zoom_name_clean or 
                                        zoom_name_clean.startswith(system_name_clean) or
                                        (len(system_name_clean) >= 2 and system_name_clean in zoom_name_clean)):
                                        matched_student_id = student_id
                                        matched_student_name = system_name
                                        break # 첫 번째 일치하는 학생으로 처리
                                
                                if not matched_student_id:
                                    print(f"Zoom matching failed for: {zoom_name}")
                                
                                if matched_student_id:
                                    if not supabase_mgr.check_already_attended(matched_student_id, selected_schedule['id']):
                                        now_str = datetime.now().isoformat()
                                        if supabase_mgr.insert_attendance(
                                            student_id=matched_student_id,
                                            schedule_id=selected_schedule['id'],
                                            check_in_time=now_str,
                                            status='출석',
                                            type_str='온라인',
                                            remark=f'Zoom 자동 출석 ({zoom_name})'
                                        ):
                                            sync_count += 1
                                if sync_count > 0:
                                    st.success(f"✅ 명단 확인 완료! 해당 반의 {sync_count}명을 '온라인 출석'으로 성공적으로 기록했습니다.")
                                else:
                                    st.info("새로 추가할 온라인 출석자가 없습니다. (이미 출석 처리되었거나 해당 반(예: C-4) 소속이 아닙니다.)")
                    except Exception as e:
                        st.error(f"Zoom 연동 중 오류 발생: {e}")
        else:
            st.warning("선택된 수업에 등록된 Zoom 회의 ID가 없습니다. (관리자 앱의 '수업 그룹' 또는 '일정 관리'에서 등록하세요.)")
    # 탭 2: 실시간 현황
    with tab2:
        st.markdown("## 📊 실시간 출석현황")
        # 🆕 자동 결석 처리 결과 표시
        if st.session_state.get('auto_absence_count', 0) > 0:
            with st.expander("✅ 자동 결석 처리 완료", expanded=False):
                st.success(f"""
                **최근 수업 자동 결석 처리:**
                - 처리된 수업: {st.session_state.get('auto_absence_count', 0)}개
                - 결석 처리: {st.session_state.get('auto_absence_total', 0)}명
                
                💡 수업 종료 후 미출석 학생이 자동으로 결석 처리되었습니다.
                """)
                
                if st.button("확인", key="confirm_auto_absence_teacher"):
                    st.session_state['auto_absence_count'] = 0
                    st.rerun()
        
        attendance = get_today_attendance()
        
        if attendance is None:
            st.error("⚠️ 출석 데이터를 불러올 수 없습니다.")
            st.info("Flask 서버가 실행 중인지 확인해주세요.")
        else:
            # 대형 통계 카드
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div class="stat-card-large">
                    <div class="stat-icon-large">✅</div>
                    <div class="stat-number-large stat-present">{attendance['present']}</div>
                    <div class="stat-label-large">출석</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="stat-card-large">
                    <div class="stat-icon-large">⏰</div>
                    <div class="stat-number-large stat-late">{attendance['late']}</div>
                    <div class="stat-label-large">지각</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="stat-card-large">
                    <div class="stat-icon-large">❌</div>
                    <div class="stat-number-large stat-absent">{attendance['absent']}</div>
                    <div class="stat-label-large">결석</div>
                </div>
                """, unsafe_allow_html=True)
            
            # 출석률
            if attendance['total'] > 0:
                rate = ((attendance['present'] + attendance['late']) / attendance['total']) * 100
                
                st.markdown("### 📈 출석률")
                st.markdown(f"""
                <div class="progress-container">
                    <div class="progress-bar" style="width: {rate}%;">
                        {rate:.1f}% ({attendance['present'] + attendance['late']} / {attendance['total']})
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if rate >= 90:
                    st.success("🏆 우수한 출석률입니다!")
                elif rate >= 80:
                    st.info("👍 좋은 출석률입니다!")
                elif rate >= 70:
                    st.warning("⚠️ 출석률이 조금 낮습니다.")
                else:
                    st.error("⚠ 출석률이 낮습니다. 결석자 확인이 필요합니다.")
            
            st.markdown("###")
            
            # 최근 출석 기록
            st.subheader("🕐 최근 출석 기록")
            
            if attendance['records']:
                recent_records = attendance['records'][-10:][::-1]
                
                for record in recent_records:
                    status = record['status']
                    
                    if status == ATTENDANCE_STATUS_PRESENT:
                        status_class = 'status-present'
                        icon = '✅'
                    elif status == ATTENDANCE_STATUS_LATE:
                        status_class = 'status-late'
                        icon = '⏰'
                    else:
                        status_class = 'status-absent'
                        icon = '❌'
                    
                    group_badge = f'<span class="group-badge">{record["그룹"]}</span>' if record['그룹'] != '미배정' else ''
                    
                    col1, col2, col3 = st.columns([5, 3, 1])
                    with col1:
                        st.markdown(f"""
                        <div class="student-list-item" style="border: none; margin: 0; padding: 10px 0;">
                            <div>
                                <span class="student-name">{record['학생']}</span>
                                {group_badge}
                                <span style="color: #999; margin-left: 15px; font-size: 16px;">
                                    {record['시간']}
                                </span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown(f"""
                        <div class="student-list-item" style="border: none; margin: 0; padding: 10px 0; justify-content: flex-end;">
                            <div class="student-status {status_class}">
                                {icon} {status}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    with col3:
                        if st.button("🗑️ 삭제", key=f"del_att_{record['id']}", help="이 출석 기록을 영구적으로 삭제합니다."):
                            with st.spinner("삭제 중..."):
                                try:
                                    from supabase_client import supabase_mgr
                                    res = supabase_mgr.client.table('attendance').delete().eq('id', record['id']).execute()
                                    if res.data or not res.error:
                                        st.toast(f"✅ {record['학생']} 기록 삭제 완료")
                                        st.success("✅ 삭제되었습니다.")
                                        import time as _time
                                        _time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error(f"❌ 삭제 실패: {res.error}")
                                except Exception as e:
                                    st.error(f"❌ 시스템 오류: {e}")
                                
                    st.markdown("<hr style='margin:0.5em 0;'>", unsafe_allow_html=True)
            else:
                st.info("아직 출석 기록이 없습니다.")

    # ⭐ 탭 3: 그룹별 현황
    with tab3:
        st.markdown("## 👥 그룹별 출석현황")
        
        df_groups = load_class_groups()
        
        if df_groups.empty:
            st.info("등록된 수업 그룹이 없습니다.")
        else:
            attendance = get_today_attendance()
            
            # ⭐ 선택된 수업의 그룹만 표시
            selected_schedule = st.session_state.get('selected_schedule')
            
            matched_group_id = None
            if selected_schedule:
                if selected_schedule.get('group_id'):
                    matched_group_id = selected_schedule['group_id']
                else:
                    # group_id가 누락된 경우 session_name에서 유추
                    session_name = selected_schedule.get('session', '') or selected_schedule.get('group_name', '')
                    import pandas as pd
                    for _, grp in df_groups.iterrows():
                        g_name = str(grp['group_name']).strip()
                        if pd.notna(g_name) and g_name and g_name in session_name.split('-')[0]:
                            matched_group_id = grp['group_id']
                            break
            
            if matched_group_id is not None:
                # 선택된 그룹만 표시
                df_groups = df_groups[df_groups['group_id'] == matched_group_id]
            
            for _, group in df_groups.iterrows():
                group_name = group['group_name']
                group_students = get_group_students(group_name)
                
                if not group_students:
                    continue
                
                group_present = 0
                group_late = 0
                group_absent = 0
                
                if attendance and attendance['records']:
                    attended = {r['학생']: r['status'] for r in attendance['records']}
                    
                    for student in group_students:
                        status = attended.get(student)
                        if status == ATTENDANCE_STATUS_PRESENT:
                            group_present += 1
                        elif status == ATTENDANCE_STATUS_LATE:
                            group_late += 1
                        else:
                            group_absent += 1
                else:
                    group_absent = len(group_students)
                
                total_group = len(group_students)
                group_rate = ((group_present + group_late) / total_group * 100) if total_group > 0 else 0
                
                st.markdown(f"### 🎓 {group_name}")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("👥 전체", total_group)
                
                with col2:
                    st.metric("✅ 출석", group_present, delta=f"{group_rate:.0f}%")
                
                with col3:
                    st.metric("⏰ 지각", group_late)
                
                with col4:
                    st.metric("❌ 결석", group_absent)
                
                st.markdown(f"""
                <div class="progress-container" style="height: 30px;">
                    <div class="progress-bar" style="width: {group_rate}%; font-size: 18px;">
                        {group_rate:.1f}%
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                with st.expander(f"📋 {group_name} 학생 목록 ({total_group}명)"):
                    if attendance and attendance['records']:
                        attended = {r['학생']: r['status'] for r in attendance['records']}
                    else:
                        attended = {}
                    
                    cols = st.columns(3)
                    for idx, student in enumerate(group_students):
                        with cols[idx % 3]:
                            if student in attended:
                                if attended[student] == ATTENDANCE_STATUS_PRESENT:
                                    st.success(f"✅ {student}")
                                elif attended[student] == ATTENDANCE_STATUS_LATE:
                                    st.warning(f"⏰ {student}")
                            else:
                                st.error(f"❌ {student}")
                
                st.markdown("---")
    
    # 탭 4: 학생 목록
    with tab4:
        st.markdown("## 📋 전체 학생 목록")
        
        df_students = load_csv_safe(STUDENTS_CSV, ['name', 'qr_code', 'phone'])
        attendance = get_today_attendance()
        
        if not df_students.empty:
            st.info(f"📚 전체 학생: {len(df_students)}명")
            
            if attendance and attendance['records']:
                attended = {r['학생']: r['status'] for r in attendance['records']}
            else:
                attended = {}
            
            # 출석한 학생
            st.markdown("### ✅ 출석한 학생")
            present_students = [s for s in df_students['name'] if attended.get(s) == ATTENDANCE_STATUS_PRESENT]            
            if present_students:
                cols = st.columns(3)
                for idx, name in enumerate(present_students):
                    with cols[idx % 3]:
                        group = get_student_group_name(name)
                        st.success(f"✅ {name}")
                        st.caption(f"🎓 {group}")
            else:
                st.info("아직 출석한 학생이 없습니다.")
            
            # 지각한 학생
            st.markdown("### ⏰ 지각한 학생")
            late_students = [s for s in df_students['name'] if attended.get(s) == ATTENDANCE_STATUS_LATE] 
            
            if late_students:
                cols = st.columns(3)
                for idx, name in enumerate(late_students):
                    with cols[idx % 3]:
                        group = get_student_group_name(name)
                        st.warning(f"⏰ {name}")
                        st.caption(f"🎓 {group}")
            else:
                st.info("지각한 학생이 없습니다.")
            
            # 미출석 학생
            st.markdown("### ❌ 미출석 학생")
            absent_students = [s for s in df_students['name'] if s not in attended]
            
            if absent_students:
                cols = st.columns(3)
                for idx, name in enumerate(absent_students):
                    with cols[idx % 3]:
                        group = get_student_group_name(name)
                        st.error(f"❌ {name}")
                        st.caption(f"🎓 {group}")
                
                st.markdown("###")
                st.warning(f"⚠️ {len(absent_students)}명의 학생이 아직 출석하지 않았습니다.")
            else:
                st.success("🎉 모든 학생이 출석했습니다!")
        else:
            st.info("등록된 학생이 없습니다.")
    
    # 🆕 탭 5: 출석 수정
    with tab5:
        st.markdown("## ✏️ 출석 기록 수정")
        
        st.info("💡 **실수로 잘못 체크된 출석을 수정하거나 삭제할 수 있습니다.**")
        
        # 수정할 날짜 선택
        col_date1, col_date2 = st.columns(2)
        
        with col_date1:
            edit_date = st.date_input(
                "📅 수정할 날짜",
                value=date.today(),
                key="edit_date_selector"
            )
        
        with col_date2:
            # 해당 날짜의 세션 로드
            df_schedule = load_csv_safe(SCHEDULE_CSV, ['date', 'start', 'end', 'session'])
            if not df_schedule.empty:
                df_schedule['date'] = pd.to_datetime(df_schedule['date']).dt.date
                day_schedules = df_schedule[df_schedule['date'] == edit_date]
                
                if not day_schedules.empty:
                    session_options = day_schedules['session'].tolist()
                    edit_session = st.selectbox(
                        "📚 수업 선택",
                        ["전체"] + session_options,
                        key="edit_session_selector"
                    )
                else:
                    edit_session = "전체"
                    st.warning("⚠️ 해당 날짜에 수업이 없습니다.")
            else:
                edit_session = "전체"
        
        st.markdown("---")
        
        # 출석 기록 로드
        try:
            if os.path.exists(ATTENDANCE_LOG_CSV):
                df_attendance = pd.read_csv(ATTENDANCE_LOG_CSV, encoding='utf-8-sig')
                
                if not df_attendance.empty:
                    df_attendance['date'] = pd.to_datetime(df_attendance['date']).dt.date
                    
                    # 필터링
                    df_filtered = df_attendance[df_attendance['date'] == edit_date]
                    
                    if edit_session != "전체":
                        df_filtered = df_filtered[df_filtered['session'] == edit_session]
                    
                    if not df_filtered.empty:
                        st.markdown(f"### 📋 출석 기록 ({len(df_filtered)}건)")
                        
                        # 정렬
                        df_filtered = df_filtered.sort_values('timestamp', ascending=False)
                        
                        for idx, record in df_filtered.iterrows():
                            status_color = {
                                '출석': '#d4edda',
                                '지각': '#fff3cd',
                                '결석': '#f8d7da'
                            }.get(record['status'], '#f5f5f5')
                            
                            status_icon = {
                                '출석': '✅',
                                '지각': '⏰',
                                '결석': '❌'
                            }.get(record['status'], '📝')
                            
                            with st.expander(
                                f"{status_icon} {record['student_name']} - {record['timestamp'][:16]}",
                                expanded=False
                            ):
                                st.markdown(f"""
                                <div style="background: {status_color}; padding: 15px; border-radius: 10px; margin-bottom: 15px;">
                                    <div style="font-weight: bold; font-size: 16px;">
                                        {record['student_name']}
                                    </div>
                                    <div style="color: #666; margin-top: 5px;">
                                        📚 {record.get('session', 'N/A')}
                                    </div>
                                    <div style="color: #666; margin-top: 5px;">
                                        🕐 {record['timestamp']}
                                    </div>
                                    <div style="color: #333; margin-top: 10px; font-size: 18px;">
                                        상태: {status_icon} {record['status']}
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                st.markdown("---")
                                
                                # 수정 폼
                                with st.form(f"edit_form_{idx}"):
                                    st.markdown("**✏️ 상태 수정**")
                                    
                                    new_status = st.selectbox(
                                        "새로운 상태",
                                        ["출석", "지각", "결석"],
                                        index=["출석", "지각", "결석"].index(record['status']),
                                        key=f"status_edit_{idx}"
                                    )
                                    
                                    col_submit, col_delete = st.columns(2)
                                    
                                    with col_submit:
                                        submitted = st.form_submit_button(
                                            "💾 수정",
                                            use_container_width=True,
                                            type="primary"
                                        )
                                    
                                    with col_delete:
                                        deleted = st.form_submit_button(
                                            "🗑️ 삭제",
                                            use_container_width=True,
                                            type="secondary"
                                        )
                                    
                                    if submitted:
                                        if update_attendance_status(
                                            record['timestamp'],
                                            record['student_name'],
                                            new_status,
                                            record.get('session')
                                        ):
                                            st.success(f"✅ {record['student_name']}의 출석 상태가 '{new_status}'(으)로 수정되었습니다!")
                                            st.balloons()
                                            st.rerun()
                                        else:
                                            st.error("❌ 수정 중 오류가 발생했습니다.")
                                    
                                    if deleted:
                                        if delete_attendance_record(
                                            record['timestamp'],
                                            record['student_name']
                                        ):
                                            st.success(f"✅ {record['student_name']}의 출석 기록이 삭제되었습니다!")
                                            st.rerun()
                                        else:
                                            st.error("❌ 삭제 중 오류가 발생했습니다.")
                    else:
                        st.info("🔭 해당 조건의 출석 기록이 없습니다.")
                else:
                    st.info("🔭 출석 기록이 없습니다.")
            else:
                st.info("🔭 아직 출석 기록 파일이 생성되지 않았습니다.")
        
        except Exception as e:
            st.error(f"❌ 출석 기록 로드 중 오류: {e}")
    
    # 🆕 탭 6: 통계 그래프
    with tab6:
        st.markdown("## 📈 출석 통계 & 그래프")
        
        # 주간/월간 선택
        stats_period = st.radio(
            "📊 통계 기간",
            ["주간 (최근 7일)", "월간 (최근 4주)"],
            horizontal=True,
            key="stats_period"
        )
        
        st.markdown("---")
        
        if "주간" in stats_period:
            # 주간 통계
            df_stats = get_weekly_attendance_stats(user['username'])
            
            if df_stats is not None and not df_stats.empty:
                st.markdown("### 📊 주간 출석통계")
                
                # 출석률 라인 차트
                fig_line = go.Figure()
                
                fig_line.add_trace(go.Scatter(
                    x=df_stats['date'],
                    y=df_stats['rate'],
                    mode='lines+markers',
                    name='출석률',
                    line=dict(color='#4CAF50', width=3),
                    marker=dict(size=10)
                ))
                
                fig_line.update_layout(
                    title='📈 주간 출석률 추이',
                    xaxis_title='날짜',
                    yaxis_title='출석률 (%)',
                    yaxis=dict(range=[0, 100]),
                    hovermode='x unified',
                    height=400
                )
                
                st.plotly_chart(fig_line, use_container_width=True)
                
                st.markdown("###")
                
                # 출석/지각/결석 막대 차트
                fig_bar = go.Figure()
                
                fig_bar.add_trace(go.Bar(
                    name='출석',
                    x=df_stats['date'],
                    y=df_stats['present'],
                    marker_color='#4CAF50'
                ))
                
                fig_bar.add_trace(go.Bar(
                    name='지각',
                    x=df_stats['date'],
                    y=df_stats['late'],
                    marker_color='#FF9800'
                ))
                
                fig_bar.add_trace(go.Bar(
                    name='결석',
                    x=df_stats['date'],
                    y=df_stats['absent'],
                    marker_color='#f44336'
                ))
                
                fig_bar.update_layout(
                    title='📊 일별 출석 현황',
                    xaxis_title='날짜',
                    yaxis_title='학생 수 (명)',
                    barmode='stack',
                    height=400
                )
                
                st.plotly_chart(fig_bar, use_container_width=True)
                
                st.markdown("###")
                
                # 데이터 테이블
                st.markdown("### 📋 상세 데이터")
                
                display_df = df_stats.copy()
                display_df.columns = ['날짜', '전체', '출석', '지각', '결석', '출석률 (%)']
                display_df['출석률 (%)'] = display_df['출석률 (%)'].round(1)
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
            else:
                st.info("🔭 최근 7일간의 출석 기록이 없습니다.")
        
        else:
            # 월간 통계
            df_stats = get_monthly_attendance_stats()
            
            if df_stats is not None and not df_stats.empty:
                st.markdown("### 📊 월간 출석통계")
                
                # 출석률 라인 차트
                fig_line = go.Figure()
                
                fig_line.add_trace(go.Scatter(
                    x=df_stats['week'],
                    y=df_stats['rate'],
                    mode='lines+markers',
                    name='출석률',
                    line=dict(color='#667eea', width=3),
                    marker=dict(size=12)
                ))
                
                fig_line.update_layout(
                    title='📈 주별 출석률 추이',
                    xaxis_title='기간',
                    yaxis_title='출석률 (%)',
                    yaxis=dict(range=[0, 100]),
                    hovermode='x unified',
                    height=400
                )
                
                st.plotly_chart(fig_line, use_container_width=True)
                
                st.markdown("###")
                
                # 출석/지각/결석 막대 차트
                fig_bar = go.Figure()
                
                fig_bar.add_trace(go.Bar(
                    name='출석',
                    x=df_stats['week'],
                    y=df_stats['present'],
                    marker_color='#4CAF50'
                ))
                
                fig_bar.add_trace(go.Bar(
                    name='지각',
                    x=df_stats['week'],
                    y=df_stats['late'],
                    marker_color='#FF9800'
                ))
                
                fig_bar.add_trace(go.Bar(
                    name='결석',
                    x=df_stats['week'],
                    y=df_stats['absent'],
                    marker_color='#f44336'
                ))
                
                fig_bar.update_layout(
                    title='📊 주별 출석 현황',
                    xaxis_title='기간',
                    yaxis_title='학생 수 (명)',
                    barmode='stack',
                    height=400
                )
                
                st.plotly_chart(fig_bar, use_container_width=True)
                
                st.markdown("###")
                
                # 데이터 테이블
                st.markdown("### 📋 상세 데이터")
                
                display_df = df_stats.copy()
                display_df.columns = ['기간', '전체', '출석', '지각', '결석', '출석률 (%)']
                display_df['출석률 (%)'] = display_df['출석률 (%)'].round(1)
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
            else:
                st.info("🔭 최근 4주간의 출석 기록이 없습니다.")
    
    # 🆕 탭 7: 메모 관리
    with tab7:
        st.markdown("## 📝 특이사항 메모")
        
        st.info("💡 **학생별 특이사항이나 중요 사항을 기록할 수 있습니다.**")
        
        # 메모 추가 섹션
        with st.expander("➕ 새 메모 추가", expanded=False):
            with st.form("add_note_form"):
                st.markdown("### 📝 메모 작성")
                
                col_note1, col_note2 = st.columns(2)
                
                with col_note1:
                    # 학생 선택
                    df_students = load_csv_safe(STUDENTS_CSV, ['name', 'qr_code', 'phone'])
                    if not df_students.empty:
                        note_student = st.selectbox(
                            "👤 학생 선택",
                            df_students['name'].tolist(),
                            key="note_student"
                        )
                    else:
                        note_student = None
                        st.warning("등록된 학생이 없습니다.")
                
                with col_note2:
                    # 날짜 선택
                    note_date = st.date_input(
                        "📅 날짜",
                        value=date.today(),
                        key="note_date"
                    )
                
                # 세션 선택
                df_schedule = load_csv_safe(SCHEDULE_CSV, ['date', 'start', 'end', 'session'])
                if not df_schedule.empty:
                    df_schedule['date'] = pd.to_datetime(df_schedule['date']).dt.date
                    day_schedules = df_schedule[df_schedule['date'] == note_date]
                    
                    if not day_schedules.empty:
                        session_options = ["일반 메모"] + day_schedules['session'].tolist()
                        note_session = st.selectbox(
                            "📚 관련 수업 (선택)",
                            session_options,
                            key="note_session"
                        )
                    else:
                        note_session = "일반 메모"
                else:
                    note_session = "일반 메모"
                
                # 메모 내용
                note_text = st.text_area(
                    "📝 메모 내용",
                    height=150,
                    placeholder="특이사항, 건강 상태, 학습 태도 등을 기록하세요...",
                    key="note_text"
                )
                
                # 제출
                submitted = st.form_submit_button(
                    "💾 메모 저장",
                    use_container_width=True,
                    type="primary"
                )
                
                if submitted:
                    if note_student and note_text and len(note_text.strip()) >= 5:
                        if save_attendance_note(
                            student_name=note_student,
                            session=note_session,
                            note_text=note_text.strip(),
                            created_by=user['name'],
                            target_date=note_date
                        ):
                            st.success("✅ 메모가 저장되었습니다!")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("❌ 메모 저장 중 오류가 발생했습니다.")
                    else:
                        st.error("❌ 학생을 선택하고 5자 이상의 메모를 입력해주세요.")
        
        st.markdown("---")
        
        # 메모 조회 섹션
        st.markdown("### 📋 저장된 메모")
        
        col_filter1, col_filter2 = st.columns(2)
        
        with col_filter1:
            # 학생 필터
            df_students = load_csv_safe(STUDENTS_CSV, ['name', 'qr_code', 'phone'])
            if not df_students.empty:
                student_filter = st.selectbox(
                    "👤 학생 선택 (전체)",
                    ["전체"] + df_students['name'].tolist(),
                    key="note_filter_student"
                )
            else:
                student_filter = "전체"
        
        with col_filter2:
            # 날짜 필터
            date_filter = st.date_input(
                "📅 날짜 (선택)",
                value=None,
                key="note_filter_date"
            )
        
        # 메모 로드
        df_notes = load_attendance_notes()
        
        if not df_notes.empty:
            # 필터 적용
            df_filtered_notes = df_notes.copy()
            
            if student_filter != "전체":
                df_filtered_notes = df_filtered_notes[df_filtered_notes['student_name'] == student_filter]
            
            if date_filter:
                date_filter_str = date_filter.isoformat()
                df_filtered_notes = df_filtered_notes[df_filtered_notes['date'] == date_filter_str]
            
            if not df_filtered_notes.empty:
                # 최신순 정렬
                df_filtered_notes = df_filtered_notes.sort_values('created_at', ascending=False)
                
                st.info(f"📝 총 {len(df_filtered_notes)}개의 메모")
                
                for idx, note in df_filtered_notes.iterrows():
                    with st.expander(
                        f"👤 {note['student_name']} | 📅 {note['date']} | {note['session']}",
                        expanded=False
                    ):
                        st.markdown(f"""
                        <div style="background: #f0f7ff; padding: 15px; border-radius: 10px; 
                                    border-left: 4px solid #2196F3; margin-bottom: 15px;">
                            <div style="color: #1976D2; font-weight: bold; margin-bottom: 10px;">
                                📝 {note['student_name']} - {note['session']}
                            </div>
                            <div style="color: #666; font-size: 13px; margin-bottom: 10px;">
                                📅 {note['date']} | ✏️ {note['created_by']} | 🕐 {note['created_at']}
                            </div>
                            <div style="color: #333; line-height: 1.6; white-space: pre-wrap; padding: 10px; 
                                        background: white; border-radius: 5px;">
                                {note['note']}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("🔭 조건에 맞는 메모가 없습니다.")
        else:
            st.info("🔭 아직 작성된 메모가 없습니다.")
    
    # 하단 로그아웃
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("🔄 새로고침", use_container_width=True, key="refresh_main_bottom"):
            st.rerun()
    
    with col2:
        # 출석 데이터 다시 가져오기
        attendance_data = get_today_attendance()
        if attendance_data and attendance_data.get('records'):
            df_export = pd.DataFrame(attendance_data['records'])
            csv = df_export.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                "📥 출석 기록 다운로드",
                csv,
                file_name=f"attendance_{date.today()}.csv",
                mime="text/csv",
                use_container_width=True,
                key="download_attendance_bottom"
            )
    
    with col3:
        if st.button("🚪 로그아웃", use_container_width=True, key="logout_main_bottom"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()

if __name__ == "__main__":
    main()

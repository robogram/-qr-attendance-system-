"""
Streamlit QR 출석 관리 앱 - Flask 독립 버전
Flask 서버 없이도 모든 기능 작동 (Priority 2 완료)
UI/UX 개선 및 PWA 지원
"""
import streamlit as st
import pandas as pd
import os
from datetime import datetime, date, time, timedelta
import io
import qrcode
import requests
import streamlit.components.v1 as components
import zipfile

# ✅ 수정: 시간 상수 추가
from config import (
    STUDENTS_CSV, SCHEDULE_CSV, PARENTS_CSV, ATTENDANCE_LOG_CSV,
    ATT_DIR, REP_DIR, FLASK_PORT,
    EARLY_ARRIVAL_MINUTES, LATE_THRESHOLD_MINUTES, AUTO_ABSENCE_MINUTES,  # 🆕 추가
    ATTENDANCE_BUFFER_BEFORE, ATTENDANCE_BUFFER_AFTER,  # 🆕 추가
    ATTENDANCE_STATUS_PRESENT, ATTENDANCE_STATUS_LATE, ATTENDANCE_STATUS_ABSENT  # 🆕 추가
)

from utils import (
    load_csv_safe, save_csv_safe, logger,
    generate_session_key, normalize_phone  # 🆕 공통 함수 사용
)

# 페이지 설정
st.set_page_config(
    page_title="로보그램 QR출석",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': 'https://www.robogram.com/help',
        'Report a bug': "https://www.robogram.com/bug",
        'About': "# 로보그램 QR 출석 시스템 v3.0 (Flask 독립)"
    }
)

# 커스텀 CSS - 모바일 최적화
st.markdown("""
<style>
    /* 전체 레이아웃 */
    .main {
        padding: 0.5rem;
    }
    
    /* 모바일 터치 최적화 버튼 */
    .stButton > button {
        width: 100%;
        min-height: 50px;
        font-size: 16px;
        font-weight: 600;
        border-radius: 10px;
        margin: 5px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    /* 주요 액션 버튼 (초록색) */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        color: white;
        border: none;
    }
    
    /* 입력 필드 */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select,
    .stDateInput > div > div > input,
    .stTimeInput > div > div > input {
        font-size: 16px;
        min-height: 50px;
        border-radius: 8px;
    }
    
    /* 카드 스타일 */
    .student-card {
        background: white;
        padding: 15px;
        margin: 10px 0;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-left: 4px solid #4CAF50;
    }
    
    .schedule-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 15px;
        margin: 10px 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* 통계 카드 */
    .stat-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin: 5px;
    }
    
    .stat-number {
        font-size: 36px;
        font-weight: bold;
        color: #4CAF50;
        margin: 10px 0;
    }
    
    .stat-label {
        font-size: 14px;
        color: #666;
    }
    
    /* 헤더 스타일 */
    h1 {
        font-size: 24px !important;
        font-weight: 700 !important;
        color: #2c3e50 !important;
        margin-bottom: 1rem !important;
    }
    
    h2 {
        font-size: 20px !important;
        font-weight: 600 !important;
        color: #34495e !important;
        margin: 1.5rem 0 1rem 0 !important;
    }
    
    h3 {
        font-size: 18px !important;
        font-weight: 600 !important;
        color: #555 !important;
    }
    
    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 20px;
        border-radius: 8px;
        font-weight: 600;
    }
    
    /* 데이터 테이블 모바일 최적화 */
    .dataframe {
        font-size: 14px;
    }
    
    /* 성공 메시지 */
    .success-message {
        background: #d4edda;
        color: #155724;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #28a745;
        margin: 10px 0;
    }
    
    /* 경고 메시지 */
    .warning-message {
        background: #fff3cd;
        color: #856404;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #ffc107;
        margin: 10px 0;
    }
    
    /* 에러 메시지 */
    .error-message {
        background: #f8d7da;
        color: #721c24;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #dc3545;
        margin: 10px 0;
    }
    
    /* 로딩 스피너 */
    .stSpinner > div {
        border-top-color: #4CAF50 !important;
    }
    
    /* 모바일 반응형 */
    @media (max-width: 768px) {
        .main {
            padding: 0.25rem;
        }
        
        h1 {
            font-size: 20px !important;
        }
        
        h2 {
            font-size: 18px !important;
        }
        
        .stat-number {
            font-size: 28px;
        }
        
        .stTabs [data-baseweb="tab"] {
            padding: 0 10px;
            font-size: 14px;
        }
    }
    
    /* 다크모드 대응 */
    @media (prefers-color-scheme: dark) {
        .student-card, .stat-card {
            background: #2d3748;
            color: #e2e8f0;
        }
    }
</style>
""", unsafe_allow_html=True)

from utils import get_today_kst
date_today = get_today_kst()

# 세션 초기화
session_defaults = {
    'attendees': [],
    'attendance_log': [],
    'scanned': set(),
    'phones': {},
    'schools': {},
    'kakao_log': [],
    'flask_connected': False,
    'current_tab': 'home',
    'use_offline_mode': False  # 🆕 오프라인 모드
}

for key, default in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default


def check_flask_connection():
    """Flask 서버 연결 상태 확인"""
    try:
        response = requests.get(f"http://localhost:{FLASK_PORT}/status", timeout=2)
        if response.status_code == 200:
            st.session_state['flask_connected'] = True
            st.session_state['use_offline_mode'] = False
            return True
    except Exception as e:
        st.session_state['flask_connected'] = False
        logger.debug(f"Flask server not reachable: {e}")
    
    return False


def load_students_to_session():
    """CSV에서 학생 정보를 세션으로 로드"""
    df = load_csv_safe(STUDENTS_CSV, ['name', 'qr_code', 'phone', 'school'])
    st.session_state.attendees = df['name'].tolist()
    st.session_state.phones = dict(zip(df['name'], df['phone'].fillna('')))
    st.session_state.schools = dict(zip(df['name'], df.get('school', pd.Series()).fillna('')))


def save_students_from_session():
    """세션의 학생 정보를 CSV로 저장"""
    df = pd.DataFrame([
        {
            "name": name,
            "qr_code": name,
            "phone": st.session_state.phones.get(name, ""),
            "school": st.session_state.schools.get(name, "")
        }
        for name in st.session_state.attendees
    ])
    return save_csv_safe(df, STUDENTS_CSV)


def load_attendance_from_csv():
    """
    🆕 CSV에서 직접 출석 데이터 로드 (Flask 독립)
    
    Returns:
        DataFrame: 출석 기록
    """
    try:
        if os.path.exists(ATTENDANCE_LOG_CSV):
            df = pd.read_csv(ATTENDANCE_LOG_CSV, encoding='utf-8-sig')
            
            # 컬럼명 정규화
            column_mapping = {
                'name': 'student_name',
                'student': 'student_name',
                'code': 'qr_code',
                'qr': 'qr_code',
                'time': 'timestamp'
            }
            df = df.rename(columns=column_mapping)
            
            # 필수 컬럼 확인
            if 'student_name' not in df.columns:
                if 'qr_code' in df.columns:
                    df['student_name'] = df['qr_code']
                else:
                    logger.warning("No student name column found")
                    return pd.DataFrame()
            
            # 날짜 변환
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date']).dt.date
            elif 'timestamp' in df.columns:
                df['date'] = pd.to_datetime(df['timestamp']).dt.date
            
            # 상태 기본값
            if 'status' not in df.columns:
                df['status'] = '출석'
            
            return df
        else:
            logger.info(f"Attendance log not found: {ATTENDANCE_LOG_CSV}")
            return pd.DataFrame()
    
    except Exception as e:
        logger.error(f"Error loading attendance from CSV: {e}")
        return pd.DataFrame()


def get_today_attendance_count():
    """
    🆕 오늘 출석 인원 카운트 (Flask 독립)
    
    Returns:
        int: 오늘 출석 인원
    """
    df = load_attendance_from_csv()
    
    if df.empty:
        return 0
    
    try:
        today_records = df[df['date'] == date_today]
        return len(today_records)
    except:
        return 0


def show_status_badge():
    """서버 연결 상태 뱃지"""
    if st.session_state['flask_connected']:
        st.success("🟢 서버 연결됨", icon="✅")
    else:
        st.info("📴 오프라인 모드", icon="ℹ️")


# 초기 로드
if not st.session_state.attendees:
    load_students_to_session()

# 헤더
col1, col2 = st.columns([3, 1])
with col1:
    st.title("📱 로보그램 QR출석")
with col2:
    if st.button("🔄", help="새로고침", key="mobile_auto_378"):
        check_flask_connection()
        st.rerun()

# 네비게이션 탭 (모바일 친화적)
tab = st.radio(
    "메뉴",
    ["🏠 홈", "👥 학생", "📅 일정", "👨‍👩‍👧 보호자", "🔹 출석", "📊 리포트"],
    horizontal=True,
    label_visibility="collapsed"
, key="mobile_auto_383")

st.markdown("---")

# ============================================================================
# 🏠 홈 대시보드
# ============================================================================
if tab == "🏠 홈":
    st.header("📊 대시보드")
    
    # 오늘 일정 표시
    df_schedule = load_csv_safe(SCHEDULE_CSV, ['date', 'start', 'end', 'session'])
    df_schedule['date'] = pd.to_datetime(df_schedule['date']).dt.date
    today_sched = df_schedule[df_schedule['date'] == date_today]
    
    if not today_sched.empty:
        row = today_sched.iloc[0]
        st.markdown(f"""
        <div class="schedule-card">
            <h3 style="color: white; margin: 0;">📅 오늘의 수업</h3>
            <p style="font-size: 24px; font-weight: bold; margin: 10px 0;">
                {row['start']} ~ {row['end']}
            </p>
            <p style="margin: 0;">{row['session']}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("🔭 오늘 예정된 수업이 없습니다.")
    
    st.markdown("###")
    
    # 통계 카드
    col1, col2, col3 = st.columns(3)
    
    total_students = len(st.session_state.attendees)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">전체 학생</div>
            <div class="stat-number">{total_students}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # 🆕 Flask 없이도 출석 수 표시
        today_attendance = get_today_attendance_count()
        
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">오늘 출석</div>
            <div class="stat-number" style="color: #4CAF50;">{today_attendance}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        absent = total_students - today_attendance if total_students > 0 else 0
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">미출석</div>
            <div class="stat-number" style="color: #ff6b6b;">{absent}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("###")
    
    # 빠른 액션
    st.subheader("⚡ 빠른 실행")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔹 출석 시작", key="quick_attendance", use_container_width=True):
            st.session_state['current_tab'] = '🔹 출석'
            st.rerun()
    
    with col2:
        if st.button("📊 리포트 보기", key="quick_report", use_container_width=True):
            st.session_state['current_tab'] = '📊 리포트'
            st.rerun()
    
    # 🆕 최근 출석 기록 미리보기 (Flask 독립)
    st.markdown("###")
    st.subheader("📋 최근 출석 기록")
    
    df_attendance = load_attendance_from_csv()
    
    if not df_attendance.empty:
        # 오늘 기록만 필터
        today_records = df_attendance[df_attendance['date'] == date_today]
        
        if not today_records.empty:
            # 최근 5개만
            df_preview = today_records.tail(5).copy()
            
            # 시간 포맷팅
            if 'timestamp' in df_preview.columns:
                df_preview['시간'] = pd.to_datetime(df_preview['timestamp']).dt.strftime('%H:%M')
            else:
                df_preview['시간'] = '-'
            
            # 표시할 컬럼 선택
            display_cols = []
            if 'student_name' in df_preview.columns:
                display_cols.append('student_name')
            if '시간' in df_preview.columns:
                display_cols.append('시간')
            if 'status' in df_preview.columns:
                display_cols.append('status')
            
            if display_cols:
                df_preview = df_preview[display_cols].rename(columns={
                    'student_name': '학생',
                    'status': '상태'
                })
                
                st.dataframe(
                    df_preview,
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.info("오늘은 아직 출석 기록이 없습니다.")
    else:
        st.info("아직 출석 기록이 없습니다.")
    
    # 🆕 오프라인 모드 안내
    if not st.session_state['flask_connected']:
        with st.expander("ℹ️ 오프라인 모드 안내"):
            st.info("""
            **현재 오프라인 모드로 작동 중입니다.**
            
            ✅ **사용 가능한 기능:**
            - 학생 관리
            - 일정 관리
            - 보호자 관리
            - 리포트 조회 (CSV 기반)
            
            ⚠️ **제한된 기능:**
            - 실시간 QR 출석 체크 (Flask 필요)
            - 카메라 스트리밍
            
            💡 **Flask 서버 실행 방법:**
            ```bash
            python flask_qr_attendance_app.py
            ```
            """)


# ============================================================================
# 👥 학생 관리
# ============================================================================
elif tab == "👥 학생":
    st.header("👥 학생 관리")
    
    # 학생 추가
    with st.expander("➕ 새 학생 추가", expanded=False):
        add_method = st.radio("추가 방법", ["직접 입력", "CSV 업로드"], horizontal=True, key="mobile_auto_544")
        
        if add_method == "직접 입력":
            new_name = st.text_input("학생명", placeholder="홍길동", key="mobile_auto_547")
            new_phone = st.text_input("전화번호 (선택)", placeholder="010-1234-5678", key="mobile_auto_548")
            new_school = st.text_input("학교명 (선택)", placeholder="서울초등학교", key="mobile_auto_549")
            
            if st.button("➕ 학생 추가", use_container_width=True, key="mobile_auto_551"):
                if new_name:
                    if new_name not in st.session_state.attendees:
                        st.session_state.attendees.append(new_name)
                        st.session_state.phones[new_name] = new_phone
                        st.session_state.schools[new_name] = new_school
                        if save_students_from_session():
                            st.success(f"✅ {new_name} 학생이 추가되었습니다!")
                            st.rerun()
                    else:
                        st.warning("이미 등록된 학생입니다.")
                else:
                    st.error("학생명을 입력해주세요.")
        
        else:
            uploaded_file = st.file_uploader("CSV 파일 업로드", type=['csv'], key="mobile_auto_566")
            if uploaded_file:
                try:
                    df_upload = pd.read_csv(uploaded_file)
                    new_names = df_upload.iloc[:, 0].astype(str).tolist()
                    added = 0
                    
                    for name in new_names:
                        name = name.strip()
                        if name and name not in st.session_state.attendees:
                            st.session_state.attendees.append(name)
                            st.session_state.phones[name] = ''
                            st.session_state.schools[name] = ''
                            added += 1
                    
                    if added > 0:
                        save_students_from_session()
                        st.success(f"✅ {added}명의 학생이 추가되었습니다!")
                        st.rerun()
                except Exception as e:
                    st.error(f"CSV 파일 처리 오류: {e}")
    
    st.markdown("###")
    
    # 학생 목록 (카드 형식)
    st.subheader(f"📋 전체 학생 ({len(st.session_state.attendees)}명)")
    
    if st.session_state.attendees:
        for idx, name in enumerate(st.session_state.attendees):
            phone = st.session_state.phones.get(name, '')
            school = st.session_state.schools.get(name, '')
            
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    school_display = f" | 🏫 {school}" if school else ""
                    st.markdown(f"""
                    <div class="student-card">
                        <h3 style="margin: 0 0 5px 0;">{name}</h3>
                        <p style="margin: 0; color: #666; font-size: 14px;">
                            📞 {phone if phone else '전화번호 없음'}{school_display}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    # QR 다운로드
                    buf = io.BytesIO()
                    qrcode.make(name).save(buf, 'PNG')
                    buf.seek(0)
                    st.download_button(
                        "📱 QR",
                        buf.getvalue(),
                        file_name=f"{name}_QR.png",
                        mime='image/png',
                        key=f"qr_{idx}",
                        use_container_width=True
                    )
                
                with col3:
                    # 삭제 버튼
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
        
        # 전체 QR ZIP 다운로드
        if st.button("📦 전체 QR ZIP 다운로드", use_container_width=True, key="mobile_auto_641"):
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
                    file_name=f"QR_Codes_{date_today}.zip",
                    mime='application/zip',
                    use_container_width=True
                , key="mobile_auto_651")
    else:
        st.info("등록된 학생이 없습니다. 새 학생을 추가해주세요.")


# ============================================================================
# 📅 일정 관리
# ============================================================================
elif tab == "📅 일정":
    st.header("📅 일정 관리")
    
    df_sched = load_csv_safe(SCHEDULE_CSV, ['date', 'start', 'end', 'session'])
    df_sched['date'] = pd.to_datetime(df_sched['date']).dt.date
    
    # 새 일정 추가
    with st.expander("➕ 새 일정 추가", expanded=False):
        new_date = st.date_input("📅 날짜", date_today, key="mobile_auto_673")
        
        col1, col2 = st.columns(2)
        with col1:
            new_start = st.time_input("🕐 시작", time(9, 0), key="mobile_auto_677")
        with col2:
            new_end = st.time_input("🕐 종료", time(10, 0), key="mobile_auto_679")
        
        new_sess = st.text_input("📚 회차명", "1회차", key="mobile_auto_681")
        
        if st.button("💾 일정 저장", use_container_width=True, key="mobile_auto_683"):
            new_row = pd.DataFrame([{
                'date': new_date,
                'start': new_start.strftime('%H:%M'),
                'end': new_end.strftime('%H:%M'),
                'session': new_sess
            }])
            df_sched = pd.concat([df_sched, new_row], ignore_index=True)
            
            if save_csv_safe(df_sched, SCHEDULE_CSV):
                st.success("✅ 일정이 저장되었습니다!")
                st.rerun()
    
    st.markdown("###")
    
    # 일정 목록
    st.subheader("📋 예정된 일정")
    
    if not df_sched.empty:
        # 날짜순 정렬
        df_sched_sorted = df_sched.sort_values('date', ascending=False)
        
        for idx, row in df_sched_sorted.iterrows():
            is_today = row['date'] == date_today
            
            col1, col2 = st.columns([4, 1])
            
            with col1:
                bg_color = "#e8f5e9" if is_today else "#f5f5f5"
                st.markdown(f"""
                <div style="background: {bg_color}; padding: 15px; border-radius: 10px; 
                            margin: 5px 0; border-left: 4px solid {'#4CAF50' if is_today else '#ccc'};">
                    <div style="font-weight: bold; font-size: 16px;">
                        {row['date']} {'🔴 오늘' if is_today else ''}
                    </div>
                    <div style="color: #666; margin: 5px 0;">
                        ⏰ {row['start']} ~ {row['end']}
                    </div>
                    <div style="color: #333;">
                        📚 {row['session']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                if st.button("🗑️", key=f"del_sched_{idx}", help="삭제", use_container_width=True):
                    df_sched.drop(idx, inplace=True)
                    df_sched.reset_index(drop=True, inplace=True)
                    if save_csv_safe(df_sched, SCHEDULE_CSV):
                        st.success("일정이 삭제되었습니다.")
                        st.rerun()
    else:
        st.info("등록된 일정이 없습니다.")


# ============================================================================
# 👨‍👩‍👧 보호자 관리
# ============================================================================
elif tab == "👨‍👩‍👧 보호자":
    st.header("👨‍👩‍👧‍👦 보호자 관리")
    
    df_parents = load_csv_safe(PARENTS_CSV, ['student', 'parent_name', 'phone'])
    
    # 새 보호자 추가
    with st.expander("➕ 새 보호자 추가", expanded=False):
        p_student = st.selectbox("👤 학생 선택", st.session_state.attendees, key="mobile_auto_748") if st.session_state.attendees else st.text_input("👤 학생명", key="mobile_auto_748")
        p_name = st.text_input("👨‍👩‍👧 보호자명", key="mobile_auto_749")
        p_phone = st.text_input("📞 전화번호", key="mobile_auto_750")
        
        if st.button("➕ 보호자 추가", use_container_width=True, key="mobile_auto_752"):
            if p_student and p_name and p_phone:
                new_parent = pd.DataFrame([{
                    'student': p_student,
                    'parent_name': p_name,
                    'phone': p_phone
                }])
                df_parents = pd.concat([df_parents, new_parent], ignore_index=True)
                
                if save_csv_safe(df_parents, PARENTS_CSV):
                    st.success("✅ 보호자가 추가되었습니다!")
                    st.rerun()
            else:
                st.error("모든 정보를 입력해주세요.")
    
    st.markdown("###")
    
    # 보호자 목록
    st.subheader("📋 보호자 목록")
    
    if not df_parents.empty:
        for idx, row in df_parents.iterrows():
            col1, col2 = st.columns([4, 1])
            
            with col1:
                st.markdown(f"""
                <div class="student-card">
                    <div style="font-weight: bold; font-size: 16px; margin-bottom: 5px;">
                        👤 {row['student']}
                    </div>
                    <div style="color: #666; font-size: 14px;">
                        👨‍👩‍👧 {row['parent_name']} | 📞 {row['phone']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                if st.button("🗑️", key=f"del_parent_{idx}", help="삭제", use_container_width=True):
                    df_parents.drop(idx, inplace=True)
                    df_parents.reset_index(drop=True, inplace=True)
                    if save_csv_safe(df_parents, PARENTS_CSV):
                        st.success("보호자가 삭제되었습니다.")
                        st.rerun()
    else:
        st.info("등록된 보호자가 없습니다.")


# ============================================================================
# 🔹 QR 출석
# ============================================================================
elif tab == "🔹 출석":
    st.header("🔹 QR 출석")
    
    # Flask 서버 연결 확인
    flask_available = check_flask_connection()
    
    if not flask_available:
        st.warning("⚠️ Flask 서버에 연결할 수 없습니다.")
        st.info("📱 실시간 QR 출석 체크는 Flask 서버가 필요합니다.")
        
        with st.expander("📖 Flask 앱 실행 방법"):
            st.code("python flask_qr_attendance_app.py", language="bash")
            
        st.markdown("###")
        st.info("""
        **대안 방법:**
        1. 수동으로 출석 체크
        2. 모바일 카메라로 QR 촬영 후 업로드
        3. 나중에 CSV 파일로 일괄 처리
        """)
    else:
        st.success("✅ Flask 서버 연결 완료")
        
        stream_url = f"http://127.0.0.1:{FLASK_PORT}/video_feed"
        
        # 모바일 최적화 스트림
        html_code = f"""
        <div style="text-align:center; padding:10px;">
            <img src="{stream_url}"
                 style="width:100%; max-width:100%; height:auto; 
                        border:3px solid #4CAF50; border-radius:15px;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.15);"
                 alt="QR 출석 스트림"/>
        </div>
        """
        
        components.html(html_code, height=900, scrolling=False)
        
        # 실시간 통계
        st.markdown("###")
        
        col1, col2, col3 = st.columns(3)
        
        try:
            response = requests.get(f"http://localhost:{FLASK_PORT}/status", timeout=2)
            if response.status_code == 200:
                status_data = response.json()
                
                with col1:
                    st.metric("📊 총 출석", status_data.get('total_scanned', 0))
                
                with col2:
                    st.metric("📝 기록수", status_data.get('total_records', 0))
                
                with col3:
                    available = "가능" if status_data.get('attendance_available', False) else "불가"
                    st.metric("🎯 출석 상태", available)
        except Exception as e:
            st.warning(f"통계 정보를 불러올 수 없습니다: {e}")


# ============================================================================
# 📊 리포트 (Flask 독립 버전)
# ============================================================================
elif tab == "📊 리포트":
    st.header("📊 출석 리포트")
    
    # 🆕 CSV에서 직접 데이터 로드 (Flask 독립)
    df_attendance = load_attendance_from_csv()
    
    if df_attendance.empty:
        st.info("🔭 아직 출석 기록이 없습니다.")
        st.info("💡 출석 체크를 시작하면 여기에 리포트가 표시됩니다.")
    else:
        # 필터 옵션
        st.markdown("### 🔍 필터")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            available_dates = sorted(df_attendance['date'].unique(), reverse=True)
            date_options = ["전체"] + [str(d) for d in available_dates]
            selected_date = st.selectbox("📅 날짜", date_options, key="mobile_auto_884")
        
        with col2:
            if 'session' in df_attendance.columns:
                sessions = ["전체"] + sorted(df_attendance['session'].unique().tolist())
                selected_session = st.selectbox("📚 수업", sessions, key="mobile_auto_889")
            else:
                selected_session = "전체"
        
        with col3:
            status_options = ["전체", "출석", "지각", "결석"]
            selected_status = st.selectbox("📊 상태", status_options, key="mobile_auto_895")
        
        # 필터 적용
        df_filtered = df_attendance.copy()
        
        if selected_date != "전체":
            df_filtered = df_filtered[df_filtered['date'] == pd.to_datetime(selected_date).date()]
        
        if selected_session != "전체" and 'session' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['session'] == selected_session]
        
        if selected_status != "전체":
            df_filtered = df_filtered[df_filtered['status'] == selected_status]
        
        st.markdown("---")
        
        if not df_filtered.empty:
            # 통계 카드
            st.markdown("### 📈 출결 현황")
            
            status_counts = df_filtered['status'].value_counts()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-label">✅ 출석</div>
                    <div class="stat-number" style="color: #4CAF50;">
                        {status_counts.get('출석', 0)}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-label">⏰ 지각</div>
                    <div class="stat-number" style="color: #FFA726;">
                        {status_counts.get('지각', 0)}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-label">❌ 결석</div>
                    <div class="stat-number" style="color: #EF5350;">
                        {status_counts.get('결석', 0)}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("###")
            
            # 전체 출석 로그
            st.subheader("📋 전체 출석 기록")
            
            # 표시할 컬럼 선택
            display_cols = []
            if 'student_name' in df_filtered.columns:
                display_cols.append('student_name')
            if 'session' in df_filtered.columns and selected_session == "전체":
                display_cols.append('session')
            if 'timestamp' in df_filtered.columns:
                df_filtered['시간'] = pd.to_datetime(df_filtered['timestamp']).dt.strftime('%H:%M:%S')
                display_cols.append('시간')
            if 'status' in df_filtered.columns:
                display_cols.append('status')
            
            if display_cols:
                df_display = df_filtered[display_cols].copy()
                
                # 컬럼명 한글화
                df_display = df_display.rename(columns={
                    'student_name': '학생',
                    'session': '수업',
                    'status': '상태'
                })
                
                st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # CSV 다운로드
            st.markdown("###")
            st.download_button(
                "📥 CSV 다운로드",
                df_display.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'),
                file_name=f"attendance_{date_today}.csv",
                mime="text/csv",
                use_container_width=True
            , key="mobile_auto_980")
        else:
            st.warning("⚠️ 선택한 조건에 해당하는 기록이 없습니다.")

# 푸터
st.markdown("---")
st.caption("© 2025 로보그램 QR 전자출석시스템 v3.0 (Flask 독립) | PWA 지원")

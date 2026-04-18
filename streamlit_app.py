"""
메인 앱 - 역할별 라우팅 (완전 통합)
로그인 후 각 역할별 완성된 앱으로 자동 연결
"""
import streamlit as st
from auth import authenticate_user, get_role_display_name
import os
import sys

# 세션 초기화
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if 'user' not in st.session_state:
    st.session_state.user = None

# [핵심] 전역 UI 가독성 CSS 강제 주입 (모든 포털에 적용)
st.markdown("""
<style>
    /* 모든 가용 입력창에 대해 배경 흰색, 글자 검정색 강제 고정 */
    input[type="text"], input[type="password"], [data-baseweb="input"] {
        background-color: #ffffff !important;
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
    }
    div[data-testid="stTextInput"] div[data-baseweb="input"] {
        background-color: #ffffff !important;
        border: 2px solid #e1e1e1 !important;
    }
</style>
""", unsafe_allow_html=True)


# 메인 로직
# 1. URL 파라미터 또는 환경 변수에 따른 포털 전환 확인
query_params = st.query_params
p_param = query_params.get("p", "").lower()
app_type = p_param or os.getenv('APP_TYPE', '').lower()

if app_type == 'staff':
    for mod in ["utils", "staff_portal"]:
        if mod in sys.modules:
            del sys.modules[mod]
    import staff_portal
    staff_portal.main()
    st.stop()
elif app_type == 'user':
    for mod in ["utils", "user_portal"]:
        if mod in sys.modules:
            del sys.modules[mod]
    import user_portal
    user_portal.main()
    st.stop()

# 2. 통합 모드 - 페이지 설정
st.set_page_config(
    page_title="온라인아카데미 QR출석",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def show_login_page():
    """로그인 페이지 - 프리미엄 한국어 UI (통합 메인)"""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap');
        * { font-family: 'Noto Sans KR', sans-serif !important; }
        
        .stApp {
            background: linear-gradient(160deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            min-height: 100vh;
        }
        
        .main .block-container {
            padding-top: 2rem;
            max-width: 480px;
        }

        .glass-card {
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border-radius: 28px;
            border: 1px solid rgba(255, 255, 255, 0.12);
            padding: 40px;
            box-shadow: 0 32px 64px -12px rgba(0, 0, 0, 0.6);
        }
        
        .brand-name {
            font-size: 32px;
            font-weight: 900;
            background: linear-gradient(135deg, #ffffff 0%, #c084fc 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            margin-top: 10px;
        }
        
        label { color: rgba(255, 255, 255, 0.8) !important; font-weight: 600 !important; }

        .stFormSubmitButton > button {
            background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 14px !important;
            height: 50px !important;
            font-weight: 700 !important;
            width: 100% !important;
            box-shadow: 0 8px 24px rgba(124, 58, 237, 0.4) !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    _, col_center, _ = st.columns([1, 6, 1])
    
    with col_center:
        st.markdown('<div style="text-align:center; margin-bottom:10px;">', unsafe_allow_html=True)
        st.image("static/mascot_small.png", width=140)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="brand-name">ROBOGRAM</div>', unsafe_allow_html=True)
        st.markdown('<div style="color:rgba(255,255,255,0.5); text-align:center; margin-bottom:30px; font-size:14px; letter-spacing:1px;">Smart Attendance System</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("아이디", placeholder="아이디를 입력하세요")
            password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요")
            submit = st.form_submit_button("🚀 로그인", use_container_width=True)
            
            if submit:
                user = authenticate_user(username, password)
                if user:
                    st.session_state.user = user
                    st.session_state.authenticated = True
                    st.success(f"✅ 인증 완료! 잠시만 기다려 주세요...")
                    st.rerun()
                else:
                    st.error("❌ 정보가 올바르지 않습니다.")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("""
        <div style="text-align:center; margin-top:25px;">
            <span style="color:rgba(255,255,255,0.3); font-size:11px;">v1.2.5 Final Recovery Package</span>
        </div>
        """, unsafe_allow_html=True)


def show_admin_app():
    """관리자 앱 안내"""
    user = st.session_state.user
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #0f0c29 0%, #302b63 100%); 
                color: white; padding: 30px; border-radius: 20px; text-align: center; margin-bottom: 20px;">
        <h1>👨‍💼 관리자 대시보드</h1>
        <p style="font-size: 18px;">환영합니다, <b>{user['name']}</b>님!</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.success("✅ 관리자 권한으로 로그인되었습니다.")
    
    st.markdown("## 🚀 관리자 앱 실행 방법")
    st.info("관리자 앱은 복잡한 기능이 많아 독립 실행을 권장합니다.")
    st.code("streamlit run admin_app.py --server.port 8502", language="bash")
    st.markdown("그 후 브라우저에서: http://localhost:8502")
    
    st.markdown("---")
    st.markdown("## 📋 관리자 주요 기능")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        ### 학생 관리
        - 학생 추가/삭제/수정
        - QR 코드 생성
        - 전체 QR ZIP 다운로드
        
        ### 일정 관리
        - 수업 일정 등록 / 수정 / 삭제

        ### 보호자 관리
        - 보호자 정보 등록 / 학생 연결
        """)
    with col2:
        st.markdown("""
        ### 사용자 관리
        - 계정 생성/삭제 / 역할 설정
        
        ### 출석 체크
        - Flask 카메라 연동
        - 실시간 출석 현황
        
        ### 리포트
        - 출석률 통계 / CSV 다운로드
        """)


def show_teacher_app():
    """선생님 앱 - teacher_app.py 임포트"""
    try:
        import teacher_app
        teacher_app.main()
    except Exception as e:
        st.error(f"선생님 앱 로드 오류: {e}")


def show_parent_app():
    """학부모 앱 - parent_app.py 임포트"""
    try:
        import parent_app
        parent_app.main()
    except Exception as e:
        st.error(f"학부모 앱 로드 오류: {e}")


def show_student_app():
    """학생 앱 - student_app.py 임포트"""
    try:
        import student_app
        student_app.main()
    except Exception as e:
        st.error(f"학생 앱 로드 오류: {e}")


def show_logout_section():
    """로그아웃 섹션"""
    st.sidebar.markdown("---")
    
    user = st.session_state.user
    st.sidebar.info(f"""
    **로그인 정보**  
    👤 {user['name']}  
    🎭 {get_role_display_name(user['role'])}
    """)
    
    if st.sidebar.button("🚪 로그아웃", use_container_width=True, key="sidebar_logout_btn"):
        st.session_state.authenticated = False
        st.session_state.user = None
        st.rerun()


# 3. 통합 로그인 처리
if not st.session_state.authenticated or not st.session_state.user:
    # 로그인 페이지
    show_login_page()
else:
    # 역할별 앱 라우팅
    user = st.session_state.user
    role = user.get('role')
    
    # 사이드바에 로그아웃 버튼
    show_logout_section()
    
    # 역할별 앱 표시
    if role == 'admin':
        show_admin_app()
    elif role == 'teacher':
        # 최신 코드 반영을 위해 모듈 캐시 삭제
        for mod in ["utils", "teacher_app"]:
            if mod in sys.modules:
                del sys.modules[mod]
        show_teacher_app()
    elif role == 'parent':
        for mod in ["utils", "parent_app"]:
            if mod in sys.modules:
                del sys.modules[mod]
        show_parent_app()
    elif role == 'student':
        for mod in ["utils", "student_app"]:
            if mod in sys.modules:
                del sys.modules[mod]
        show_student_app()
    else:
        st.error("알 수 없는 사용자 역할입니다.")
        if st.button("🚪 로그아웃", key="error_logout_btn"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()

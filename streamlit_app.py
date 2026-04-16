"""
메인 앱 - 역할별 라우팅 (완전 통합)
로그인 후 각 역할별 완성된 앱으로 자동 연결
"""
import streamlit as st
from auth import authenticate_user, get_role_display_name
import os

# 세션 초기화
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if 'user' not in st.session_state:
    st.session_state.user = None

# 메인 로직
# 1. 환경 변수(APP_TYPE)에 따른 강제 포털 전환 확인 (set_page_config 이전에 실행)
app_type = os.getenv('APP_TYPE', '').lower()

if app_type == 'staff':
    import staff_portal
    staff_portal.main()
    st.stop()
elif app_type == 'user':
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
    """로그인 페이지 - 프리미엄 UI 업그레이드"""
    st.markdown("""
    <style>
        /* 배경 그라데이션 및 애니메이션 */
        .stApp {
            background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e1b4b 100%);
            background-size: 400% 400%;
            animation: gradient 15s ease infinite;
        }
        @keyframes gradient {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        /* 글래스모피즘 컨테이너 */
        .login-card {
            background: rgba(255, 255, 255, 0.07);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-radius: 24px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 40px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            max-width: 480px;
            margin: auto;
            color: white;
        }

        /* 텍스트 스타일 */
        .logo-text {
            font-size: 32px;
            font-weight: 800;
            background: linear-gradient(to right, #fff, #a5b4fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-top: 10px;
            letter-spacing: -1px;
        }
        .logo-subtext {
            color: rgba(255, 255, 255, 0.6);
            font-size: 16px;
            margin-bottom: 30px;
        }

        /* 입력 필드 스타일 커스텀 */
        div[data-baseweb="input"] {
            background-color: rgba(255, 255, 255, 0.05) !important;
            border-radius: 12px !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            color: white !important;
        }
        input {
            color: white !important;
        }
        label {
            color: rgba(255, 255, 255, 0.8) !important;
            font-weight: 500 !important;
        }

        /* 버튼 프리미엄 스타일 */
        .stButton > button {
            background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
            color: white;
            border: none;
            border-radius: 12px;
            padding: 12px 24px;
            font-size: 18px;
            font-weight: 700;
            width: 100%;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.3);
            margin-top: 10px;
        }
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 20px 25px -5px rgba(99, 102, 241, 0.4);
            background: linear-gradient(135deg, #4f46e5 0%, #9333ea 100%);
        }
        
        /* 테스트 계정 안내 익스팬더 디자인 */
        .stExpander {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            margin-top: 20px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # 레이아웃 구성
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # 로고 표시 부분
        try:
            st.markdown(f'''<div style="text-align: center;"><img src="data:image/png;base64,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" width="120"></div>''', unsafe_allow_html=True)
        except:
            st.markdown("<div style='font-size: 70px; text-align: center;'>🎓</div>", unsafe_allow_html=True)
            
        st.markdown("""
        <div style='text-align: center;'>
            <div class="logo-text">ROBOGRAM ACADEMY</div>
            <div class="logo-subtext">QR Smart Attendance System</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 로그인 폼
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your ID")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            submit = st.form_submit_button("Sign In")
            
            if submit:
                if not username or not password:
                    st.warning("Please enter your credentials.")
                else:
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state.user = user
                        st.session_state.authenticated = True
                        st.success(f"Welcome back, {user['name']}!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Please try again.")
        
        with st.expander("🔐 Test Accounts Access"):
            st.markdown("""
            <div style='font-size: 14px; color: rgba(255,255,255,0.7);'>
            <b>Admin:</b> admin / admin123<br>
            <b>Teacher:</b> teacher1 / teacher123<br>
            <b>Parent:</b> parent1 / parent123<br>
            <b>Student:</b> student1 / student123
            </div>
            """, unsafe_allow_html=True)


def show_admin_app():
    """관리자 앱 안내"""
    user = st.session_state.user
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; padding: 30px; border-radius: 15px; text-align: center;">
        <h1>👨‍💼 관리자 대시보드</h1>
        <p style="font-size: 18px;">환영합니다, {user['name']}님!</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("###")
    
    st.success("✅ 관리자 권한으로 로그인되었습니다.")
    
    # 실행 방법 안내
    st.markdown("## 🚀 관리자 앱 실행 방법")
    
    st.info("""
    **방법 1: 새 터미널에서 실행 (권장)**
    
    관리자 앱은 복잡한 기능이 많아 독립 실행을 권장합니다.
    """)
    
    st.code("streamlit run admin_app.py --server.port 8502", language="bash")
    
    st.markdown("그 후 브라우저에서: http://localhost:8502")
    
    st.markdown("---")
    
    # 주요 기능 안내
    st.markdown("## 📋 관리자 주요 기능")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 학생 관리
        - 학생 추가/삭제/수정
        - QR 코드 생성
        - 전체 QR ZIP 다운로드
        
        ### 일정 관리
        - 수업 일정 등록
        - 일정 수정/삭제
        
        ### 보호자 관리
        - 보호자 정보 등록
        - 학생 연결
        """)
    
    with col2:
        st.markdown("""
        ### 사용자 관리
        - 계정 생성/삭제
        - 역할 설정
        - 권한 관리
        
        ### 출석 체크
        - Flask 카메라 연동
        - 실시간 출석 현황
        
        ### 리포트
        - 출석률 통계
        - CSV 다운로드
        """)
    
    st.markdown("---")
    
    # 빠른 시작 가이드
    with st.expander("📖 빠른 시작 가이드"):
        st.markdown("""
        ### 1단계: Flask 서버 실행
        ```bash
        python flask_qr_attendance_app.py
        ```
        
        ### 2단계: 관리자 앱 실행
        ```bash
        streamlit run admin_app.py --server.port 8502
        ```
        
        ### 3단계: 로그인
        - 이미 로그인되어 있으므로 바로 사용 가능!
        - 또는 admin / admin123로 재로그인
        
        ### 4단계: 기능 사용
        - 홈: 대시보드 확인
        - 학생: 학생 관리
        - 일정: 수업 일정 관리
        - 출석: QR 출석 체크
        - 리포트: 통계 확인
        """)


def show_teacher_app():
    """선생님 앱 - teacher_app.py 임포트"""
    try:
        import teacher_app
        teacher_app.main()
    except Exception as e:
        st.error(f"선생님 앱 로드 오류: {e}")
        st.info("teacher_app.py 파일이 필요합니다.")


def show_parent_app():
    """학부모 앱 - parent_app.py 임포트"""
    try:
        import parent_app
        parent_app.main()
    except Exception as e:
        st.error(f"학부모 앱 로드 오류: {e}")
        st.info("parent_app.py 파일이 필요합니다.")


def show_student_app():
    """학생 앱 - student_app.py 임포트"""
    try:
        import student_app
        student_app.main()
    except Exception as e:
        st.error(f"학생 앱 로드 오류: {e}")
        st.info("student_app.py 파일이 필요합니다.")


def show_logout_section():
    """로그아웃 섹션"""
    st.sidebar.markdown("---")
    
    user = st.session_state.user
    st.sidebar.info(f"""
    **로그인 정보**  
    👤 {user['name']}  
    🎭 {get_role_display_name(user['role'])}
    """)
    
    if st.sidebar.button("🚪 로그아웃", use_container_width=True):
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
        show_teacher_app()
    elif role == 'parent':
        show_parent_app()
    elif role == 'student':
        show_student_app()
    else:
        st.error("알 수 없는 사용자 역할입니다.")
        if st.button("🚪 로그아웃"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()

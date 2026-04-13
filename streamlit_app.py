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
    """로그인 페이지"""
    st.markdown("""
    <style>
        .main {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .login-container {
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            max-width: 450px;
            margin: 100px auto;
        }
        .logo {
            text-align: center;
            margin-bottom: 30px;
        }
        .logo-icon {
            font-size: 70px;
        }
        .logo-text {
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }
        .logo-subtext {
            color: #666;
            font-size: 16px;
        }
        .stButton > button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            padding: 15px;
            font-size: 18px;
            font-weight: bold;
            width: 100%;
            margin-top: 20px;
        }
        .stTextInput > div > div > input {
            border-radius: 10px;
            border: 2px solid #e0e0e0;
            padding: 12px;
            font-size: 16px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div class="logo">
            <div class="logo-icon">🎓</div>
            <div class="logo-text">온라인아카데미</div>
            <div class="logo-subtext">QR 전자출석 시스템</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("###")
        
        with st.form("login_form"):
            username = st.text_input("아이디", placeholder="아이디를 입력하세요")
            password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요")
            
            submit = st.form_submit_button("🔐 로그인")
            
            if submit:
                if not username or not password:
                    st.error("아이디와 비밀번호를 입력해주세요.")
                else:
                    user = authenticate_user(username, password)
                    
                    if user:
                        st.session_state.user = user
                        st.session_state.authenticated = True
                        st.success(f"환영합니다, {user['name']}님!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ 아이디 또는 비밀번호가 올바르지 않습니다.")
        
        with st.expander("🔍 테스트 계정"):
            st.info("""
            **👨‍💼 관리자**  
            아이디: `admin` / 비밀번호: `admin123`
            
            **👩‍🏫 선생님**  
            아이디: `teacher1` / 비밀번호: `teacher123`
            
            **👨‍👩‍👧 학부모**  
            아이디: `parent1` / 비밀번호: `parent123`
            
            **🧒 학생**  
            아이디: `student1` / 비밀번호: `student123`
            """)


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

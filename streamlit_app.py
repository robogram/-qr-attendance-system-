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
    """로그인 페이지 - 프리미엄 한국어 UI"""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap');
        
        * { font-family: 'Noto Sans KR', sans-serif !important; }
        
        /* 전체 배경 */
        .stApp {
            background: linear-gradient(160deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            min-height: 100vh;
        }
        
        /* 메인 컨테이너 패딩 제거 */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        /* 글래스모피즘 카드 */
        .glass-card {
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border-radius: 28px;
            border: 1px solid rgba(255, 255, 255, 0.12);
            padding: 48px 40px;
            box-shadow: 0 32px 64px -12px rgba(0, 0, 0, 0.6),
                        inset 0 1px 0 rgba(255,255,255,0.1);
        }
        
        .brand-name {
            font-size: 36px;
            font-weight: 900;
            background: linear-gradient(135deg, #ffffff 0%, #c084fc 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            letter-spacing: -1.5px;
            margin: 0;
        }
        
        .brand-subtitle {
            font-size: 14px;
            color: rgba(255, 255, 255, 0.55);
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-top: 4px;
        }
        
        .section-title {
            font-size: 22px;
            font-weight: 700;
            color: white;
            margin-bottom: 4px;
        }
        
        .section-desc {
            font-size: 14px;
            color: rgba(255,255,255,0.5);
            margin-bottom: 28px;
        }
        
        /* 라벨 */
        label, .stTextInput label {
            color: rgba(255, 255, 255, 0.8) !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            letter-spacing: 0.5px !important;
            text-transform: uppercase;
        }
        
        /* 입력창 */
        div[data-baseweb="input"] {
            background: rgba(255, 255, 255, 0.06) !important;
            border-radius: 14px !important;
            border: 1.5px solid rgba(255,255,255,0.1) !important;
            transition: all 0.3s ease !important;
        }
        div[data-baseweb="input"]:focus-within {
            border-color: rgba(167, 139, 250, 0.6) !important;
            background: rgba(255, 255, 255, 0.09) !important;
            box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.15) !important;
        }
        input {
            color: white !important;
            font-size: 15px !important;
        }
        input::placeholder { color: rgba(255,255,255,0.3) !important; }
        
        /* 로그인 버튼 */
        .stFormSubmitButton > button, .stButton > button {
            background: linear-gradient(135deg, #7c3aed 0%, #a855f7 50%, #ec4899 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 14px !important;
            padding: 14px 0 !important;
            font-size: 16px !important;
            font-weight: 700 !important;
            width: 100% !important;
            letter-spacing: 0.5px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 8px 24px rgba(124, 58, 237, 0.4) !important;
            margin-top: 8px !important;
        }
        .stFormSubmitButton > button:hover, .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 16px 32px rgba(124, 58, 237, 0.5) !important;
            background: linear-gradient(135deg, #6d28d9 0%, #9333ea 50%, #db2777 100%) !important;
        }
        
        /* 익스팬더 */
        details {
            background: rgba(255,255,255,0.04) !important;
            border: 1px solid rgba(255,255,255,0.08) !important;
            border-radius: 14px !important;
            margin-top: 16px !important;
        }
        details > summary {
            color: rgba(255,255,255,0.6) !important;
            padding: 12px 16px !important;
            font-size: 13px !important;
        }
        
        /* 구분선 */
        .divider {
            display: flex;
            align-items: center;
            gap: 12px;
            margin: 20px 0;
        }
        .divider-line {
            flex: 1;
            height: 1px;
            background: rgba(255,255,255,0.1);
        }
        .divider-text {
            color: rgba(255,255,255,0.35);
            font-size: 12px;
            font-weight: 500;
        }
        
        /* 하단 장식 태그 */
        .badge {
            display: inline-block;
            background: rgba(124,58,237,0.2);
            border: 1px solid rgba(124,58,237,0.3);
            color: #c084fc;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 1px;
        }
        
        /* 경고/성공 메시지 */
        .stAlert {
            border-radius: 12px !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    _, col_center, _ = st.columns([1, 1.8, 1])
    
    with col_center:
        # 마스코트 + 브랜드
        st.markdown("""
        <div style="text-align:center; margin-bottom: 28px;">
            <div style="font-size: 90px; line-height:1;">🤖</div>
            <div class="brand-name">ROBOGRAM</div>
            <div class="brand-subtitle">Smart Attendance System</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 로그인 카드
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="section-title">👋 다시 오셨군요!</div>
        <div class="section-desc">계속하려면 로그인해 주세요</div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("아이디", placeholder="아이디를 입력하세요")
            password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요")
            
            submit = st.form_submit_button("🚀  로그인", use_container_width=True)
            
            if submit:
                if not username or not password:
                    st.warning("⚠️ 아이디와 비밀번호를 모두 입력해 주세요.")
                else:
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state.user = user
                        st.session_state.authenticated = True
                        st.success(f"✅ 환영합니다, **{user['name']}**님!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ 아이디 또는 비밀번호가 올바르지 않습니다.")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        with st.expander("🔑 테스트 계정 정보"):
            st.markdown("""
            <div style='font-size: 13px; line-height: 2; color: rgba(255,255,255,0.75);'>
            👨‍💼 <b>관리자</b>: admin / admin123<br>
            👩‍🏫 <b>선생님</b>: teacher1 / teacher123<br>
            👨‍👩‍👧 <b>학부모</b>: parent1 / parent123<br>
            🧒 <b>학생</b>: student1 / student123
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="text-align:center; margin-top: 28px;">
            <span class="badge">🔒 SSL 보안 인증</span>
            &nbsp;
            <span class="badge">📊 실시간 출석</span>
            &nbsp;
            <span class="badge">🤖 로보그램</span>
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

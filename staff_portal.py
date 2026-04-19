import streamlit as st
from auth import authenticate_user, get_role_display_name
import os

# 세션 초기화
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user' not in st.session_state:
    st.session_state.user = None

def login_screen():
    st.set_page_config(page_title="로보그램 관리자 포털", page_icon="🛡️", layout="centered")
    
    # 강력한 가독성 확보를 위한 CSS (Troubleshooting Guide 패턴 적용)
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');
        * { font-family: 'Noto Sans KR', sans-serif !important; }
        
        .stApp {
            background-color: #fcfcfc;
            color: #0f172a;
        }
        
        .main .block-container {
            padding-top: 3rem;
            max-width: 450px;
        }
        
        /* Glassmorphism Logic Card (White Mode) */
        div[data-testid="stForm"] {
            background: #ffffff !important;
            border-radius: 28px !important;
            border: 1px solid #e2e8f0 !important;
            padding: 40px !important;
            box-shadow: 0 20px 40px rgba(0,0,0,0.05) !important;
        }
        
        /* 입력창 가독성 강제 설정 (화이트 모드 고대비) */
        input[type="text"], input[type="password"], [data-baseweb="input"] {
            background-color: #f8fafc !important;
            color: #0f172a !important;
            -webkit-text-fill-color: #0f172a !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 12px !important;
            height: 48px !important;
        }
        
        div[data-testid="stTextInput"] label {
            color: #334155 !important;
            font-weight: 700 !important;
            font-size: 15px !important;
            margin-bottom: 8px !important;
        }
        
        div[data-testid="stTextInput"] div[data-baseweb="input"] {
            border: 1px solid #cbd5e1 !important;
        }

        /* 민트-블루 버튼 */
        .stFormSubmitButton > button {
            background: linear-gradient(90deg, #4fd1c5 0%, #06b6d4 100%) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 12px !important;
            height: 50px !important;
            font-size: 17px !important;
            font-weight: 700 !important;
            width: 100% !important;
            margin-top: 20px !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 10px 20px rgba(6, 182, 212, 0.2) !important;
        }
        .stFormSubmitButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 15px 30px rgba(6, 182, 212, 0.3) !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1.8, 1])
    with col2:
        # [핵심] st.image를 사용한 안정적인 마스코트 로딩
        st.image("static/mascot_small.png", width=140)
        st.markdown("""
        <div style="text-align:center; margin-bottom:28px;">
            <div style="font-size: 32px; font-weight: 900; color: #0f172a;">관리자 포털</div>
            <div style="font-size: 13px; color: #64748b; letter-spacing:2px;">ADMIN & TEACHER ACCESS</div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("아이디", placeholder="아이디를 입력하세요", key="staff_login_user")
            password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요", key="staff_login_pass")
            submit = st.form_submit_button("🔐  로그인", use_container_width=True, key="staff_login_btn")
            
            if submit:
                user = authenticate_user(username, password)
                if user and user['role'] in ['admin', 'teacher']:
                    st.session_state.user = user
                    st.session_state.authenticated = True
                    st.success(f"✅ 인증 완료 — {user['name']}님, 환영합니다!")
                    st.rerun()
                elif user:
                    st.error("⛔ 접근 권한 없음 — 관리자/선생님 전용 포털입니다.")
                else:
                    st.error("❌ 아이디 또는 비밀번호가 올바르지 않습니다.")

def main():
    if not st.session_state.authenticated:
        login_screen()
        return

    user = st.session_state.user
    role = user['role']
    
    from utils import get_now_kst
    now_kst = get_now_kst()
    st.sidebar.title(f"안녕하세요, {user['name']}님")
    st.sidebar.info(f"권한: {get_role_display_name(role)}")
    st.sidebar.caption(f"v1.2.0+Final Fix")
    st.sidebar.markdown(f"🕒 **현재 시간 (KST):**  \n`{now_kst.strftime('%Y-%m-%d %H:%M:%S')}`")
    
    menu_options = []
    if role == 'admin':
        menu_options = ["🏠 관리자 홈", "👩‍🏫 선생님 화면"]
    elif role == 'teacher':
        menu_options = ["👩‍🏫 선생님 화면"]
        
    choice = st.sidebar.selectbox("메뉴 선택", menu_options, key="staff_main_menu")
    
    if st.sidebar.button("🚪 로그아웃", use_container_width=True, key="staff_logout_btn"):
        st.session_state.authenticated = False
        st.session_state.user = None
        st.rerun()

    import sys
    try:
        if choice == "🏠 관리자 홈":
            for mod in ["utils", "admin_app"]:
                if mod in sys.modules:
                    del sys.modules[mod]
            import admin_app
            if hasattr(admin_app, "main"):
                admin_app.main()
        elif choice == "👩‍🏫 선생님 화면":
            for mod in ["utils", "teacher_app"]:
                if mod in sys.modules:
                    del sys.modules[mod]
            import teacher_app
            if hasattr(teacher_app, "main"):
                teacher_app.main()
    except Exception as e:
        st.error(f"앱 로드 오류: {e}")

if __name__ == "__main__":
    main()

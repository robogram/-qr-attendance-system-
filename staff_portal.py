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
    
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');
        * { font-family: 'Noto Sans KR', sans-serif !important; }
        .stApp { background: linear-gradient(160deg, #0f0c29 0%, #302b63 50%, #24243e 100%); }
        .main .block-container { padding-top: 2rem; }
        label { color: rgba(255, 255, 255, 0.8) !important; font-weight: 600 !important; font-size: 13px !important; }
        div[data-baseweb="input"] {
            background: rgba(255, 255, 255, 0.06) !important;
            border-radius: 14px !important;
            border: 1.5px solid rgba(255,255,255,0.1) !important;
        }
        input { color: white !important; }
        .stFormSubmitButton > button, .stButton > button {
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
            color: white !important; border: none !important; border-radius: 14px !important;
            font-size: 16px !important; font-weight: 700 !important; width: 100% !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1.8, 1])
    with col2:
        st.markdown("""
        <div style="text-align:center; margin-bottom:28px;">
            <div style="font-size:80px;">🛡️</div>
            <div style="font-size:30px; font-weight:900; background:linear-gradient(to right,#fff,#a5b4fc);
                        -webkit-background-clip:text; -webkit-text-fill-color:transparent;">관리자 포털</div>
            <div style="font-size:13px; color:rgba(255,255,255,0.5); letter-spacing:2px;">ADMIN & TEACHER ACCESS</div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("아이디", placeholder="아이디를 입력하세요")
            password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요")
            submit = st.form_submit_button("🔐  로그인", use_container_width=True)
            
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
    
    st.sidebar.title(f"안녕하세요, {user['name']}님")
    st.sidebar.info(f"권한: {get_role_display_name(role)}")
    
    menu_options = []
    if role == 'admin':
        menu_options = ["🏠 관리자 홈", "👩‍🏫 선생님 화면"]
    elif role == 'teacher':
        menu_options = ["👩‍🏫 선생님 화면"]
        
    choice = st.sidebar.selectbox("메뉴 선택", menu_options)
    
    if st.sidebar.button("🚪 로그아웃", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user = None
        st.rerun()

    try:
        if choice == "🏠 관리자 홈":
            import admin_app
        elif choice == "👩‍🏫 선생님 화면":
            import teacher_app
    except Exception as e:
        st.error(f"화면을 불러오는 중 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main()

import streamlit as st
from auth import authenticate_user, get_role_display_name
import os
import sys

# 세션 초기화
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user' not in st.session_state:
    st.session_state.user = None

def login_screen():
    st.set_page_config(page_title="Robogram Staff Suite", page_icon="🛡️", layout="centered")
    
    # 배경 디자인
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%);
    }
    .login-container {
        background: rgba(255, 255, 255, 0.05);
        padding: 40px;
        border-radius: 20px;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.title("🤖 Staff Portal")
    st.write("로보그램 출석 시스템 행정 관리")
    
    with st.form("login_form"):
        username = st.text_input("아이디")
        password = st.text_input("비밀번호", type="password")
        submit = st.form_submit_button("로그인", use_container_width=True)
        
        if submit:
            user = authenticate_user(username, password)
            if user and user['role'] in ['admin', 'teacher']:
                st.session_state.user = user
                st.session_state.authenticated = True
                st.rerun()
            elif user:
                st.error("접근 권한이 없습니다. 행정직원용 포털입니다.")
            else:
                st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
    st.markdown('</div>', unsafe_allow_html=True)

def main():
    if not st.session_state.authenticated:
        login_screen()
        return

    user = st.session_state.user
    role = user['role']
    
    # 사이드바 설정
    st.sidebar.title(f"환영합니다, {user['name']}님")
    st.sidebar.info(f"권한: {get_role_display_name(role)}")
    
    # 메뉴 구성 (관리자는 둘 다, 선생님은 선생님만)
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

    # 페이지 렌더링
    try:
        if choice == "🏠 관리자 홈":
            # admin_app.py 실행 (여기서는 sys.argv를 조작하거나 직접 import하여 실행)
            import admin_app
            # admin_app 내에 st.set_page_config가 있으므로 주의가 필요함.
            # 실제 운영 시에는 admin_app을 모듈화하여 함수로 호출하는 것이 좋음.
        elif choice == "👩‍🏫 선생님 화면":
            import teacher_app
    except Exception as e:
        st.error(f"화면을 불러오는 중 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main()

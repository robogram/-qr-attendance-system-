import streamlit as st
from auth import authenticate_user, get_role_display_name
import os

# 세션 초기화
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user' not in st.session_state:
    st.session_state.user = None

def login_screen():
    st.set_page_config(page_title="Robogram Attendance App", page_icon="🎒", layout="centered")
    
    # 모바일 최적화 및 프리미엄 디자인
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
    }
    .login-container {
        background: rgba(255, 255, 255, 0.1);
        padding: 30px;
        border-radius: 20px;
        backdrop-filter: blur(15px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: white;
        text-align: center;
    }
    .stTextInput > div > div > input {
        background: rgba(255, 255, 255, 0.9);
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.title("🎒 My Attendance")
    st.write("로보그램 출석 및 자녀 관리 서비스")
    
    with st.form("login_form"):
        username = st.text_input("아이디 (또는 휴대폰번호)")
        password = st.text_input("비밀번호", type="password")
        submit = st.form_submit_button("로그인", use_container_width=True)
        
        if submit:
            user = authenticate_user(username, password)
            if user and user['role'] in ['parent', 'student']:
                st.session_state.user = user
                st.session_state.authenticated = True
                st.rerun()
            elif user:
                st.error("학부모 또는 학생 계정이 아닙니다. 행정실에 문의하세요.")
            else:
                st.error("정보가 올바르지 않습니다.")
    st.markdown('</div>', unsafe_allow_html=True)

def main():
    if not st.session_state.authenticated:
        login_screen()
        return

    user = st.session_state.user
    role = user['role']
    
    # 사용자별 자동 화면 전환 (학부모는 자녀 관리, 학생은 본인 QR)
    # 별도의 메뉴 없이 로그인 즉시 해당 앱으로 연결하여 UX 극대화
    if role == 'parent':
        import parent_app
    elif role == 'student':
        import student_app

    # 로그아웃 버튼 (하단 고정 또는 사이드바)
    if st.sidebar.button("🚪 로그아웃", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user = None
        st.rerun()

if __name__ == "__main__":
    main()

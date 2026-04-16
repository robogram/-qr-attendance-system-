import streamlit as st
from auth import authenticate_user, get_role_display_name
import os

# 세션 초기화
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user' not in st.session_state:
    st.session_state.user = None

def login_screen():
    st.set_page_config(page_title="로보그램 출석 앱", page_icon="🎒", layout="centered")
    
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');
        * { font-family: 'Noto Sans KR', sans-serif !important; }
        .stApp { background: linear-gradient(160deg, #4f46e5 0%, #7c3aed 100%); }
        .main .block-container { padding-top: 2rem; }
        label { color: white !important; font-weight: 600 !important; font-size: 13px !important; }
        div[data-baseweb="input"] {
            background: rgba(255, 255, 255, 0.15) !important;
            border-radius: 14px !important;
            border: 1.5px solid rgba(255,255,255,0.2) !important;
        }
        input { color: white !important; }
        input::placeholder { color: rgba(255,255,255,0.5) !important; }
        .stFormSubmitButton > button, .stButton > button {
            background: white !important;
            color: #4f46e5 !important; border: none !important; border-radius: 14px !important;
            font-size: 16px !important; font-weight: 700 !important; width: 100% !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1.8, 1])
    with col2:
        st.markdown("""
        <div style="text-align:center; margin-bottom:28px;">
            <div style="font-size:80px;">🎒</div>
            <div style="font-size:30px; font-weight:900; color:white; letter-spacing:-1px;">내 출석 확인</div>
            <div style="font-size:13px; color:rgba(255,255,255,0.7); letter-spacing:1px; margin-top:4px;">학생 / 학부모 전용</div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("아이디", placeholder="아이디를 입력하세요")
            password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요")
            submit = st.form_submit_button("🚀  로그인", use_container_width=True)
            
            if submit:
                user = authenticate_user(username, password)
                if user and user['role'] in ['parent', 'student']:
                    st.session_state.user = user
                    st.session_state.authenticated = True
                    st.rerun()
                elif user:
                    st.error("⛔ 학부모 또는 학생 계정이 아닙니다.")
                else:
                    st.error("❌ 아이디 또는 비밀번호가 올바르지 않습니다.")


def main():
    if not st.session_state.authenticated:
        login_screen()
        return

    user = st.session_state.user
    role = user.get('role')
    
    if st.sidebar.button("🚪 로그아웃", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user = None
        st.rerun()

    try:
        if role == 'parent':
            import parent_app
            parent_app.main()
        elif role == 'student':
            import student_app
            student_app.main()
        else:
            st.error("알 수 없는 사용자 역할입니다.")
    except Exception as e:
        st.error(f"앱 로드 오류: {e}")

if __name__ == "__main__":
    main()

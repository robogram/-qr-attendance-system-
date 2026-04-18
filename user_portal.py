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
        
        .stApp {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            background-attachment: fixed;
        }
        
        .main .block-container {
            padding-top: 3rem;
            max-width: 450px;
        }
        
        /* Glassmorphism Logic Card */
        div[data-testid="stForm"] {
            background: rgba(255, 255, 255, 0.15) !important;
            backdrop-filter: blur(15px) !important;
            -webkit-backdrop-filter: blur(15px) !important;
            border-radius: 24px !important;
            border: 1px solid rgba(255, 255, 255, 0.25) !important;
            padding: 30px !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2) !important;
        }
        
        /* Input Styling */
        div[data-testid="stTextInput"] label {
            color: white !important;
            font-weight: 500 !important;
            font-size: 15px !important;
            margin-bottom: 8px !important;
        }
        
        div[data-testid="stTextInput"] div[data-baseweb="input"] {
            background-color: rgba(255, 255, 255, 0.95) !important;
            border-radius: 12px !important;
            border: 1px solid rgba(255, 255, 255, 0.5) !important;
            height: 48px !important;
            transition: all 0.3s ease !important;
        }
        
        input {
            color: #1e293b !important;
            font-size: 16px !important;
            font-weight: 500 !important;
        }

        /* Input Placeholder Styling */
        input::placeholder {
            color: rgba(30, 41, 59, 0.4) !important;
        }

        /* Focus state for inputs */
        div[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within {
            border: 2px solid #4f46e5 !important;
            background-color: #ffffff !important;
        }
        
        /* Button Styling */
        .stFormSubmitButton > button {
            background: linear-gradient(90deg, #ffffff 0%, #f0f0f0 100%) !important;
            color: #4f46e5 !important;
            border: none !important;
            border-radius: 12px !important;
            height: 50px !important;
            font-size: 17px !important;
            font-weight: 700 !important;
            width: 100% !important;
            margin-top: 20px !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1) !important;
        }
        
        .stFormSubmitButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(0,0,0,0.15) !important;
            background: #ffffff !important;
        }

        .header-container {
            text-align: center;
            margin-bottom: 40px;
        }

        .header-title {
            font-size: 32px;
            font-weight: 900;
            color: white;
            letter-spacing: -1px;
            margin-bottom: 8px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }

        .header-subtitle {
            font-size: 15px;
            color: rgba(255, 255, 255, 0.8);
            letter-spacing: 0.5px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="header-container">
        <img src="data:image/png;base64,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" style="width:120px; height:auto; display:block; margin:0 auto 15px; filter:drop-shadow(0 8px 16px rgba(0,0,0,0.3));">
        <div class="header-title">로보그램 출석 앱</div>
        <div class="header-subtitle">학생 / 학부모 전용 로그인</div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        username = st.text_input("아이디", placeholder="아이디를 입력하세요", key="user_login_user")
        password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요", key="user_login_pass")
        submit = st.form_submit_button("🚀 로그인", use_container_width=True, key="user_login_btn")
        
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
    
    # 사이드바 스타일링
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                background-color: rgba(255, 255, 255, 0.1) !important;
                backdrop-filter: blur(10px) !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.sidebar.title(f"👋 안녕하세요!")
    st.sidebar.subheader(f"{user.get('name', '사용자')}님 환영합니다")
    st.sidebar.info(f"권한: {get_role_display_name(role)}")
    st.sidebar.caption(f"v1.1.7+Session Fix")

    if st.sidebar.button("🚪 로그아웃", use_container_width=True, key="user_logout_btn"):
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

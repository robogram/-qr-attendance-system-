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
    
    # 강력한 가독성 확보를 위한 CSS (Troubleshooting Guide 패턴 적용)
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
        
        /* [핵심] 입력창 가독성 강제 설정 (흰색 배경 + 검정색 글자) */
        input[type="text"], input[type="password"], [data-baseweb="input"] {
            background-color: #ffffff !important;
            color: #000000 !important;
            -webkit-text-fill-color: #000000 !important;
            border-radius: 12px !important;
            height: 48px !important;
        }
        
        div[data-testid="stTextInput"] label {
            color: white !important;
            font-weight: 500 !important;
            font-size: 15px !important;
            margin-bottom: 8px !important;
        }
        
        div[data-testid="stTextInput"] div[data-baseweb="input"] {
            border: 2px solid #e1e1e1 !important;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05) !important;
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
    </style>
    """, unsafe_allow_html=True)
    
    # [핵심] st.image를 사용한 안정적인 마스코트 로딩
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        st.image("static/mascot_small.png", width=140)
    
    st.markdown(f"""
    <div style="text-align:center; margin-top:15px; margin-bottom: 40px;">
        <div style="font-size: 32px; font-weight: 900; color: white; text-shadow: 0 2px 4px rgba(0,0,0,0.2);">로보그램 출석 앱</div>
        <div style="font-size: 15px; color: rgba(255, 255, 255, 0.8);">학생 / 학부모 전용 로그인</div>
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
    st.sidebar.caption(f"v1.2.0+Final Fix")

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

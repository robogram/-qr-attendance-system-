import streamlit as st
import base64
import os
import time
from auth import authenticate_by_name_and_birth, get_role_display_name

# 1. 페이지 설정 (반드시 모든 Streamlit 명령 중 최상단에 위치)
st.set_page_config(page_title="ROBOGRAM Kids", layout="centered")

# 2. 이미지 파일을 Base64로 변환하는 함수
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return None

def login_screen():
    # 세션 상태 초기화
    if "login_success" not in st.session_state:
        st.session_state.login_success = False
    if "login_error" not in st.session_state:
        st.session_state.login_error = False

    mascot_path = "static/mascot_premium.png"
    mascot_base64 = get_base64_image(mascot_path)

    # 3. 프리미엄 UI/UX 커스텀 CSS
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Jua&family=Noto+Sans+KR:wght@400;700&display=swap');

    /* 전체 배경 및 폰트 설정 (단어 단위 줄바꿈 적용) */
    .stApp {{ 
        background: linear-gradient(135deg, #fdfcfb 0%, #e2d1c3 100%);
        word-break: keep-all !important;
        word-wrap: break-word !important;
    }}

    /* 중앙 컨테이너 */
    [data-testid="block-container"] {{
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(15px);
        border-radius: 40px;
        border: 2px solid #ffffff;
        padding: 50px 40px;
        max-width: 440px;
        margin-top: 10vh;
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.05);
    }}

    @media (max-width: 768px) {{
        [data-testid="block-container"] {{ margin-top: 2vh !important; padding: 30px 20px !important; }}
    }}

    /* 마스코트 애니메이션 */
    .main-mascot {{
        position: absolute;
        top: -85px; right: -25px; width: 160px;
        filter: drop-shadow(0 20px 30px rgba(0,0,0,0.15));
        animation: floating 3s ease-in-out infinite;
        z-index: 100;
    }}
    @keyframes floating {{
        0%, 100% {{ transform: translateY(0) rotate(-2deg); }}
        50% {{ transform: translateY(-20px) rotate(5deg); }}
    }}

    .header-container {{ padding-top: 30px; text-align: center; margin-bottom: 20px; position: relative; }}
    .title-text {{ font-family: 'Jua', sans-serif; font-size: 34px; color: #ff8cdd; margin-bottom: 5px; }}
    .sub-text {{ font-size: 15px; color: #777; margin-bottom: 20px; }}

    /* 입력창 및 버튼 */
    .stTextInput > div > div > input {{
        border-radius: 20px !important; border: 2px solid #eee !important; padding: 12px 20px !important;
    }}
    .stButton > button {{
        background: linear-gradient(90deg, #ff8cdd, #ffb7b2) !important;
        border-radius: 25px !important; height: 3.5em; font-family: 'Jua', sans-serif;
        font-size: 20px; color: white !important; border: none !important;
        box-shadow: 0 4px 15px rgba(255, 140, 221, 0.3) !important; transition: transform 0.2s;
    }}
    .stButton > button:hover {{ transform: scale(1.02); }}

    /* 에러 메시지: 시인성 강화 */
    .error-box {{
        background-color: rgba(255, 75, 75, 0.1);
        border: 1px solid rgba(255, 75, 75, 0.2);
        border-radius: 15px;
        padding: 12px;
        margin-bottom: 15px;
        text-align: center;
        animation: fadeIn 0.3s ease-in;
    }}
    .error-text {{
        color: #ff4b4b;
        font-weight: bold;
        font-size: 14px;
        line-height: 1.4;
    }}

    /* 흔들림 효과 */
    {'.stTextInput > div > div > input { border-color: #ff4b4b !important; animation: shake 0.4s cubic-bezier(.36,.07,.19,.97) both !important; }' if st.session_state.login_error else ''}
    @keyframes shake {{
        10%, 90% {{ transform: translate3d(-1px, 0, 0); }}
        20%, 80% {{ transform: translate3d(2px, 0, 0); }}
        30%, 50%, 70% {{ transform: translate3d(-4px, 0, 0); }}
        40%, 60% {{ transform: translate3d(4px, 0, 0); }}
    }}

    /* 성공 화면 */
    .success-view {{
        text-align: center;
        padding: 20px 0;
        animation: successPop 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }}
    @keyframes successPop {{
        from {{ opacity: 0; transform: scale(0.8); }}
        to {{ opacity: 1; transform: scale(1); }}
    }}
    </style>
    """, unsafe_allow_html=True)

    if st.session_state.login_success:
        # --- [성공 시 보여줄 화면] ---
        st.balloons()
        st.markdown(f"""
        <div class="success-view">
            {"<img src='data:image/png;base64," + mascot_base64 + "' style='width:180px; margin-bottom:20px;'>" if mascot_base64 else ""}
            <h1 style="font-family: 'Jua', sans-serif; color: #ff8cdd;">로그인 성공!</h1>
            <p style="color: #666; font-size: 18px;">로보보가 길을 찾고 있어요... 🚀</p>
        </div>
        """, unsafe_allow_html=True)
        
        # UI가 렌더링될 시간을 벌기 위해 st.empty와 sleep 사용
        time.sleep(2)
        st.session_state.authenticated = True
        st.rerun()

    else:
        # --- [로그인 입력 폼] ---
        st.markdown(f"""
        <div class="header-container">
            {"<img src='data:image/png;base64," + mascot_base64 + "' class='main-mascot'>" if mascot_base64 else ""}
            <div class="title-text">안녕, 친구들!</div>
            <div class="sub-text">오늘도 신나는 코딩 모험을 시작해볼까?</div>
        </div>
        """, unsafe_allow_html=True)

        student_name = st.text_input("나의 이름", placeholder="이름을 적어주세요", key="user_login_name")
        access_code = st.text_input("비밀번호 (생년월일 6자리)", type="password", placeholder="예: 150305", key="user_login_code")
        
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        # 에러 메시지: 더 선명하고 박스 형태로 표시
        if st.session_state.login_error:
            st.markdown("""
            <div class="error-box">
                <div class="error-text">앗! 이름이나 생년월일이 틀린 것 같아.<br>다시 한번 확인해 볼래? 😢</div>
            </div>
            """, unsafe_allow_html=True)

        if st.button("수업 입장하기", key="user_login_submit", use_container_width=True):
            if student_name and access_code:
                with st.spinner("로보미가 확인 중... 🤖"):
                    user = authenticate_by_name_and_birth(student_name, access_code)
                    if user and user['role'] in ['parent', 'student']:
                        st.session_state.login_success = True
                        st.session_state.login_error = False
                        st.session_state.user = user
                        st.rerun() # 성공 시 위쪽 login_success 블록으로 이동
                    else:
                        st.session_state.login_success = False
                        st.session_state.login_error = True
                        st.rerun() # 실패 시 에러 메시지 표시
            else:
                st.warning("이름과 비밀번호를 모두 입력해 줘!")

def main():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None

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
    st.sidebar.caption(f"v1.2.2-UI-Fix")

    if st.sidebar.button("🚪 로그아웃", use_container_width=True, key="user_logout_btn"):
        for key in ["authenticated", "user", "login_success", "login_error"]:
            if key in st.session_state:
                del st.session_state[key]
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

import streamlit as st
import base64
import os
import time
from auth import authenticate_by_name_and_birth, get_role_display_name

# 1. 이미지 파일을 Base64로 변환하는 함수
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return None

def login_screen():
    # 세션 상태 초기화 (애니메이션 및 에러 처리용)
    if "login_success" not in st.session_state:
        st.session_state.login_success = False
    if "login_error" not in st.session_state:
        st.session_state.login_error = False

    st.set_page_config(page_title="ROBOGRAM Kids", layout="centered")

    mascot_path = "static/mascot_small.png"
    mascot_base64 = get_base64_image(mascot_path)

    # 3. 프리미엄 UI/UX 커스텀 CSS (Dedent 적용하여 안정성 확보)
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Jua&family=Noto+Sans+KR:wght@400;700&display=swap');

    /* 전체 배경: 경쾌한 파스텔 그라데이션 */
    .stApp {{
        background: linear-gradient(135deg, #fdfcfb 0%, #e2d1c3 100%) !important;
    }}

    /* 글래스모피즘 컨테이너 및 반응형 설정 */
    [data-testid="block-container"] {{
        background: rgba(255, 255, 255, 0.6) !important;
        backdrop-filter: blur(15px) !important;
        -webkit-backdrop-filter: blur(15px) !important;
        border-radius: 40px !important;
        border: 2px solid #ffffff !important;
        padding: 50px 40px !important;
        max-width: 440px !important;
        margin-top: 10vh !important;
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.05) !important;
        transition: all 0.5s ease-in-out !important;
    }}

    /* 모바일 화면 최적화 (미디어 쿼리) */
    @media (max-width: 768px) {{
        [data-testid="block-container"] {{
            margin-top: 2vh !important;
            padding: 30px 20px !important;
        }}
        .title-text {{ font-size: 28px !important; }}
        .stButton > button {{ height: 4em !important; font-size: 18px !important; }}
    }}

    /* 헤더 및 마스코트 애니메이션 */
    .header-container {{ text-align: center; margin-bottom: 25px; }}
    .mascot-welcome {{
        width: 120px;
        margin-bottom: -10px;
        animation: hi-animation 2s ease-in-out infinite;
    }}
    @keyframes hi-animation {{
        0%, 100% {{ transform: rotate(-5deg); }}
        50% {{ transform: rotate(5deg); }}
    }}

    .title-text {{ font-family: 'Jua', sans-serif !important; font-size: 34px !important; color: #ff8cdd !important; margin-bottom: 5px !important; }}
    .sub-text {{ font-size: 15px !important; color: #777 !important; margin-bottom: 20px !important; }}

    /* 입력창 및 버튼 디자인 */
    .stTextInput > div > div > input {{
        border-radius: 20px !important;
        border: 2px solid #eee !important;
        padding: 12px 20px !important;
    }}

    /* [에러 발생 시] Shake 애니메이션 */
    {'.stTextInput > div > div > input { border-color: #ff4b4b !important; animation: shake 0.5s !important; }' if st.session_state.login_error else ''}

    @keyframes shake {{
        0%, 100% {{ transform: translateX(0); }}
        25% {{ transform: translateX(-8px); }}
        75% {{ transform: translateX(8px); }}
    }}

    /* [로그인 성공 시] Fade-out 애니메이션 */
    {'.stApp [data-testid="block-container"] { animation: fadeOut 0.8s forwards !important; }' if st.session_state.login_success else ''}

    @keyframes fadeOut {{
        from {{ opacity: 1; transform: translateY(0); }}
        to {{ opacity: 0; transform: translateY(-30px); }}
    }}

    .stButton > button {{
        background: linear-gradient(90deg, #ff8cdd, #ffb7b2) !important;
        border-radius: 25px !important;
        height: 3.5em !important;
        font-family: 'Jua', sans-serif !important;
        font-size: 20px !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(255, 140, 221, 0.3) !important;
        transition: transform 0.2s !important;
    }}
    .stButton > button:hover {{ transform: scale(1.02) !important; }}
    </style>
    """, unsafe_allow_html=True)

    # 4. 화면 구성
    st.markdown(f"""
    <div class="header-container">
        {"<img src='data:image/png;base64," + mascot_base64 + "' class='mascot-welcome'>" if mascot_base64 else ""}
        <div class="title-text">안녕, 친구들!</div>
        <div class="sub-text">오늘도 신나는 코딩 모험을 시작해볼까?</div>
    </div>
    """, unsafe_allow_html=True)

    student_name = st.text_input("나의 이름", placeholder="이름을 입력해 주세요", key="user_login_name")
    access_code = st.text_input("비밀번호 (생년월일 6자리)", type="password", placeholder="예: 150305", key="user_login_code")

    st.markdown("<div style='height:15px'></div>", unsafe_allow_html=True)

    # 5. 로그인 처리 로직
    if st.button("수업 입장하기", key="user_login_submit"):
        if student_name and access_code:
            with st.spinner("로보미가 확인 중... 🤖"):
                # Supabase 연동 코드 적용
                user = authenticate_by_name_and_birth(student_name, access_code)
                time.sleep(0.8) # 의도적인 약간의 딜레이로 UX 고도화
                
                if user and user['role'] in ['parent', 'student']:
                    st.session_state.login_success = True
                    st.session_state.login_error = False
                    st.session_state.user = user
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.session_state.login_success = False
                    st.session_state.login_error = True
                    st.error("이름이나 비밀번호가 맞지 않아요! 💡")
                    st.rerun()
        else:
            st.warning("이름과 비밀번호를 모두 입력해 주세요!")

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

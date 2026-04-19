import streamlit as st
from auth import authenticate_user, get_role_display_name
import os
import base64

# 세션 초기화
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user' not in st.session_state:
    st.session_state.user = None

# 이미지 파일을 Base64로 변환하는 함수 (허깅페이스 배포 안정성 확보)
def get_base64_image(image_path):
    if os.path.exists(image_path):
        try:
            with open(image_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode()
        except Exception:
            return None
    return None

def login_screen():
    st.set_page_config(page_title="ROBOGRAM Attendance", layout="centered")
    
    mascot_path = "static/mascot_small.png"
    mascot_bg_path = "static/mascot_small1.png"
    mascot_base64 = get_base64_image(mascot_path)
    mascot_bg_base64 = get_base64_image(mascot_bg_path)

    # 1. 프리미엄 글래스모피즘 CSS 주입
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@800&family=Noto+Sans+KR:wght@400;700;900&display=swap');

    /* 전체 앱 배경 */
    .stApp {{
        background: linear-gradient(135deg, #e0f7fa 0%, #fce4ec 100%);
        font-family: 'Noto Sans KR', sans-serif !important;
    }}

    /* Streamlit 메인 컨테이너 글래스모피즘 카드화 */
    [data-testid="block-container"] {{
        background: rgba(255, 255, 255, 0.45);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-radius: 32px;
        border: 1px solid rgba(255, 255, 255, 0.7);
        padding: 50px 40px 40px 40px;
        max-width: 460px;
        margin-top: 5vh;
        box-shadow: 0 25px 50px rgba(0, 0, 0, 0.04);
    }}

    /* 헤더 영역 중앙 정렬 및 애니메이션 */
    .header-container {{
        position: relative;
        text-align: center;
        margin-bottom: 20px;
    }}

    .main-mascot {{
        position: absolute;
        top: -90px;
        right: -10px;
        width: 120px;
        filter: drop-shadow(0 15px 20px rgba(0,0,0,0.12));
        animation: floating 3.5s ease-in-out infinite;
        z-index: 10;
    }}

    .bg-mascot {{
        position: absolute;
        bottom: -20px;
        left: -30px;
        width: 140px;
        opacity: 0.5;
        transform: rotate(-12deg);
        z-index: -1;
    }}

    @keyframes floating {{
        0%, 100% {{ transform: translateY(0) rotate(0deg); }}
        50% {{ transform: translateY(-18px) rotate(4deg); }}
    }}

    .logo-text {{
        font-family: 'Montserrat', sans-serif !important;
        font-size: 42px;
        font-weight: 800;
        letter-spacing: -1.5px;
        background: linear-gradient(to right, #00838f, #d81b60);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }}

    .logo-sub {{
        font-size: 14px;
        color: #455a64;
        font-weight: 500;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 20px;
    }}

    /* 탭 메뉴 커스텀 */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 10px;
        justify-content: center;
        background-color: rgba(255, 255, 255, 0.4);
        padding: 6px;
        border-radius: 16px;
    }}
    
    .stTabs [data-baseweb="tab"] {{
        font-weight: 700 !important;
        border-radius: 10px !important;
    }}

    /* 입력 필드 스타일링 */
    input[type="text"], input[type="password"] {{
        background-color: white !important;
        color: #0f172a !important;
        border-radius: 12px !important;
    }}

    /* 프리미엄 버튼 */
    .stButton > button {{
        width: 100%;
        border-radius: 14px !important;
        height: 3.2em !important;
        background: linear-gradient(90deg, #0097a7, #00bcd4) !important;
        color: white !important;
        border: none !important;
        font-weight: 700 !important;
        font-size: 16px !important;
        box-shadow: 0 8px 15px rgba(0, 188, 212, 0.2) !important;
        transition: all 0.3s ease !important;
        margin-top: 10px;
    }}
    .stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 12px 20px rgba(0, 188, 212, 0.3) !important;
    }}
    </style>
    """, unsafe_allow_html=True)
    
    # 2. 헤더 섹션 렌더링
    st.markdown(f"""
    <div class="header-container">
        {"<img src='data:image/png;base64," + mascot_base64 + "' class='main-mascot'>" if mascot_base64 else ""}
        {"<img src='data:image/png;base64," + mascot_bg_base64 + "' class='bg-mascot'>" if mascot_bg_base64 else ""}
        <div class="logo-text">ROBOGRAM</div>
        <div class="logo-sub">Smart Hybrid Attendance</div>
    </div>
    """, unsafe_allow_html=True)
    
    # 3. 역할별 로그인 탭 렌더링
    role_selection = st.tabs(["🔒 시스템 관리자", "👩‍🏫 교육 담당자"])

    with role_selection[0]:
        with st.container():
            username = st.text_input("관리자 계정", placeholder="Admin ID", key="admin_id_final")
            password = st.text_input("액세스 토큰", type="password", placeholder="Access Token", key="admin_pw_final")
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            if st.button("관리 센터 접속", key="btn_admin_final"):
                user = authenticate_user(username, password)
                if user and user['role'] == 'admin':
                    st.session_state.user = user
                    st.session_state.authenticated = True
                    st.success("✅ 관리자 권한 확인 완료!")
                    st.rerun()
                elif user:
                    st.error("⛔ 시스템 관리자만 접근 가능한 탭입니다.")
                else:
                    st.error("❌ 정보가 올바르지 않습니다.")

    with role_selection[1]:
        with st.container():
            username = st.text_input("교사 이메일", placeholder="teacher@robogram.com", key="teacher_id_final")
            password = st.text_input("비밀번호", type="password", placeholder="••••••••", key="teacher_pw_final")
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            if st.button("클래스 대시보드 열기", key="btn_teacher_final"):
                user = authenticate_user(username, password)
                if user and user['role'] == 'teacher':
                    st.session_state.user = user
                    st.session_state.authenticated = True
                    st.success("✅ 교육 담당자 인증 성공!")
                    st.rerun()
                elif user:
                    st.error("⛔ 교육 담당자 전용 로그인입니다.")
                else:
                    st.error("❌ 이메일 또는 비밀번호를 확인해 주세요.")

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

"""
QR 출석 시스템 설정 파일 - 최종 개선 버전
모든 설정값 최적화 및 설명 추가
"""
import os
import platform

# ==========================================
# 📁 파일 경로 설정
# ==========================================
STUDENTS_CSV = "students.csv"
SCHEDULE_CSV = "schedule.csv"
PARENTS_CSV = "parents.csv"
ATTENDANCE_LOG_CSV = "attendance.csv"
TEACHER_GROUPS_CSV = "teacher_groups.csv"
ATT_DIR = 'attendance_records'
REP_DIR = 'reports'

# 디렉토리 자동 생성
for directory in [ATT_DIR, REP_DIR]:
    os.makedirs(directory, exist_ok=True)

# ==========================================
# 🎨 폰트 설정 (크로스 플랫폼 지원)
# ==========================================
def get_font_path():
    """
    운영체제별 한글 폰트 경로 자동 감지
    
    Returns:
        str: 폰트 파일 경로
    """
    system = platform.system()
    
    if system == "Windows":
        # Windows - 맑은 고딕
        return "C:\\Windows\\Fonts\\malgun.ttf"
    
    elif system == "Darwin":  # macOS
        # macOS - 애플고딕
        return "/System/Library/Fonts/AppleGothic.ttf"
    
    else:  # Linux
        # Ubuntu/Debian - 나눔고딕
        font_paths = [
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]
        
        for path in font_paths:
            if os.path.exists(path):
                return path
        
        # 폰트를 찾을 수 없으면 기본 폰트
        return None

FONT_PATH = get_font_path()

# ==========================================
# 📹 카메라 설정
# ==========================================
# 카메라 인덱스 (0: 기본 웹캠, 1: 외부 카메라)
CAMERA_INDEX = 0

# 카메라 해상도 (고화질 QR 인식을 위해 높은 해상도 권장)
CAMERA_WIDTH = 2560   # 폭
CAMERA_HEIGHT = 1440  # 높이

# JPEG 압축 품질 (1-100, 높을수록 화질 좋음)
JPEG_QUALITY = 100

# ==========================================
# ⏰ 출석 시간 설정
# ==========================================
# 수업 시작 전 출석 가능 시간 (분)
# 예: 30분이면 수업 시작 30분 전부터 출석 체크 가능
EARLY_ARRIVAL_MINUTES = 30

# 🆕 지각 판정 기준 시간 (분)
# 예: 10분이면 수업 시작 후 10분까지는 "출석"으로 처리
# 10분 이후부터는 "지각"으로 처리
LATE_THRESHOLD_MINUTES = 10

# 🆕 메시지 표시 시간 (초)
# 출석 완료 메시지가 화면에 표시되는 시간
MESSAGE_DISPLAY_SECONDS = 3

# ==========================================
# 🤖 자동 결석 처리 설정
# ==========================================
# 🆕 수업 종료 후 자동 결석 처리 대기 시간 (분)
# Priority 1: 10분 → 30분으로 변경 (더 여유있게)
# 
# 동작 방식:
# - 수업이 18:00에 끝난다면
# - 18:30에 자동으로 미출석 학생을 "결석" 처리
# 
# 권장값:
# - 학원/과외: 30-60분 (늦게 오는 학생 고려)
# - 정규 학교: 10-15분 (엄격한 관리)
AUTO_ABSENCE_MINUTES = 30  # ✅ 10분 → 30분으로 변경

# ==========================================
# 🎨 폰트 크기 설정
# ==========================================
# Flask 앱 카메라 화면에 표시되는 텍스트 크기
TITLE_FONT_SIZE = 32      # 타이틀 (예: "로보그램 QR출석")
MESSAGE_FONT_SIZE = 18    # 출석 메시지 (예: "홍길동님! 출석 완료!")
SMALL_FONT_SIZE = 18      # 작은 텍스트

# ==========================================
# 🌐 Flask 서버 설정
# ==========================================
# Flask 서버 호스트 (0.0.0.0 = 모든 네트워크에서 접근 가능)
FLASK_HOST = '0.0.0.0'

# Flask 서버 포트
FLASK_PORT = 5000

# 디버그 모드 (개발 중에만 True, 배포 시 False)
FLASK_DEBUG = False

# ==========================================
# 💬 인사말 메시지 풀
# ==========================================
# QR 출석 완료 시 랜덤으로 표시되는 메시지
# 🆕 더 다양하고 재미있는 메시지 추가
GREETINGS = [
    # 기본 인사
    "출석 완료! 오늘도 멋지게 시작해볼까?",
    "반가워요! 오늘도 신나는 하루 되길~!",
    "입장 완료! 두뇌를 깨울 시간이에요 ",
    "인식 완료! 코드 히어로 출근했어요 ",
    
    # 게임 스타일
    "QR찍고 레벨 업 시작~ \n\n게임보다 재밌는 수업이 기다려요!",
    "오늘도 출석 챌린지 성공! 넌 최고야 ",
    "Level Up! 출석 완료로 경험치 +10",
    "Achievement Unlocked: 출석 달인!",
    
    # AI/코딩 테마
    "AI 친구들도 반가워해요! 출석 OK, 학습 모드 ON!",
    "오늘도 코딩 미션, 준비 완료! 출석을 축하해요 ",
    "와우! 출석 성공! \n\n오늘도 코딩 마스터가 되어보자!",
    "로보그램 세상으로 로그인! 환영합니다 ",
    
    # 응원 메시지
    "너의 오늘을 응원해! 출석 완료",
    "와줘서 고마워! 오늘도 함께해줘서 좋아 ",
    "너는 이미 멋진 시작을 했어! 파이팅 ",
    "내일의 천재, 오늘도 출석 중!",
    
    # 유머러스
    "띠링! 출석 완료~ \n\n오늘도 너의 전설이 시작된다!",
    "어서와~ 여긴 똑똑이들의 천국이야! ",
    "QR 찍는 순간! 넌 이미 반쯤 천재야!",
    "짠! 넌 지금 출석에 성공한 슈퍼 루키야 ",
    "QR만 찍었을 뿐인데... 벌써 멋져요!",
    "너의 출석은 이미 전설이야 ",
    
    # 동기부여
    "출석 완료! 오늘의 미션을 시작하지!",
    "출석 인증 완료! 두뇌 회전 준비됐나요?",
    "출석 성공! 오늘도 신박한 코드로 출발~",
    "환영합니다, 미래의 프로그래머님 ",
    "출석으로 하루를 시작! 브레인 부스터 ON!",
    
    # 재치있는 표현
    "딩동~ 오늘도 당신의 출석을 응원합니다!",
    "QR 찌릿~ 너의 에너지가 느껴졌어",
    "넌 이미 출석이라는 퀘스트를 클리어했어!",
    "출석했군요! 오늘도 지식의 보물을 찾아서!",
    "코딩 히어로, 출석 완료! 오늘도 전진~",
]

# ==========================================
# 🔒 보안 설정
# ==========================================
# 🆕 세션 타임아웃 (초)
# 사용자가 일정 시간 동안 활동이 없으면 자동 로그아웃
SESSION_TIMEOUT_SECONDS = 3600  # 1시간

# 🆕 비밀번호 최소 길이
MIN_PASSWORD_LENGTH = 6

# 🆕 로그인 실패 최대 횟수
MAX_LOGIN_ATTEMPTS = 5

# ==========================================
# 📊 리포트 설정
# ==========================================
# 🆕 한 페이지당 표시할 기록 수
RECORDS_PER_PAGE = 50

# 🆕 차트 색상 팔레트
CHART_COLORS = {
    'attendance': '#4CAF50',  # 출석 - 초록
    'late': '#FF9800',        # 지각 - 주황
    'absent': '#F44336',      # 결석 - 빨강
    'primary': '#667eea',     # 주요 색상 - 보라
    'secondary': '#764ba2'    # 보조 색상 - 진보라
}

# ==========================================
# 📱 모바일 앱 설정
# ==========================================
# 🆕 PWA 앱 이름
PWA_APP_NAME = "로보그램 QR출석"

# 🆕 PWA 테마 색상
PWA_THEME_COLOR = "#667eea"

# 🆕 PWA 배경 색상
PWA_BACKGROUND_COLOR = "#ffffff"

# ==========================================
# 🔔 알림 설정
# ==========================================
# 🆕 출석 완료 시 소리 재생 여부
PLAY_SOUND_ON_ATTENDANCE = True

# 🆕 카카오톡 알림 사용 여부
USE_KAKAO_NOTIFICATION = False

# ==========================================
# 🗄️ 데이터베이스 설정 (향후 확장)
# ==========================================
# 🆕 SQLite 데이터베이스 파일 경로
DB_PATH = "attendance_system.db"

# 🆕 데이터 백업 주기 (일)
BACKUP_INTERVAL_DAYS = 7

# ==========================================
# 🐛 디버깅 설정
# ==========================================
# 🆕 로그 레벨
# DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = "INFO"

# 🆕 로그 파일 경로
LOG_FILE = "attendance_system.log"

# 🆕 로그 파일 최대 크기 (MB)
LOG_MAX_SIZE_MB = 10

# 🆕 로그 백업 파일 수
LOG_BACKUP_COUNT = 5

# ==========================================
# 🎯 기능 플래그 (Feature Flags)
# ==========================================
# 새로운 기능을 테스트할 때 사용
FEATURES = {
    'auto_absence': True,           # 자동 결석 처리
    'face_recognition': False,       # 얼굴 인식 (향후 추가)
    'voice_greeting': False,         # 음성 인사 (향후 추가)
    'email_report': False,           # 이메일 리포트 (향후 추가)
    'sms_notification': False,       # SMS 알림 (향후 추가)
    'barcode_support': False,        # 바코드 지원 (향후 추가)
    'multi_camera': False,           # 다중 카메라 (향후 추가)
    'offline_mode': True,            # 오프라인 모드
}

# ==========================================
# 📝 설정 검증 함수
# ==========================================
def validate_config():
    """
    설정값의 유효성을 검사합니다.
    
    Returns:
        tuple: (is_valid, error_messages)
    """
    errors = []
    
    # 카메라 설정 검증
    if CAMERA_WIDTH < 640 or CAMERA_HEIGHT < 480:
        errors.append("⚠️ 카메라 해상도가 너무 낮습니다. 최소 640x480을 권장합니다.")
    
    # 시간 설정 검증
    if EARLY_ARRIVAL_MINUTES < 0:
        errors.append("⚠️ 조기 도착 시간은 0분 이상이어야 합니다.")
    
    if LATE_THRESHOLD_MINUTES < 0:
        errors.append("⚠️ 지각 판정 시간은 0분 이상이어야 합니다.")
    
    if AUTO_ABSENCE_MINUTES < 5:
        errors.append("⚠️ 자동 결석 처리 시간은 최소 5분 이상을 권장합니다.")
    
    # 폰트 경로 검증
    if FONT_PATH and not os.path.exists(FONT_PATH):
        errors.append(f"⚠️ 폰트 파일을 찾을 수 없습니다: {FONT_PATH}")
    
    # 포트 검증
    if not (1024 <= FLASK_PORT <= 65535):
        errors.append(f"⚠️ Flask 포트는 1024-65535 범위여야 합니다: {FLASK_PORT}")
    
    return len(errors) == 0, errors


def print_config_summary():
    """설정 요약 정보를 출력합니다."""
    print("=" * 60)
    print("🎯 QR 출석 시스템 설정 요약")
    print("=" * 60)
    print(f"📹 카메라: {CAMERA_WIDTH}x{CAMERA_HEIGHT}")
    print(f"⏰ 조기 도착: {EARLY_ARRIVAL_MINUTES}분 전부터 가능")
    print(f"⏱️  지각 기준: 수업 시작 후 {LATE_THRESHOLD_MINUTES}분")
    print(f"🤖 자동 결석: 수업 종료 후 {AUTO_ABSENCE_MINUTES}분")
    print(f"🌐 Flask 서버: {FLASK_HOST}:{FLASK_PORT}")
    print(f"🎨 폰트: {FONT_PATH if FONT_PATH else '기본 폰트'}")
    print(f"💬 인사말: {len(GREETINGS)}개")
    print("=" * 60)
    
    # 설정 검증
    is_valid, errors = validate_config()
    
    if is_valid:
        print("✅ 모든 설정이 유효합니다!")
    else:
        print("❌ 설정 오류 발견:")
        for error in errors:
            print(f"   {error}")
    
    print("=" * 60)


# ==========================================
# 📌 실행 시 설정 검증
# ==========================================
if __name__ == "__main__":
    print_config_summary()

# config.py 끝부분에 추가

# ==========================================
# 🔄 호환성 보장을 위한 통합 상수 (Priority 1)
# ==========================================

# ✅ 보고서 권장: 모든 앱에서 동일한 변수명 사용
ATTENDANCE_BUFFER_BEFORE = EARLY_ARRIVAL_MINUTES  # 30분
ATTENDANCE_BUFFER_AFTER = 15  # 수업 종료 후 버퍼 (새로 추가)

# 출석 상태 상수 (통일성 보장)
ATTENDANCE_STATUS_PRESENT = "출석"
ATTENDANCE_STATUS_LATE = "지각"  
ATTENDANCE_STATUS_ABSENT = "결석"


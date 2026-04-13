"""
QR 출석 시스템 공통 유틸리티 함수
"""
import pandas as pd
import cv2
import numpy as np
from PIL import ImageFont, ImageDraw, Image as PILImage
from datetime import datetime, date, timedelta
import os
import logging
from logging.handlers import RotatingFileHandler
from config import LOG_FILE, LOG_MAX_SIZE_MB, LOG_BACKUP_COUNT, LOG_LEVEL

# 로깅 설정 (RotatingFileHandler 적용)
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

# 핸들러 설정
file_handler = RotatingFileHandler(
    LOG_FILE, 
    maxBytes=LOG_MAX_SIZE_MB * 1024 * 1024, 
    backupCount=LOG_BACKUP_COUNT,
    encoding='utf-8'
)
stream_handler = logging.StreamHandler()

# 포맷 설정
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

# 핸들러 추가
logger.addHandler(file_handler)
logger.addHandler(stream_handler)


def load_csv_safe(path, columns, dtype=None):
    """
    CSV 파일을 안전하게 로드합니다.
    파일이 없으면 빈 DataFrame을 생성합니다.
    
    Args:
        path: CSV 파일 경로
        columns: 컬럼 리스트
        dtype: 데이터 타입 (선택)
    
    Returns:
        DataFrame
    """
    try:
        if not os.path.exists(path):
            df = pd.DataFrame(columns=columns)
            df.to_csv(path, index=False, encoding='utf-8-sig')
            logger.info(f"Created new CSV file: {path}")
            return df
        
        df = pd.read_csv(path, dtype=dtype, encoding='utf-8-sig')
        logger.info(f"Loaded CSV file: {path} ({len(df)} rows)")
        return df
    
    except Exception as e:
        logger.error(f"Error loading CSV {path}: {e}")
        df = pd.DataFrame(columns=columns)
        return df


def save_csv_safe(df, path):
    """
    DataFrame을 안전하게 CSV로 저장합니다.
    
    Args:
        df: 저장할 DataFrame
        path: 저장 경로
    
    Returns:
        bool: 성공 여부
    """
    try:
        df.to_csv(path, index=False, encoding='utf-8-sig')
        logger.info(f"Saved CSV file: {path}")
        return True
    except Exception as e:
        logger.error(f"Error saving CSV {path}: {e}")
        return False


def draw_text_on_frame(frame, text, pos=(20, 40), font_path=None, font_size=36):
    """
    프레임에 한글 텍스트를 오버레이합니다.
    
    Args:
        frame: OpenCV 프레임 (BGR)
        text: 표시할 텍스트
        pos: 텍스트 위치 (x, y)
        font_path: 폰트 파일 경로
        font_size: 폰트 크기
    
    Returns:
        텍스트가 추가된 프레임
    """
    try:
        # BGR to RGB 변환
        pil_img = PILImage.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        
        # 폰트 로드
        try:
            if font_path and os.path.exists(font_path):
                font = ImageFont.truetype(font_path, font_size)
            else:
                font = ImageFont.load_default()
        except Exception as e:
            logger.warning(f"Font loading failed, using default: {e}")
            font = ImageFont.load_default()
        
        # 멀티라인 텍스트 처리
        lines = text.split('\n')
        y = pos[1]
        
        for line in lines:
            draw.text(
                (pos[0], y),
                line,
                font=font,
                fill=(0, 255, 0),
                stroke_width=2,
                stroke_fill=(0, 0, 0)
            )
            y += font_size + 4
        
        # RGB to BGR 변환
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    
    except Exception as e:
        logger.error(f"Error drawing text: {e}")
        return frame


def load_schedule_for_today(schedule_csv):
    """
    오늘 날짜의 수업 일정을 로드합니다.
    
    Args:
        schedule_csv: 일정 CSV 파일 경로
    
    Returns:
        tuple: (start_datetime, end_datetime) 또는 (None, None)
    """
    try:
        df = pd.read_csv(schedule_csv, parse_dates=["date"])
        today = date.today()
        today_row = df[df["date"].dt.date == today]
        
        if today_row.empty:
            logger.info("No schedule found for today")
            return None, None
        
        row = today_row.iloc[0]
        start_dt = datetime.combine(
            today, 
            datetime.strptime(row["start"], "%H:%M").time()
        )
        end_dt = datetime.combine(
            today, 
            datetime.strptime(row["end"], "%H:%M").time()
        )
        
        logger.info(f"Today's schedule: {start_dt} - {end_dt}")
        return start_dt, end_dt
    
    except Exception as e:
        logger.error(f"Error loading schedule: {e}")
        return None, None


def get_attendance_status(scan_time, start_time, late_threshold_minutes=10):
    """
    스캔 시간을 기준으로 출석 상태를 판단합니다.
    
    Args:
        scan_time: QR 스캔 시간
        start_time: 수업 시작 시간
        late_threshold_minutes: 지각 판정 기준 (분)
    
    Returns:
        str: "출석" 또는 "지각"
    """
    if scan_time <= start_time + timedelta(minutes=late_threshold_minutes):
        return "출석"
    return "지각"


def validate_qr_code(code, valid_codes):
    """
    QR 코드가 등록된 코드인지 확인합니다.
    
    Args:
        code: 스캔된 QR 코드
        valid_codes: 유효한 코드 집합
    
    Returns:
        bool: 유효 여부
    """
    return code in valid_codes


def format_attendance_record(code, timestamp, status):
    """
    출석 기록을 포맷팅합니다.
    
    Args:
        code: 학생 코드
        timestamp: 시간
        status: 상태
    
    Returns:
        dict: 포맷팅된 기록
    """
    return {
        "code": code,
        "timestamp": timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp,
        "status": status
    }


def check_camera_available(camera_index=0):
    """
    카메라가 사용 가능한지 확인합니다.
    
    Args:
        camera_index: 카메라 인덱스
    
    Returns:
        bool: 사용 가능 여부
    """
    try:
        cap = cv2.VideoCapture(camera_index)
        if cap.isOpened():
            ret, _ = cap.read()
            cap.release()
            return ret
        return False
    except Exception as e:
        logger.error(f"Camera check failed: {e}")
        return False


# utils.py 끝부분에 추가

# ==========================================
# 🆕 호환성 개선 함수 (보고서 권장사항)
# ==========================================

def generate_session_key(session_name, session_date, session_time):
    """
    표준 세션 키 생성 (Flask와 다른 앱 간 호환)
    
    Args:
        session_name: 세션명 (예: "1회차")
        session_date: 날짜 (date 객체 또는 문자열)
        session_time: 시간 (예: "09:00")
    
    Returns:
        str: 세션 키 (예: "2025-10-14_1회차_09:00")
    """
    if isinstance(session_date, date):
        session_date = session_date.strftime('%Y-%m-%d')
    
    return f"{session_date}_{session_name}_{session_time}"


def normalize_phone(phone):
    """
    전화번호 정규화 (한국 형식)
    admin_app.py의 로직을 공통 함수로 이동
    
    Args:
        phone: 전화번호 (문자열 또는 None)
    
    Returns:
        str: 정규화된 전화번호 (예: "010-1234-5678")
    """
    import pandas as pd
    
    # None, nan, 빈값 체크
    if phone is None or phone == '' or pd.isna(phone):
        return ''
    
    phone = str(phone).strip()
    
    # 'nan', 'none', 'null' 문자열 체크
    if phone.lower() in ['nan', 'none', 'null', '']:
        return ''
    
    # 숫자만 추출
    phone = ''.join(filter(str.isdigit, phone))
    
    # 너무 짧으면 그대로 반환
    if len(phone) < 9:
        return phone
    
    # 0으로 시작하지 않으면 0 추가
    if not phone.startswith('0'):
        phone = '0' + phone
    
    # 포맷팅
    if len(phone) == 11:  # 010-1234-5678
        return f"{phone[:3]}-{phone[3:7]}-{phone[7:]}"
    elif len(phone) == 10:  # 02-1234-5678
        return f"{phone[:2]}-{phone[2:6]}-{phone[6:]}"
    
    return phone


def auto_process_absences_unified(schedule_csv, attendance_csv, students_csv, 
                                   buffer_minutes=30, lock_timeout=5):
    """
    통합 자동 결석 처리 함수 (중복 방지)
    
    Args:
        schedule_csv: 일정 CSV 경로
        attendance_csv: 출석 CSV 경로
        students_csv: 학생 CSV 경로
        buffer_minutes: 수업 종료 후 대기 시간
        lock_timeout: 락 타임아웃 (초)
    
    Returns:
        int: 처리된 결석 건수
    """
    try:
        try:
            import filelock
            lock = filelock.FileLock("absence_processing.lock", timeout=lock_timeout)
        except ImportError:
            # Fallback to a dummy lock if filelock is not installed
            class DummyLock:
                def __init__(self, *args, **kwargs): pass
                def __enter__(self): return self
                def __exit__(self, exc_type, exc_val, exc_tb): pass
            lock = DummyLock()
            filelock = type('DummyFilelock', (), {'Timeout': Exception})()
            
        from config import ATTENDANCE_STATUS_ABSENT
        
        try:
            with lock:
                logger.info("Starting auto absence processing (with lock)")
                
                # 일정 로드
                df_schedule = load_csv_safe(schedule_csv, ['date', 'start', 'end', 'session'])
                df_schedule['date'] = pd.to_datetime(df_schedule['date']).dt.date
                
                # 출석 로드
                df_attendance = load_csv_safe(attendance_csv, 
                    ['date', 'session', 'student_name', 'qr_code', 'timestamp', 'status'])
                
                # 학생 로드
                df_students = load_csv_safe(students_csv, ['name', 'qr_code', 'phone', 'school'])
                
                now = datetime.now()
                today = date.today()
                processed_count = 0
                
                # 오늘의 끝난 수업들 확인
                for _, sched in df_schedule[df_schedule['date'] == today].iterrows():
                    end_time = datetime.strptime(sched['end'], '%H:%M').time()
                    end_dt = datetime.combine(today, end_time)
                    
                    # 수업 종료 + 버퍼 시간이 지났는지 확인
                    if now < end_dt + timedelta(minutes=buffer_minutes):
                        continue
                    
                    # 이 세션의 출석 기록 확인
                    session_key = generate_session_key(
                        sched['session'], 
                        sched['date'], 
                        sched['start']
                    )
                    
                    session_records = df_attendance[
                        (df_attendance['date'] == sched['date']) & 
                        (df_attendance['session'] == sched['session'])
                    ]
                    
                    attended_students = set(session_records['student_name'].unique())
                    all_students = set(df_students['name'].tolist())
                    
                    # 결석 학생 찾기
                    absent_students = all_students - attended_students
                    
                    # 결석 기록 추가 (중복 체크)
                    for student in absent_students:
                        # 이미 결석 처리되었는지 확인
                        existing = df_attendance[
                            (df_attendance['date'] == sched['date']) &
                            (df_attendance['session'] == sched['session']) &
                            (df_attendance['student_name'] == student) &
                            (df_attendance['status'] == ATTENDANCE_STATUS_ABSENT)
                        ]
                        
                        if existing.empty:
                            # 새 결석 기록 추가
                            new_record = pd.DataFrame([{
                                'date': sched['date'],
                                'session': sched['session'],
                                'student_name': student,
                                'qr_code': student,
                                'timestamp': end_dt.isoformat(),
                                'status': ATTENDANCE_STATUS_ABSENT
                            }])
                            
                            df_attendance = pd.concat([df_attendance, new_record], 
                                                     ignore_index=True)
                            processed_count += 1
                            logger.info(f"Auto absence: {student} - {sched['session']}")
                
                # 저장
                if processed_count > 0:
                    save_csv_safe(df_attendance, attendance_csv)
                    logger.info(f"Processed {processed_count} absences")
                
                return processed_count
                
        except filelock.Timeout:
            logger.info("Another process is handling absences (lock timeout)")
            return 0
            
    except Exception as e:
        logger.error(f"Error in auto_process_absences_unified: {e}")
        return 0


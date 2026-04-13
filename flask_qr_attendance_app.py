"""
Flask QR 출석 시스템 - 중복 체크 강화 최종 버전 (Priority 3 완료)
카메라 스트리밍 및 QR 인식 담당
자동 결석 처리 + 강화된 중복 체크
"""
from flask import Flask, request, jsonify, Response, render_template_string, jsonify
import cv2
from pyzbar.pyzbar import decode
from datetime import datetime, timedelta
import random
import csv
import atexit
import logging
import pandas as pd
import os
from threading import Thread, Lock
import time
from collections import defaultdict

# 로컬 모듈 임포트
from config import (
    STUDENTS_CSV, ATTENDANCE_LOG_CSV, SCHEDULE_CSV,
    CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT,
    EARLY_ARRIVAL_MINUTES, LATE_THRESHOLD_MINUTES,
    MESSAGE_DISPLAY_SECONDS, GREETINGS,
    FLASK_HOST, FLASK_PORT, FLASK_DEBUG, JPEG_QUALITY, FONT_PATH,
    TITLE_FONT_SIZE, MESSAGE_FONT_SIZE, SMALL_FONT_SIZE,
    AUTO_ABSENCE_MINUTES,
    # 🆕 출석 상태 상수 추가
    ATTENDANCE_STATUS_PRESENT,
    ATTENDANCE_STATUS_LATE,
    ATTENDANCE_STATUS_ABSENT
)
from utils import (
    load_csv_safe, draw_text_on_frame, load_schedule_for_today,
    get_attendance_status, validate_qr_code, format_attendance_record,
    check_camera_available, logger
)

# Flask 앱 초기화
app = Flask(__name__)

# ==========================================
# 🔒 전역 변수 및 스레드 안전성
# ==========================================
attendance_records = []
attendance_lock = Lock()  # 🆕 스레드 안전성을 위한 Lock

# 🆕 강화된 중복 체크 시스템
# 구조: {student_name: {session_key: timestamp}}
scanned_students = defaultdict(dict)
scanned_lock = Lock()  # 🆕 중복 체크용 Lock

camera = None

# ==========================================
# 📹 카메라 관리
# ==========================================
def initialize_camera():
    """카메라를 초기화합니다."""
    global camera
    
    if not check_camera_available(CAMERA_INDEX):
        logger.error("Camera not available")
        return False
    
    camera = cv2.VideoCapture(CAMERA_INDEX)
    
    # 고화질 설정
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    camera.set(cv2.CAP_PROP_FPS, 30)
    camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    camera.set(cv2.CAP_PROP_AUTOFOCUS, 1)
    camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
    
    logger.info(f"Camera initialized: {CAMERA_WIDTH}x{CAMERA_HEIGHT} @ 30fps")
    return True


def cleanup_camera():
    """카메라 리소스를 정리합니다."""
    global camera
    if camera is not None:
        camera.release()
        cv2.destroyAllWindows()
        logger.info("Camera resources released")


# 앱 종료 시 카메라 정리
atexit.register(cleanup_camera)


# ==========================================
# 🎯 유효 코드 로드
# ==========================================
def load_valid_codes():
    """유효한 QR 코드 목록(students 테이블의 qr_code_data)을 로드합니다."""
    from supabase_client import supabase_mgr
    valid_codes = supabase_mgr.load_valid_codes()
    logger.info(f"Loaded {len(valid_codes)} valid codes from Supabase")
    return valid_codes


# ==========================================
# 🆕 강화된 세션 키 생성
# ==========================================
def generate_session_key(session_name, session_date, session_time):
    """
    정확한 세션 키 생성
    
    Args:
        session_name: 수업명
        session_date: 날짜
        session_time: 시작 시간
    
    Returns:
        str: 고유 세션 키
    """
    return f"{session_date}_{session_name}_{session_time}"


# ==========================================
# 🆕 강화된 중복 체크 시스템
# ==========================================
def is_already_scanned(student_id, schedule_id):
    """학생이 해당 세션에 이미 출석했는지 확인 (Supabase)"""
    from supabase_client import supabase_mgr
    return supabase_mgr.check_already_attended(student_id, schedule_id)


def mark_as_scanned(student_name, session_key):
    """
    학생을 출석 처리로 표시
    
    Args:
        student_name: 학생 이름
        session_key: 세션 키
    """
    with scanned_lock:
        scanned_students[student_name][session_key] = datetime.now()
        logger.info(f"Marked as scanned: {student_name} for session {session_key}")


# ==========================================
# 🆕 현재 진행중인 수업 찾기 (개선)
# ==========================================
def get_student_schedule(student_name):
    """학생의 이름으로 오늘 진행 중인 해당 학생의 수업 정보를 찾습니다."""
    try:
        from supabase_client import supabase_mgr
        now = datetime.now()
        target_date_str = now.date().isoformat()
        
        # 1. 학생이 속한 그룹 찾기 (STUDENT_GROUPS_CSV 사용)
        from config import STUDENT_GROUPS_CSV
        df_std_groups = load_csv_safe(STUDENT_GROUPS_CSV, ['student_name', 'group_id'])
        student_group_ids = df_std_groups[df_std_groups['student_name'] == student_name]['group_id'].tolist()
        
        if not student_group_ids:
            logger.warning(f"Student {student_name} is not assigned to any group.")
            return None

        # 2. 그룹 ID로 그룹명(B반, A반 등) 찾기 (CLASS_GROUPS_CSV 사용)
        from admin_app import CLASS_GROUPS_CSV
        df_classes = load_csv_safe(CLASS_GROUPS_CSV, ['group_id', 'group_name'])
        group_names = df_classes[df_classes['group_id'].isin(student_group_ids)]['group_name'].tolist()
        
        # 3. 오늘 전체 일정 가져오기
        schedules = supabase_mgr.get_schedule_for_date(target_date_str)
        if not schedules:
            return None
            
        # 4. 학생의 그룹명과 일치하는 일정 필터링
        for sched in schedules:
            class_name = sched.get('class_name', '')
            # 그룹명(A반)이 수업명(A반 1회차 등)에 포함되는지 확인
            is_match = any(gn in class_name for gn in group_names)
            
            if is_match:
                try:
                    class_start_dt = datetime.fromisoformat(sched['start_time'].replace('Z', '')) if sched['start_time'] else None
                    if class_start_dt and class_start_dt.tzinfo:
                        class_start_dt = class_start_dt.replace(tzinfo=None)
                        
                    class_end_dt = datetime.fromisoformat(sched['end_time'].replace('Z', '')) if sched['end_time'] else None
                    if class_end_dt and class_end_dt.tzinfo:
                        class_end_dt = class_end_dt.replace(tzinfo=None)
                    
                    if not class_start_dt or not class_end_dt: continue
                    
                    # 출석 인정 범위 (EARLY_ARRIVAL_MINUTES 분 전 ~ 수업 종료 시각)
                    attendance_start = class_start_dt - timedelta(minutes=EARLY_ARRIVAL_MINUTES)
                    
                    if attendance_start <= now <= class_end_dt:
                        return {
                            'schedule_id': sched['id'],
                            'session_name': sched['class_name'],
                            'start_time': class_start_dt.strftime('%H:%M'),
                            'end_time': class_end_dt.strftime('%H:%M'),
                            'start_dt': class_start_dt,
                            'end_dt': class_end_dt
                        }
                except: continue
        
        return None
def get_current_session():
    """오늘 전체 일정 중 현재 시간 기준으로 진행 중인 수업 정보를 찾습니다."""
    try:
        from supabase_client import supabase_mgr
        now = datetime.now()
        target_date_str = now.date().isoformat()
        
        # 오늘 전체 일정 가져오기
        schedules = supabase_mgr.get_schedule_for_date(target_date_str)
        if not schedules:
            return None
            
        for sched in schedules:
            try:
                class_start_dt = datetime.fromisoformat(sched['start_time'].replace('Z', '')) if sched['start_time'] else None
                if class_start_dt and class_start_dt.tzinfo:
                    class_start_dt = class_start_dt.replace(tzinfo=None)
                    
                class_end_dt = datetime.fromisoformat(sched['end_time'].replace('Z', '')) if sched['end_time'] else None
                if class_end_dt and class_end_dt.tzinfo:
                    class_end_dt = class_end_dt.replace(tzinfo=None)
                
                if not class_start_dt or not class_end_dt: continue
                
                # 출석 인정 범위 (30분 전 ~ 수업 종료 시각)
                attendance_start = class_start_dt - timedelta(minutes=EARLY_ARRIVAL_MINUTES)
                
                if attendance_start <= now <= class_end_dt:
                    return {
                        'schedule_id': sched['id'],
                        'session_name': sched['class_name'],
                        'start_time': class_start_dt.strftime('%H:%M'),
                        'end_time': class_end_dt.strftime('%H:%M'),
                        'start_dt': class_start_dt,
                        'end_dt': class_end_dt
                    }
            except: continue
        
        return None
    except Exception as e:
        logger.error(f"Error in get_current_session: {e}")
        return None


# ==========================================
# 🤖 자동 결석 처리 (개선)
# ==========================================
def auto_absence_checker():
    """Supabase 버전: 자동 결석 처리는 백엔드 크론으로 이전 예정이므로 현재 로컬 스레드에서는 패스합니다."""
    pass

def process_absence_for_session(session_name, target_date):
    """Supabase 버전: 자동 결석 처리 로직 (미사용)"""
    return {'success': False, 'count': 0, 'error': 'Not applicable for Supabase'}


# ==========================================
# 📹 비디오 스트리밍 (개선)
# ==========================================
def generate_frames():
    """비디오 프레임을 생성하고 QR 코드를 스캔합니다."""
    global attendance_records
    
    # 메시지 표시용 변수
    last_msg = None
    last_ts = None
    msg_duration = timedelta(seconds=MESSAGE_DISPLAY_SECONDS)
    
    while True:
        # 카메라에서 프레임 읽기
        if camera is None or not camera.isOpened():
            logger.error("Camera not available")
            break
        
        success, frame = camera.read()
        if not success:
            logger.warning("Failed to read frame")
            break
        
        now = datetime.now()
        
        # 유효한 코드 로드
        valid_codes = load_valid_codes()
        
        # 메시지 표시 중이면 스캔 건너뛰기
        if last_msg and (now - last_ts) <= msg_duration:
            frame = draw_text_on_frame(frame, last_msg, pos=(20, 40), font_path=FONT_PATH)
            ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' +
                       buffer.tobytes() + b'\r\n')
            continue
        
        # 🆕 타이틀은 이제 student_schedule 안에서 개별적으로 체크하되,
        # 루프 전에는 일반적인 안내 문구만 표시
        
        # 타이틀 항상 표시
        frame = draw_text_on_frame(
            frame, 
            "로보그램 QR전자출석 프로그램", 
            pos=(20, 40),
            font_path=FONT_PATH,
            font_size=TITLE_FONT_SIZE
        )
        
        # QR 코드 인식
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        decoded_objects = decode(gray)
        
        if decoded_objects:
            for obj in decoded_objects:
                try:
                    code = obj.data.decode('utf-8').strip()
                    
                    # 1. 명단에 있는지 확인
                    from supabase_client import supabase_mgr
                    student = supabase_mgr.get_student_by_qr(code)
                    if not student:
                        last_msg = f"{code}님은 출석 명단에 없습니다."
                        last_ts = now
                        logger.warning(f"Unregistered code scanned: {code}")
                        continue
                    
                    student_id = student['id']
                    student_name = student['student_name']
                    
                    # 2. 학생에게 맞는 현재 수업 확인 (학생-그룹 매칭 기반)
                    current_session = get_student_schedule(student_name)
                    
                    if not current_session:
                        last_msg = f"{student_name}님의 진행 중인\n수업이 없습니다."
                        last_ts = now
                        logger.warning(f"No active session for student {student_name}")
                        continue
                    
                    schedule_id = current_session['schedule_id']
                    
                    # 3. 중복 출석 확인
                    session_key = f"{now.date().isoformat()}_{current_session['session_name']}_{student_id}"
                    
                    # 메모리 체크 우선
                    already_scanned = False
                    with scanned_lock:
                        if student_name in scanned_students and session_key in scanned_students[student_name]:
                            already_scanned = True
                    
                    if already_scanned or is_already_scanned(student_id, schedule_id):
                        last_msg = f"{student_name}님은 이미 출석 체크되었습니다."
                        last_ts = now
                        logger.info(f"Duplicate scan blocked: {student_name}")
                        continue
                    
                    # 4. 출석 상태 판정
                    start_dt = current_session['start_dt']
                    time_diff = (now - start_dt).total_seconds() / 60
                    
                    if time_diff <= 0:
                        status = "출석"
                        status_detail = "정시 출석"
                    elif time_diff <= LATE_THRESHOLD_MINUTES:
                        status = "지각"
                        status_detail = f"{int(time_diff)}분 지각"
                    else:
                        status = "결석"
                        status_detail = "수업 중 도착"
                    
                    # 5. DB에 기록
                    success = supabase_mgr.insert_attendance(
                        student_id=student_id,
                        schedule_id=schedule_id,
                        check_in_time=now.isoformat(),
                        status=status,
                        type_str='오프라인'
                    )
                    
                    if success:
                        mark_as_scanned(student_name, session_key)
                        with attendance_lock:
                            record = format_attendance_record(student_name, now, status)
                            attendance_records.append(record)
                        
                        if status == "출석" or status == "지각":
                            if status == "지각":
                                last_msg = f"{student_name}님!\n\n{status_detail}"
                            else:
                                greeting = random.choice(GREETINGS)
                                last_msg = f"{student_name}님!\n\n{greeting}"
                        else:
                            last_msg = f"{student_name}님! 너무 늦었네요."
                            
                        logger.info(f"Attendance recorded: {student_name} - {status} ({status_detail})")
                    else:
                        last_msg = "DB 기록 실패. 관리자에게 문의하세요."
                    
                    last_ts = now
                
                except Exception as e:
                    logger.error(f"Error processing QR code: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    continue
        
        # 메시지 오버레이
        if last_msg and (now - last_ts) <= msg_duration:
            frame = draw_text_on_frame(
                frame, 
                last_msg, 
                pos=(20, 160),
                font_path=FONT_PATH,
                font_size=MESSAGE_FONT_SIZE
            )
        
        # JPEG 인코딩 및 스트리밍
        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
        if not ret:
            logger.warning("Failed to encode frame")
            continue
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + 
               buffer.tobytes() + b'\r\n')


# ==========================================
# 🌐 Flask 라우트
# ==========================================
@app.route('/video_feed')
def video_feed():
    """비디오 스트림 엔드포인트"""
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/')
def index():
    """메인 페이지"""
    return _index_html()

@app.route('/api/shutdown', methods=['POST'])
def shutdown():
    """Flask 서버를 안전하게 종료합니다."""
    import os
    import signal
    logger.info('Shutdown API called. Terminating server...')
    # Return response first then kill
    def kill_server():
        import time as _t
        _t.sleep(0.5)
        os._exit(0)  # On Windows, os._exit is more reliable for immediate termination
    Thread(target=kill_server, daemon=True).start()
    return jsonify({'message': 'Server shutting down...'}), 200

def _index_html():
    """메인 페이지 HTML"""
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QR 출석 스트리밍</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            background-color: #1a1a1a;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .container {
            max-width: 100%;
            padding: 20px;
        }
        img {
            width: 100%;
            height: auto;
            border: 3px solid #4CAF50;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        h1 {
            color: #4CAF50;
            text-align: center;
            font-family: Arial, sans-serif;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔹 로보그램 QR 출석 시스템</h1>
        <img src="/video_feed" alt="QR 출석 스트림" />
    </div>
</body>
</html>
""")


@app.route("/attendance_log")
def attendance_log():
    """출석 로그 API 엔드포인트"""
    try:
        with attendance_lock:
            return jsonify(attendance_records)
    except Exception as e:
        logger.error(f"Error in attendance_log endpoint: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/status")
def status():
    """시스템 상태 확인 엔드포인트"""
    try:
        current_session = get_current_session()
        now = datetime.now()
        
        # 출석 가능 여부 판단
        attendance_available = False
        if current_session:
            start_dt = current_session['start_dt']
            end_dt = current_session['end_dt']
            attendance_start = start_dt - timedelta(minutes=EARLY_ARRIVAL_MINUTES)
            
            attendance_available = attendance_start <= now <= end_dt
        
        status_info = {
            "camera_active": camera is not None and camera.isOpened(),
            "total_scanned": sum(len(sessions) for sessions in scanned_students.values()),
            "total_records": len(attendance_records),
            "current_session": current_session['session_name'] if current_session else None,
            "current_time": now.isoformat(),
            "attendance_available": attendance_available
        }
        
        return jsonify(status_info)
    
    except Exception as e:
        logger.error(f"Error in status endpoint: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/reset")
def reset():
    """출석 데이터 리셋 (디버깅용)"""
    global scanned_students, attendance_records
    
    with scanned_lock:
        scanned_students.clear()
    
    with attendance_lock:
        attendance_records.clear()
    
    logger.info("Attendance data reset")
    return jsonify({"message": "Attendance data has been reset"})


# ==========================================
# 🚀 앱 실행
# ==========================================
if __name__ == '__main__':
    # 카메라 초기화
    if initialize_camera():
        # 자동 결석 처리 스레드 시작
        absence_thread = Thread(target=auto_absence_checker, daemon=True)
        absence_thread.start()
        logger.info(f"✅ Auto absence checker started ({AUTO_ABSENCE_MINUTES} minutes after class end)")
        
        logger.info(f"Starting Flask server at http://{FLASK_HOST}:{FLASK_PORT}")
        logger.info("=" * 60)
        logger.info("🎯 강화된 중복 체크 시스템 활성화")
        logger.info("=" * 60)
        
        app.run(
            host=FLASK_HOST, 
            port=FLASK_PORT, 
            debug=FLASK_DEBUG, 
            threaded=True
        )
    else:
        logger.error("Failed to initialize camera. Exiting.")

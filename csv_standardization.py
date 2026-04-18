"""
CSV 파일 표준화 스크립트
기존 CSV 파일들의 구조 문제를 자동으로 수정합니다.
"""
import pandas as pd
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from utils import get_now_kst


def backup_csv(filename):
    """CSV 파일 백업"""
    if os.path.exists(filename):
        backup_name = f"{filename}.backup_{get_now_kst().strftime('%Y%m%d_%H%M%S')}"
        import shutil
        shutil.copy(filename, backup_name)
        logger.info(f"[OK] backup complete: {backup_name}")
        return True
    return False


def standardize_attendance_csv():
    """attendance.csv 표준화"""
    filename = "attendance.csv"
    
    if not os.path.exists(filename):
        logger.warning(f"[!] {filename} file not found.")
        return
    
    logger.info(f"[File] {filename} standardization started...")
    
    # 백업
    backup_csv(filename)
    
    try:
        # CSV 읽기
        df = pd.read_csv(filename, encoding='utf-8-sig')
        
        logger.info(f"[Stats] current columns: {list(df.columns)}")
        logger.info(f"[Stats] current dtypes:\n{df.dtypes}")
        
        # ===== 1. 중복 컬럼 처리 =====
        if 'code' in df.columns:
            logger.info("[Fix] removing 'code' column (duplicate of qr_code)")
            df = df.drop(columns=['code'])
        
        # ===== 2. 컬럼명 표준화 =====
        column_mapping = {
            'name': 'student_name',
            'student': 'student_name',
            'qr': 'qr_code',
            'time': 'timestamp'
        }
        
        df = df.rename(columns=column_mapping)
        logger.info("[OK] column renaming complete")
        
        # ===== 3. 필수 컬럼 확인 및 생성 =====
        required_columns = ['date', 'session', 'student_name', 'qr_code', 'timestamp', 'status']
        
        for col in required_columns:
            if col not in df.columns:
                if col == 'student_name' and 'qr_code' in df.columns:
                    df['student_name'] = df['qr_code']
                    logger.info("✅ 'student_name' 컬럼 생성 (qr_code에서)")
                elif col == 'status':
                    df['status'] = '출석'
                    logger.info("✅ 'status' 컬럼 생성 (기본값: 출석)")
                elif col == 'date' and 'timestamp' in df.columns:
                    df['date'] = pd.to_datetime(df['timestamp']).dt.date
                    logger.info("[OK] 'date' column created (from timestamp)")
        
        # ===== 4. 데이터 타입 변환 =====
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            logger.info("[OK] timestamp -> DateTime conversion")
        
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
            logger.info("[OK] date -> Date conversion")
        
        if 'qr_code' in df.columns:
            df['qr_code'] = df['qr_code'].astype(str)
            logger.info("[OK] qr_code -> String conversion")
        
        # ===== 5. 컬럼 순서 정렬 =====
        final_columns = ['date', 'session', 'student_name', 'qr_code', 'timestamp', 'status']
        
        # 존재하는 컬럼만 선택
        available_columns = [col for col in final_columns if col in df.columns]
        df = df[available_columns]
        
        logger.info(f"[OK] final column order: {available_columns}")
        
        # ===== 6. 중복 제거 =====
        before_count = len(df)
        df = df.drop_duplicates(subset=['date', 'session', 'student_name'], keep='first')
        after_count = len(df)
        
        if before_count > after_count:
            logger.info(f"[OK] duplicates removed: {before_count - after_count} rows removed")
        
        # ===== 7. 저장 =====
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f"[OK] {filename} standardization complete!")
        logger.info(f"[Stats] final row count: {len(df)}")
        logger.info(f"[Stats] final columns: {list(df.columns)}")
        
    except Exception as e:
        logger.error(f"❌ {filename} 표준화 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())


def standardize_class_groups_csv():
    """class_groups.csv 표준화"""
    filename = "class_groups.csv"
    
    if not os.path.exists(filename):
        logger.warning(f"⚠️ {filename} 파일이 없습니다.")
        return
    
    logger.info(f"📂 {filename} 표준화 시작...")
    
    # 백업
    backup_csv(filename)
    
    try:
        df = pd.read_csv(filename, encoding='utf-8-sig')
        
        logger.info(f"📊 현재 컬럼: {list(df.columns)}")
        
        # ===== 1. weekdays 타입 확인 =====
        if 'weekdays' in df.columns:
            # Integer면 String으로 변환
            df['weekdays'] = df['weekdays'].astype(str)
            logger.info("✅ weekdays → String 변환")
        
        # ===== 2. total_hours 확인 =====
        if 'total_hours' in df.columns:
            df['total_hours'] = pd.to_numeric(df['total_hours'], errors='coerce').fillna(1.0)
            logger.info("✅ total_hours → Float 변환 (결측값 → 1.0)")
        else:
            df['total_hours'] = 1.0
            logger.info("✅ total_hours 컬럼 생성 (기본값: 1.0)")
        
        # ===== 3. 날짜 형식 통일 =====
        if 'start_date' in df.columns:
            df['start_date'] = pd.to_datetime(df['start_date'], errors='coerce').dt.strftime('%Y-%m-%d')
            logger.info("✅ start_date → YYYY-MM-DD 형식")
        
        if 'end_date' in df.columns:
            df['end_date'] = pd.to_datetime(df['end_date'], errors='coerce').dt.strftime('%Y-%m-%d')
            logger.info("✅ end_date → YYYY-MM-DD 형식")
        
        # ===== 4. 저장 =====
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f"[OK] {filename} standardization complete!")
        
    except Exception as e:
        logger.error(f"❌ {filename} 표준화 실패: {e}")


def standardize_students_csv():
    """students.csv 표준화"""
    filename = "students.csv"
    
    if not os.path.exists(filename):
        logger.warning(f"⚠️ {filename} 파일이 없습니다.")
        return
    
    logger.info(f"📂 {filename} 표준화 시작...")
    
    # 백업
    backup_csv(filename)
    
    try:
        df = pd.read_csv(filename, encoding='utf-8-sig')
        
        logger.info(f"📊 현재 컬럼: {list(df.columns)}")
        
        # ===== 1. 중복 컬럼 처리 =====
        if 'code' in df.columns and 'qr_code' in df.columns:
            # code와 qr_code가 같은 값인지 확인
            if (df['code'] == df['qr_code']).all():
                logger.info("🔧 'code' 컬럼 제거 (qr_code와 동일)")
                df = df.drop(columns=['code'])
            else:
                logger.warning("⚠️ 'code'와 'qr_code'가 다릅니다. 수동 확인 필요!")
        
        # ===== 2. 전화번호 정규화 =====
        if 'phone' in df.columns:
            def normalize_phone(phone):
                if pd.isna(phone):
                    return ""
                phone = str(phone).strip()
                phone = ''.join(filter(str.isdigit, phone))
                
                if len(phone) == 11 and phone.startswith('010'):
                    return f"{phone[:3]}-{phone[3:7]}-{phone[7:]}"
                elif len(phone) == 10:
                    return f"0{phone[:2]}-{phone[2:6]}-{phone[6:]}"
                else:
                    return phone
            
            df['phone'] = df['phone'].apply(normalize_phone)
            logger.info("✅ 전화번호 정규화 (010-XXXX-XXXX)")
        
        # ===== 3. 필수 컬럼 확인 =====
        required_columns = ['name', 'qr_code', 'phone', 'school']
        
        for col in required_columns:
            if col not in df.columns:
                if col == 'school':
                    df['school'] = ""
                    logger.info("✅ 'school' 컬럼 생성 (빈 값)")
        
        # ===== 4. 저장 =====
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f"[OK] {filename} standardization complete!")
        logger.info(f"[Stats] student count: {len(df)}")
        
    except Exception as e:
        logger.error(f"❌ {filename} 표준화 실패: {e}")


def standardize_schedule_csv():
    """schedule.csv 표준화"""
    filename = "schedule.csv"
    
    if not os.path.exists(filename):
        logger.warning(f"⚠️ {filename} 파일이 없습니다.")
        return
    
    logger.info(f"📂 {filename} 표준화 시작...")
    
    # 백업
    backup_csv(filename)
    
    try:
        df = pd.read_csv(filename, encoding='utf-8-sig')
        
        logger.info(f"📊 현재 컬럼: {list(df.columns)}")
        
        # ===== 1. 날짜 형식 통일 =====
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%Y-%m-%d')
            logger.info("✅ date → YYYY-MM-DD 형식")
        
        # ===== 2. 시간 형식 확인 =====
        if 'start' in df.columns:
            # HH:MM 형식 확인
            try:
                pd.to_datetime(df['start'], format='%H:%M', errors='raise')
                logger.info("✅ start 시간 형식 정상")
            except:
                logger.warning("⚠️ start 시간 형식 확인 필요")
        
        if 'end' in df.columns:
            try:
                pd.to_datetime(df['end'], format='%H:%M', errors='raise')
                logger.info("✅ end 시간 형식 정상")
            except:
                logger.warning("⚠️ end 시간 형식 확인 필요")
        
        # ===== 3. 저장 =====
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f"[OK] {filename} standardization complete!")
        logger.info(f"[Stats] schedule count: {len(df)}")
        
    except Exception as e:
        logger.error(f"❌ {filename} 표준화 실패: {e}")


def verify_csv_structure():
    """모든 CSV 파일 구조 검증"""
    logger.info("\n" + "="*60)
    logger.info("[List] CSV file structure verification")
    logger.info("="*60)
    
    files = {
        'attendance.csv': ['date', 'session', 'student_name', 'qr_code', 'timestamp', 'status'],
        'class_groups.csv': ['group_id', 'group_name', 'weekdays', 'start_time', 'end_time', 'start_date', 'end_date', 'total_hours'],
        'students.csv': ['name', 'qr_code', 'phone', 'school'],
        'student_groups.csv': ['student_name', 'group_id'],
        'schedule.csv': ['date', 'start', 'end', 'session'],
        'users.csv': ['user_id', 'username', 'password', 'role', 'name', 'phone', 'student_id', 'email']
    }
    
    for filename, expected_columns in files.items():
        if os.path.exists(filename):
            try:
                df = pd.read_csv(filename, encoding='utf-8-sig')
                actual_columns = list(df.columns)
                
                missing = set(expected_columns) - set(actual_columns)
                extra = set(actual_columns) - set(expected_columns)
                
                if missing or extra:
                    logger.warning(f"\n[!] {filename}:")
                    if missing:
                        logger.warning(f"   누락된 컬럼: {missing}")
                    if extra:
                        logger.warning(f"   추가 컬럼: {extra}")
                else:
                    logger.info(f"[OK] {filename}: normal ({len(df)} rows)")
                
            except Exception as e:
                logger.error(f"❌ {filename}: 읽기 실패 - {e}")
        else:
            logger.warning(f"⚠️ {filename}: 파일 없음")
    
    logger.info("="*60)


def main():
    """메인 실행 함수"""
    print("-" * 60)
    print("       QR 출석 시스템 CSV 표준화 도구")
    print("-" * 60)
    
    logger.info("[>>>] CSV standardization started...\n")
    
    # 1. 현재 상태 검증
    logger.info("=" * 60)
    logger.info("1단계: 현재 CSV 파일 상태 검증")
    logger.info("=" * 60)
    verify_csv_structure()
    
    # 2. 사용자 확인
    print("\n[!] Backup files will be automatically created.")
    while True:
        response = input("계속 진행하시겠습니까? (y/n): ").strip().lower()
        
        if response == 'y':
            logger.info("✅ 표준화를 시작합니다.")
            break
        elif response == 'n':
            logger.info("❌ 사용자가 취소했습니다.")
            return
        else:
            print("[!] Please enter 'y' or 'n'.")
            continue
    
    # 3. 표준화 실행
    logger.info("\n" + "=" * 60)
    logger.info("2단계: CSV 파일 표준화 실행")
    logger.info("=" * 60)
    
    standardize_attendance_csv()
    print()
    
    standardize_class_groups_csv()
    print()
    
    standardize_students_csv()
    print()
    
    standardize_schedule_csv()
    print()
    
    # 4. 최종 검증
    logger.info("\n" + "=" * 60)
    logger.info("3단계: 표준화 후 검증")
    logger.info("=" * 60)
    verify_csv_structure()
    
    logger.info("\n[OK] CSV standardization complete!")
    logger.info("[File] backups saved in .backup_YYYYMMDD_HHMMSS format.")


if __name__ == "__main__":
    main()

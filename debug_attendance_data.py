"""
출석 데이터 디버깅 스크립트
학부모 앱에서 출석 기록이 제대로 표시되지 않는 문제 진단
"""
import pandas as pd
from datetime import datetime, date, time, timedelta

print("="*80)
print("📊 출석 데이터 디버깅 스크립트")
print("="*80)
print()

# 1. 학생 정보 확인
print("1️⃣ 학생 정보 (students.csv)")
print("-" * 80)
try:
    df_students = pd.read_csv('students.csv', encoding='utf-8-sig')
    print(f"총 학생 수: {len(df_students)}명\n")
    print(df_students.to_string(index=False))
    print()
except Exception as e:
    print(f"❌ 오류: {e}\n")

# 2. 출석 기록 확인
print("\n2️⃣ 출석 기록 (attendance.csv)")
print("-" * 80)
try:
    df_attendance = pd.read_csv('attendance.csv', encoding='utf-8-sig')
    print(f"총 출석 기록: {len(df_attendance)}개\n")
    
    # 학생별 출석 횟수
    if not df_attendance.empty:
        print("📋 학생별 출석 기록 수:")
        student_counts = df_attendance['student_name'].value_counts()
        for student, count in student_counts.items():
            print(f"  - {student}: {count}회")
        print()
        
        # 전체 데이터 표시
        print("📊 전체 출석 기록:")
        print(df_attendance.to_string(index=False))
    print()
except Exception as e:
    print(f"❌ 오류: {e}\n")

# 3. 학생-그룹 매핑 확인
print("\n3️⃣ 학생-그룹 매핑 (student_groups.csv)")
print("-" * 80)
try:
    df_student_groups = pd.read_csv('student_groups.csv', encoding='utf-8-sig')
    print(f"총 매핑: {len(df_student_groups)}개\n")
    
    # 학생별 그룹
    if not df_student_groups.empty:
        print("📋 학생별 그룹 배정:")
        for idx, row in df_student_groups.iterrows():
            print(f"  - {row['student_name']}: 그룹 {row['group_id']}")
        print()
except Exception as e:
    print(f"❌ 오류: {e}\n")

# 4. 수업 그룹 정보
print("\n4️⃣ 수업 그룹 정보 (class_groups.csv)")
print("-" * 80)
try:
    df_class_groups = pd.read_csv('class_groups.csv', encoding='utf-8-sig')
    print(f"총 그룹 수: {len(df_class_groups)}개\n")
    
    if not df_class_groups.empty:
        print("📋 그룹 목록:")
        for idx, row in df_class_groups.iterrows():
            print(f"  - 그룹 {row['group_id']}: {row['group_name']}")
        print()
except Exception as e:
    print(f"❌ 오류: {e}\n")

# 5. 수업 일정
print("\n5️⃣ 수업 일정 (schedule.csv)")
print("-" * 80)
try:
    df_schedule = pd.read_csv('schedule.csv', encoding='utf-8-sig')
    print(f"총 일정: {len(df_schedule)}개\n")
    
    if not df_schedule.empty:
        print("📋 일정 목록:")
        print(df_schedule.to_string(index=False))
        print()
except Exception as e:
    print(f"❌ 오류: {e}\n")

# 6. 특정 학생 분석 (김정숙)
print("\n6️⃣ 특정 학생 상세 분석")
print("-" * 80)

student_name = "성소영"  # 실제 학생 이름
print(f"분석 대상: {student_name}\n")

try:
    # 학생 존재 확인
    df_students = pd.read_csv('students.csv', encoding='utf-8-sig')
    student = df_students[df_students['name'] == student_name]
    
    if student.empty:
        print(f"❌ '{student_name}' 학생을 찾을 수 없습니다!")
        print("\n💡 students.csv에 등록된 학생 목록:")
        for name in df_students['name'].unique():
            print(f"  - {name}")
    else:
        student_qr = student.iloc[0]['qr_code']
        print(f"✅ QR 코드: {student_qr}")
        
        # 그룹 배정 확인
        df_student_groups = pd.read_csv('student_groups.csv', encoding='utf-8-sig')
        student_group = df_student_groups[df_student_groups['student_name'] == student_name]
        
        if student_group.empty:
            print(f"⚠️ 그룹 미배정!")
        else:
            group_id = student_group.iloc[0]['group_id']
            print(f"✅ 배정 그룹 ID: {group_id}")
            
            # 그룹 정보
            df_class_groups = pd.read_csv('class_groups.csv', encoding='utf-8-sig')
            group = df_class_groups[df_class_groups['group_id'] == group_id]
            
            if not group.empty:
                print(f"✅ 그룹명: {group.iloc[0]['group_name']}")
                print(f"   시간: {group.iloc[0]['start_time']} ~ {group.iloc[0]['end_time']}")
        
        # 출석 기록 확인
        df_attendance = pd.read_csv('attendance.csv', encoding='utf-8-sig')
        
        # 이름으로 검색
        by_name = df_attendance[df_attendance['student_name'] == student_name]
        print(f"\n📊 이름으로 검색한 출석 기록: {len(by_name)}개")
        
        # QR 코드로 검색
        if 'qr_code' in df_attendance.columns:
            by_qr = df_attendance[df_attendance['qr_code'] == student_qr]
            print(f"📊 QR 코드로 검색한 출석 기록: {len(by_qr)}개")
            
            if not by_qr.empty:
                print("\n✅ 출석 기록 상세:")
                print(by_qr.to_string(index=False))
        
        # 그룹 일정과 매칭
        if not student_group.empty and not group.empty:
            print("\n7️⃣ 그룹 일정과 출석 기록 매칭 분석")
            print("-" * 80)
            
            group_name = group.iloc[0]['group_name']
            df_schedule = pd.read_csv('schedule.csv', encoding='utf-8-sig')
            
            # 해당 그룹의 일정
            group_schedule = df_schedule[df_schedule['session'].str.contains(group_name, na=False)]
            print(f"\n'{group_name}' 그룹의 전체 일정: {len(group_schedule)}개")
            
            if not group_schedule.empty:
                print("\n📅 그룹 일정:")
                print(group_schedule.to_string(index=False))
                
                # 날짜별 매칭 체크
                print("\n🔍 날짜별 출석 체크:")
                
                df_attendance['timestamp_dt'] = pd.to_datetime(df_attendance['timestamp'])
                df_attendance['date_only'] = df_attendance['timestamp_dt'].dt.date
                
                for _, sched in group_schedule.iterrows():
                    sched_date = pd.to_datetime(sched['date']).date()
                    sched_start = sched['start']
                    sched_end = sched['end']
                    
                    # 해당 날짜의 출석 기록
                    day_attendance = by_qr[by_qr['date_only'] == sched_date]
                    
                    if day_attendance.empty:
                        print(f"  ❌ {sched_date} ({sched_start}~{sched_end}): 출석 기록 없음")
                    else:
                        for _, att in day_attendance.iterrows():
                            att_time = att['timestamp_dt'].strftime('%H:%M:%S')
                            print(f"  ✅ {sched_date} ({sched_start}~{sched_end}): {att['status']} at {att_time}")
                            
                            # 시간 범위 체크
                            start_hour, start_min = map(int, sched_start.split(':'))
                            end_hour, end_min = map(int, sched_end.split(':'))
                            
                            buffer_start = datetime.combine(sched_date, time(start_hour, start_min)) - timedelta(minutes=30)
                            buffer_end = datetime.combine(sched_date, time(end_hour, end_min)) + timedelta(minutes=15)
                            
                            att_datetime = att['timestamp_dt']
                            
                            if buffer_start <= att_datetime <= buffer_end:
                                print(f"     ✅ 시간 범위 내 (버퍼: {buffer_start.strftime('%H:%M')} ~ {buffer_end.strftime('%H:%M')})")
                            else:
                                print(f"     ❌ 시간 범위 밖! (버퍼: {buffer_start.strftime('%H:%M')} ~ {buffer_end.strftime('%H:%M')})")
                                print(f"        출석 시간: {att_datetime}")

except Exception as e:
    print(f"❌ 오류: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("✅ 분석 완료!")
print("="*80)

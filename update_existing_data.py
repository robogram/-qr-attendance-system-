"""
기존 데이터 업데이트 스크립트
class_groups.csv에 total_hours 컬럼 추가
"""
import pandas as pd
import os
from datetime import datetime, timedelta

CLASS_GROUPS_CSV = "class_groups.csv"

def update_class_groups_csv():
    """class_groups.csv에 total_hours 컬럼 추가 및 자동 계산"""
    
    if not os.path.exists(CLASS_GROUPS_CSV):
        print("❌ class_groups.csv 파일이 없습니다.")
        return
    
    try:
        # CSV 로드
        df = pd.read_csv(CLASS_GROUPS_CSV, encoding='utf-8-sig')
        
        print(f"📊 현재 그룹 수: {len(df)}개")
        
        # total_hours 컬럼이 이미 있는지 확인
        if 'total_hours' in df.columns:
            print("✅ total_hours 컬럼이 이미 존재합니다.")
            
            # None 또는 NaN 값이 있으면 자동 계산
            needs_calculation = df['total_hours'].isna().sum()
            
            if needs_calculation > 0:
                print(f"⚠️ {needs_calculation}개 그룹의 교육시간을 자동 계산합니다...")
            else:
                print("✅ 모든 그룹의 교육시간이 설정되어 있습니다.")
                return
        else:
            print("➕ total_hours 컬럼을 추가합니다...")
            df['total_hours'] = None
        
        # 각 그룹의 교육시간 계산
        for idx, row in df.iterrows():
            if pd.isna(row.get('total_hours')):
                try:
                    # 1회 수업 시간 계산
                    start_time = datetime.strptime(row['start_time'], '%H:%M').time()
                    end_time = datetime.strptime(row['end_time'], '%H:%M').time()
                    
                    start_dt = datetime.combine(datetime.today(), start_time)
                    end_dt = datetime.combine(datetime.today(), end_time)
                    duration_hours = (end_dt - start_dt).total_seconds() / 3600
                    
                    # 수업 횟수 계산
                    weekdays = [int(x) for x in str(row['weekdays']).split(',')]
                    start_date = pd.to_datetime(row['start_date']).date()
                    end_date = pd.to_datetime(row['end_date']).date()
                    
                    classes_count = 0
                    current_date = start_date
                    
                    while current_date <= end_date:
                        if current_date.weekday() in weekdays:
                            classes_count += 1
                        current_date += timedelta(days=1)
                    
                    # 총 교육시간
                    total_hours = round(duration_hours * classes_count, 1)
                    
                    # 1시간 미만은 1시간으로
                    if total_hours < 1:
                        total_hours = 1.0
                    
                    df.at[idx, 'total_hours'] = total_hours
                    
                    print(f"✅ {row['group_name']}: {total_hours}시간 ({duration_hours:.1f}h × {classes_count}회)")
                
                except Exception as e:
                    print(f"❌ {row.get('group_name', '?')} 계산 실패: {e}")
                    df.at[idx, 'total_hours'] = 1.0
        
        # 저장
        df.to_csv(CLASS_GROUPS_CSV, index=False, encoding='utf-8-sig')
        print(f"\n✅ {CLASS_GROUPS_CSV} 업데이트 완료!")
        
        # 결과 확인
        print("\n📋 최종 결과:")
        print(df[['group_name', 'start_time', 'end_time', 'start_date', 'end_date', 'total_hours']])
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")


if __name__ == "__main__":
    print("🔧 기존 데이터 업데이트 시작...\n")
    update_class_groups_csv()
    print("\n✅ 모든 업데이트 완료!")

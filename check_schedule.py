"""
schedule.csv 내용 확인 스크립트
A반 일정이 있는지 확인합니다.
"""
import pandas as pd
import os

SCHEDULE_CSV = "schedule.csv"

def check_schedule():
    """일정 확인"""
    
    if not os.path.exists(SCHEDULE_CSV):
        print(f"❌ {SCHEDULE_CSV} 파일이 없습니다.")
        return
    
    try:
        # CSV 읽기
        df = pd.read_csv(SCHEDULE_CSV, encoding='utf-8-sig')
        
        print("="*60)
        print("📅 Schedule.csv 내용 확인")
        print("="*60)
        print(f"총 일정 수: {len(df)}개")
        print()
        
        # 전체 내용 출력
        print("📋 전체 일정:")
        print("-"*60)
        for idx, row in df.iterrows():
            print(f"{idx+1}. {row['date']} | {row['start']}~{row['end']} | {row['session']}")
        
        print()
        print("="*60)
        
        # A반 일정 찾기
        a_class = df[df['session'].str.contains('A반', na=False)]
        
        if not a_class.empty:
            print("✅ A반 일정을 찾았습니다!")
            print("-"*60)
            for idx, row in a_class.iterrows():
                print(f"📅 {row['date']} | {row['start']}~{row['end']} | {row['session']}")
            print()
        else:
            print("❌ A반 일정이 없습니다!")
            print()
            print("💡 해결 방법:")
            print("   1. schedule.csv에 다음 줄을 추가:")
            print("      2025-10-13,16:50,17:00,A반")
            print()
            print("   2. 또는 regenerate_schedule.py 실행")
            print()
        
        print("="*60)
        
        # 수업별 통계
        print("\n📊 수업별 일정 수:")
        print("-"*60)
        session_counts = df['session'].value_counts()
        for session, count in session_counts.items():
            print(f"  {session}: {count}회")
        
        print("="*60)
        
        # 날짜별 통계
        print("\n📆 날짜별 일정:")
        print("-"*60)
        date_counts = df['date'].value_counts().sort_index()
        for date, count in date_counts.items():
            print(f"  {date}: {count}개 수업")
        
        print("="*60)
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║       📅 일정 확인 도구                                  ║
║                                                           ║
║   schedule.csv의 내용을 확인합니다.                       ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    check_schedule()

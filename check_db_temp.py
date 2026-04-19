from utils import get_supabase_client
import pandas as pd
import sys

def check_students():
    try:
        supabase = get_supabase_client()
        res = supabase.table('students').select('*').execute()
        df = pd.DataFrame(res.data)
        print("--- DB 학생 명단 (상위 30명) ---")
        if not df.empty:
            print(df[['name', 'group_id']].head(30))
        else:
            print("학생 데이터가 없습니다.")
        
        # 4/18 출석 기록 확인
        res_att = supabase.table('attendance').select('*').eq('date', '2026-04-18').execute()
        df_att = pd.DataFrame(res_att.data)
        print("\n--- 2026-04-18 현재 출석 기록 수 ---")
        print(len(df_att))
        if not df_att.empty:
            print(df_att[['student_id', 'status', 'type']].head(10))
            
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    check_students()

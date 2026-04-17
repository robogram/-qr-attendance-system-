import pandas as pd
import json
import os
from supabase_client import supabase_mgr

USERS_CSV = "users.csv"

def migrate():
    print("🚀 시작: 사용자 데이터 Supabase 클라우드 마이그레이션...")
    
    if not supabase_mgr.client:
        print("❌ Supabase 클라이언트 연결 실패. .env 설정을 확인하세요.")
        return
        
    if not os.path.exists(USERS_CSV):
        print("❌ 로컬에 users.csv 파일이 없습니다. 업로드할 데이터가 없습니다.")
        return
        
    try:
        # Load local csv safely
        encodings = ['utf-8-sig', 'utf-8', 'cp949', 'euc-kr']
        df = None
        for enc in encodings:
            try:
                df = pd.read_csv(USERS_CSV, encoding=enc)
                break
            except Exception:
                pass
                
        if df is None:
            print("❌ users.csv를 읽을 수 없습니다.")
            return
            
        print(f"✅ 로컬 데이터 로드 완료: 총 {len(df)}건")
        
        success_count = 0
        error_count = 0
        
        # Loop over rows and insert/upsert to Supabase
        for idx, row in df.iterrows():
            # CSV column mapping to Supabase columns
            user_data = {
                'username': str(row.get('username', '')),
                'password': str(row.get('password', '')),
                'role': str(row.get('role', 'student')),
                'name': str(row.get('name', '')) if pd.notna(row.get('name')) else "",
                'phone': str(row.get('phone', '')) if pd.notna(row.get('phone')) else "",
                'student_id': str(row.get('student_id', '')) if pd.notna(row.get('student_id')) else "",
                'email': str(row.get('email', '')) if pd.notna(row.get('email')) else ""
            }
            
            # 중복 체크
            existing = supabase_mgr.get_user_by_username(user_data['username'])
            if existing:
                # Update
                try:
                    supabase_mgr.client.table('users').update(user_data).eq('username', user_data['username']).execute()
                    success_count += 1
                except Exception as e:
                    print(f"업데이트 실패 ({user_data['username']}): {e}")
                    error_count += 1
            else:
                # Insert
                try:
                    supabase_mgr.client.table('users').insert(user_data).execute()
                    success_count += 1
                except Exception as e:
                    print(f"삽입 실패 ({user_data['username']}): {e}")
                    error_count += 1
        
        print("\n" + "="*40)
        print("🎯 마이그레이션 작업 결과")
        print("="*40)
        print(f"총 데이터: {len(df)} 건")
        print(f"✅ 전송 성공: {success_count} 건")
        print(f"❌ 전송 실패: {error_count} 건")
        if error_count == 0:
            print("\n🎉 모든 사용자 데이터가 퍼펙트하게 클라우드로 올라갔습니다!")
        else:
            print("\n⚠️ 일부 데이터 전송에 실패했습니다. 로그를 참조하세요.")
        
    except Exception as e:
        print(f"❌ 예기치 않은 오류 발생: {e}")

if __name__ == "__main__":
    migrate()

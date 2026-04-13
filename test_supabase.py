from supabase_client import supabase_mgr

def test_connection():
    try:
        if supabase_mgr.client is None:
            print("❌ Supabase 클라이언트 초기화 실패 (환경 변수 확인 요망)")
            return
            
        # 간단한 쿼리 테스트 (테이블이 비어있어도 에러가 나지 않는지 확인)
        result = supabase_mgr.client.table('students').select('count', count='exact').limit(1).execute()
        print("✅ Supabase 연결 테스트 성공!")
        print(f"Data: {result.data}")
    except Exception as e:
        print(f"❌ Supabase 연결 테스트 실패: {e}")

if __name__ == "__main__":
    test_connection()

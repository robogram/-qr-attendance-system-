# qr_attendance/login.py
import csv
import os

def login(username, password):
    """
    CSV 기반 로그인 - 평문 비교
    """
    csv_path = 'users.csv'
    
    try:
        # BOM 제거를 위해 utf-8-sig 사용
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for user in reader:
                # 공백 제거 (키와 값 모두)
                user = {k.strip(): v.strip() if isinstance(v, str) else v 
                       for k, v in user.items()}
                
                # 평문 비교
                if user.get('username') == username and user.get('password') == password:
                    print(f"✅ 로그인 성공: {user.get('name', 'Unknown')} ({user.get('role', 'Unknown')})")
                    
                    return {
                        'success': True,
                        'user_id': user.get('user_id', ''),  # 🔥 BOM 제거 후 정상 작동
                        'role': user.get('role', ''),
                        'name': user.get('name', ''),
                        'username': user.get('username', ''),
                        'email': user.get('email', ''),
                        'phone': user.get('phone', ''),
                        'student_id': user.get('student_id', '')
                    }
        
        print("❌ 로그인 실패: 사용자 정보가 일치하지 않습니다")
        return {
            'success': False, 
            'message': '아이디 또는 비밀번호가 틀립니다'
        }
        
    except FileNotFoundError:
        print(f"❌ 파일 없음: {csv_path}")
        return {
            'success': False,
            'message': 'users.csv 파일을 찾을 수 없습니다'
        }
    except Exception as e:
        import traceback
        print(f"❌ 오류 상세:")
        traceback.print_exc()
        return {
            'success': False,
            'message': f'로그인 오류: {str(e)}'
        }


def get_user_by_id(user_id):
    """사용자 ID로 사용자 정보 조회"""
    csv_path = 'users.csv'
    
    try:
        # BOM 제거
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for user in reader:
                user = {k.strip(): v.strip() if isinstance(v, str) else v 
                       for k, v in user.items()}
                
                if user.get('user_id') and str(user.get('user_id')) == str(user_id):
                    return user
        return None
    except Exception as e:
        print(f"❌ 오류: {e}")
        return None


def get_user_by_username(username):
    """사용자명으로 사용자 정보 조회"""
    csv_path = 'users.csv'
    
    try:
        # BOM 제거
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for user in reader:
                user = {k.strip(): v.strip() if isinstance(v, str) else v 
                       for k, v in user.items()}
                
                if user.get('username') == username:
                    return user
        return None
    except Exception as e:
        print(f"❌ 오류: {e}")
        return None


def get_users_by_role(role):
    """역할별 사용자 목록 조회"""
    csv_path = 'users.csv'
    users = []
    
    try:
        # BOM 제거
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for user in reader:
                user = {k.strip(): v.strip() if isinstance(v, str) else v 
                       for k, v in user.items()}
                
                if user.get('role') == role:
                    users.append(user)
        return users
    except Exception as e:
        print(f"❌ 오류: {e}")
        return []


def list_all_users():
    """모든 사용자 목록 출력 (디버깅용)"""
    csv_path = 'users.csv'
    
    try:
        # BOM 제거
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            print(f"\n{'='*70}")
            print(f"📋 전체 사용자 목록 ({csv_path})")
            print(f"{'='*70}")
            
            users_by_role = {'admin': [], 'teacher': [], 'parent': [], 'student': []}
            
            for user in reader:
                # 키 정리
                user = {k.strip(): v for k, v in user.items()}
                role = user.get('role', 'unknown').strip()
                if role in users_by_role:
                    users_by_role[role].append(user)
            
            total = 0
            for role, users in users_by_role.items():
                if users:
                    print(f"\n【{role.upper()}】 ({len(users)}명)")
                    for user in users:
                        user_id = user.get('user_id', '?')
                        username = user.get('username', '?')
                        name = user.get('name', '?')
                        phone = user.get('phone', '?')
                        print(f"  ID:{user_id:3} | {username:18} | {name:12} | {phone}")
                    total += len(users)
            
            print(f"\n📊 총 사용자: {total}명")
            print(f"{'='*70}\n")
    except Exception as e:
        print(f"❌ 오류: {e}")


# 테스트 코드
if __name__ == "__main__":
    print("=" * 70)
    print("로보그램 출석관리 시스템 - 로그인 테스트")
    print("=" * 70)
    
    # 전체 사용자 목록 출력
    list_all_users()
    
    # 1. Admin 로그인
    print("【1. Admin 로그인 테스트】")
    result = login("admin", "admin123")
    print(f"✅ user_id: '{result.get('user_id')}' (비어있지 않아야 함)")
    print(f"   role: {result.get('role')}")
    print(f"   name: {result.get('name')}\n")
    
    # 2. Teacher 로그인
    print("【2. Teacher 로그인 테스트】")
    result = login("teacher1", "teacher123")
    print(f"✅ user_id: '{result.get('user_id')}'")
    print(f"   role: {result.get('role')}\n")
    
    # 3. ID로 조회 테스트
    print("【3. ID로 사용자 조회 테스트】")
    user = get_user_by_id("1")
    if user:
        print(f"✅ 찾음: {user.get('name')} ({user.get('username')})")
    else:
        print(f"❌ 못 찾음")
    print()
    
    # 4. username으로 조회 테스트
    print("【4. Username으로 사용자 조회 테스트】")
    user = get_user_by_username("teacher1")
    if user:
        print(f"✅ 찾음: {user.get('name')} (ID: {user.get('user_id')})")
    else:
        print(f"❌ 못 찾음")
    print()
    
    # 5. 역할별 조회 테스트
    print("【5. 역할별 사용자 조회 테스트】")
    teachers = get_users_by_role('teacher')
    print(f"✅ 교사 {len(teachers)}명 찾음:")
    for t in teachers:
        print(f"   - {t.get('name')} ({t.get('username')})")
    print()
    
    # 6. 잘못된 로그인
    print("【6. 잘못된 비밀번호 테스트】")
    result = login("admin", "wrongpassword")
    print(f"결과: {result.get('message')}\n")
    
    print("=" * 70)
    print("✅ 모든 테스트 완료!")
    print("=" * 70)

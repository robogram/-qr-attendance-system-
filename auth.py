"""
인증 및 권한 관리 시스템
"""
import pandas as pd
import hashlib
import os
from datetime import datetime, timedelta

USERS_CSV = "users.csv"

# 사용자 역할별 권한 정의
PERMISSIONS = {
    'admin': {
        'can_manage_students': True,
        'can_manage_schedule': True,
        'can_manage_users': True,
        'can_view_all_students': True,
        'can_export_data': True,
        'can_delete_data': True,
        'can_view_reports': True,
        'can_check_attendance': True
    },
    'teacher': {
        'can_manage_students': False,
        'can_manage_schedule': False,
        'can_manage_users': False,
        'can_view_all_students': True,
        'can_export_data': True,
        'can_delete_data': False,
        'can_view_reports': True,
        'can_check_attendance': True
    },
    'parent': {
        'can_manage_students': False,
        'can_manage_schedule': False,
        'can_manage_users': False,
        'can_view_all_students': False,  # 내 자녀만
        'can_export_data': False,
        'can_delete_data': False,
        'can_view_reports': False,  # 내 자녀 리포트만
        'can_check_attendance': False
    },
    'student': {
        'can_manage_students': False,
        'can_manage_schedule': False,
        'can_manage_users': False,
        'can_view_all_students': False,  # 본인만
        'can_export_data': False,
        'can_delete_data': False,
        'can_view_reports': False,  # 본인 리포트만
        'can_check_attendance': False
    }
}

# 기본 관리자/테스트 계정 (users.csv 없을 때 fallback용)
DEFAULT_ACCOUNTS = [
    {'user_id': 1, 'username': 'admin', 'password': 'admin123', 'role': 'admin', 'name': '관리자', 'phone': '010-0000-0000', 'student_id': '', 'email': 'admin@robogram.co.kr'},
    {'user_id': 2, 'username': 'teacher1', 'password': 'teacher123', 'role': 'teacher', 'name': '선생님', 'phone': '010-1111-1111', 'student_id': '', 'email': 'teacher1@robogram.co.kr'},
    {'user_id': 3, 'username': 'parent1', 'password': 'parent123', 'role': 'parent', 'name': '학부모', 'phone': '010-2222-2222', 'student_id': '', 'email': 'parent1@robogram.co.kr'},
    {'user_id': 4, 'username': 'student1', 'password': 'student123', 'role': 'student', 'name': '학생', 'phone': '010-3333-3333', 'student_id': 'student1', 'email': ''},
]

def load_users():
    """사용자 목록 로드 (자동 인코딩 감지 + 기본 계정 fallback)"""
    default_df = pd.DataFrame(DEFAULT_ACCOUNTS)
    
    if not os.path.exists(USERS_CSV):
        return default_df
    
    # 여러 인코딩 시도
    encodings = ['utf-8-sig', 'utf-8', 'cp949', 'euc-kr', 'latin1']
    
    for encoding in encodings:
        try:
            df = pd.read_csv(USERS_CSV, encoding=encoding)
            # 성공하면 UTF-8로 다시 저장 시도 (읽기 전용 환경이면 무시)
            try:
                df.to_csv(USERS_CSV, index=False, encoding='utf-8-sig')
            except Exception:
                pass
            return df
        except (UnicodeDecodeError, Exception):
            continue
    
    # 모든 인코딩 실패 시 기본 계정 반환
    return default_df


def authenticate_user(username, password):
    """
    사용자 인증
    
    Args:
        username: 사용자명
        password: 비밀번호
    
    Returns:
        dict: 사용자 정보 또는 None
    """
    # 먼저 CSV에서 찾기
    df_users = load_users()
    
    # 사용자 찾기
    user = df_users[
        (df_users['username'] == username) & 
        (df_users['password'] == password)
    ]
    
    if not user.empty:
        return user.iloc[0].to_dict()
    
    # CSV에 없으면 기본 계정에서 찾기 (HF 배포 환경 대비)
    for account in DEFAULT_ACCOUNTS:
        if account['username'] == username and account['password'] == password:
            return account
    
    return None


def check_permission(user_role, permission):
    """
    권한 확인
    
    Args:
        user_role: 사용자 역할 (admin, teacher, parent, student)
        permission: 확인할 권한
    
    Returns:
        bool: 권한 여부
    """
    return PERMISSIONS.get(user_role, {}).get(permission, False)


def get_user_by_id(user_id):
    """사용자 ID로 사용자 정보 조회"""
    df_users = load_users()
    user = df_users[df_users['user_id'] == user_id]
    
    if user.empty:
        return None
    
    return user.iloc[0].to_dict()


def get_user_by_username(username):
    """사용자명으로 사용자 정보 조회"""
    df_users = load_users()
    user = df_users[df_users['username'] == username]
    
    if user.empty:
        return None
    
    return user.iloc[0].to_dict()


def create_user(username, password, role, name, phone='', student_id='', email=''):
    """
    새 사용자 생성
    
    Args:
        username: 사용자명 (로그인 ID)
        password: 비밀번호
        role: 역할 (admin, teacher, parent, student)
        name: 실명
        phone: 전화번호 (선택)
        student_id: 학생 ID - parent나 student 역할일 경우
        email: 이메일 (선택)
    
    Returns:
        dict: 생성된 사용자 정보 또는 None
    """
    df_users = load_users()
    
    # 중복 확인
    if not df_users[df_users['username'] == username].empty:
        return None
    
    # 새 사용자 ID 생성
    new_id = df_users['user_id'].max() + 1 if not df_users.empty else 1
    
    # 새 사용자 추가
    new_user = {
        'user_id': new_id,
        'username': username,
        'password': password,  # 실제로는 해시화 필요
        'role': role,
        'name': name,
        'phone': phone,
        'student_id': student_id,
        'email': email
    }
    
    df_users = pd.concat([df_users, pd.DataFrame([new_user])], ignore_index=True)
    df_users.to_csv(USERS_CSV, index=False, encoding='utf-8-sig')
    
    return new_user


def update_user(user_id, **kwargs):
    """사용자 정보 업데이트"""
    df_users = load_users()
    
    if user_id not in df_users['user_id'].values:
        return False
    
    for key, value in kwargs.items():
        if key in df_users.columns:
            df_users.loc[df_users['user_id'] == user_id, key] = value
    
    df_users.to_csv(USERS_CSV, index=False, encoding='utf-8-sig')
    return True


def delete_user(user_id):
    """사용자 삭제"""
    df_users = load_users()
    
    # admin은 삭제 불가
    user = df_users[df_users['user_id'] == user_id]
    if user.empty or user.iloc[0]['role'] == 'admin':
        return False
    
    df_users = df_users[df_users['user_id'] != user_id]
    df_users.to_csv(USERS_CSV, index=False, encoding='utf-8-sig')
    return True


def get_students_by_parent(parent_name):
    """학부모의 자녀 목록 조회"""
    df_users = load_users()
    parent = df_users[df_users['name'] == parent_name]
    
    if parent.empty:
        return []
    
    student_ids = parent['student_id'].tolist()
    # 쉼표로 구분된 여러 자녀 지원
    all_student_ids = []
    for sid in student_ids:
        if pd.notna(sid) and sid:
            all_student_ids.extend([s.strip() for s in str(sid).split(',')])
    
    return all_student_ids


def hash_password(password):
    """
    비밀번호 해시화 (실제 배포 시 사용)
    
    Args:
        password: 평문 비밀번호
    
    Returns:
        str: 해시화된 비밀번호
    """
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password, hashed):
    """비밀번호 확인"""
    return hash_password(password) == hashed


def get_role_display_name(role):
    """역할 한글명 반환"""
    role_names = {
        'admin': '👨‍💼 관리자',
        'teacher': '👩‍🏫 선생님',
        'parent': '👨‍👩‍👧 학부모',
        'student': '🧒 학생'
    }
    return role_names.get(role, role)


def get_role_home_page(role):
    """역할별 홈페이지 URL"""
    return f"/{role}"


def require_role(allowed_roles):
    """
    데코레이터: 특정 역할만 접근 가능
    
    Usage:
        @require_role(['admin', 'teacher'])
        def some_function():
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            import streamlit as st
            
            if 'user' not in st.session_state:
                st.error("로그인이 필요합니다.")
                st.stop()
            
            user_role = st.session_state.user.get('role')
            if user_role not in allowed_roles:
                st.error("접근 권한이 없습니다.")
                st.stop()
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_permission(permission):
    """
    데코레이터: 특정 권한이 있어야 접근 가능
    
    Usage:
        @require_permission('can_manage_students')
        def some_function():
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            import streamlit as st
            
            if 'user' not in st.session_state:
                st.error("로그인이 필요합니다.")
                st.stop()
            
            user_role = st.session_state.user.get('role')
            if not check_permission(user_role, permission):
                st.error("이 작업을 수행할 권한이 없습니다.")
                st.stop()
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

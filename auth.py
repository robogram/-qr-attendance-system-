"""
인증 및 권한 관리 시스템 (Supabase Migration Version)
"""
import pandas as pd
import hashlib
import os
from datetime import datetime, timedelta
from supabase_client import supabase_mgr

# 이제 CSV를 보지 않지만, 시스템상 레거시가 남아있을 수 있어 변수만 남김
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

# 기본 관리자/테스트 계정 (Supabase 응답이 비어있을 때 fallback용)
DEFAULT_ACCOUNTS = [
    {'user_id': 1, 'username': 'admin', 'password': 'admin123', 'role': 'admin', 'name': '관리자', 'phone': '010-0000-0000', 'student_id': '', 'email': 'admin@robogram.co.kr'},
    {'user_id': 2, 'username': 'teacher1', 'password': 'teacher123', 'role': 'teacher', 'name': '선생님', 'phone': '010-1111-1111', 'student_id': '', 'email': 'teacher1@robogram.co.kr'},
    {'user_id': 3, 'username': 'parent1', 'password': 'parent123', 'role': 'parent', 'name': '학부모', 'phone': '010-2222-2222', 'student_id': '', 'email': 'parent1@robogram.co.kr'},
    {'user_id': 4, 'username': 'student1', 'password': 'student123', 'role': 'student', 'name': '학생', 'phone': '010-3333-3333', 'student_id': 'student1', 'email': ''},
]

def load_users():
    """사용자 목록 로드 (Supabase 기반)"""
    users_data = supabase_mgr.get_all_users()
    
    if not users_data:
        return pd.DataFrame(DEFAULT_ACCOUNTS)
        
    df = pd.DataFrame(users_data)
    # 기존 코드 호환성을 위해 Supabase의 'id'를 'user_id'로 복제
    if 'id' in df.columns:
        df['user_id'] = df['id']
    return df


def authenticate_user(username, password):
    """
    사용자 인증 (Supabase 기반)
    """
    user = supabase_mgr.get_user_by_username(username)
    if user and user.get('password') == password:
        user['user_id'] = user.get('id')  # 호환성
        return user
        
    # Supabase에 없으면 기본 계정에서 찾기 (fallback)
    for account in DEFAULT_ACCOUNTS:
        if account['username'] == username and account['password'] == password:
            return account
    
    return None


def check_permission(user_role, permission):
    return PERMISSIONS.get(user_role, {}).get(permission, False)


def get_user_by_id(user_id):
    """사용자 ID로 사용자 정보 조회"""
    user = supabase_mgr.get_user_by_id(user_id)
    if user:
        user['user_id'] = user.get('id')
    return user


def get_user_by_username(username):
    """사용자명으로 사용자 정보 조회"""
    user = supabase_mgr.get_user_by_username(username)
    if user:
        user['user_id'] = user.get('id')
    return user


def create_user(username, password, role, name, phone='', student_id='', email=''):
    """새 사용자 생성 (Supabase)"""
    # 중복 확인
    existing = supabase_mgr.get_user_by_username(username)
    if existing:
        return None
        
    user_data = {
        'username': username,
        'password': password,
        'role': role,
        'name': name,
        'phone': phone,
        'student_id': student_id,
        'email': email
    }
    
    res = supabase_mgr.insert_user(user_data)
    if res:
        res['user_id'] = res.get('id')
        return res
    return None


def update_user(user_id, **kwargs):
    """사용자 정보 업데이트"""
    user_data = {}
    valid_keys = ['username', 'password', 'role', 'name', 'phone', 'student_id', 'email']
    
    for key, value in kwargs.items():
        if key in valid_keys:
            user_data[key] = value
            
    if user_data:
        return supabase_mgr.update_user(user_id, user_data)
    return False


def delete_user(user_id):
    """사용자 삭제"""
    # admin은 삭제 불가 점검
    user = get_user_by_id(user_id)
    if not user or user.get('role') == 'admin':
        return False
        
    return supabase_mgr.delete_user(user_id)


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
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def get_role_display_name(role):
    role_names = {
        'admin': '👨‍💼 관리자',
        'teacher': '👩‍🏫 선생님',
        'parent': '👨‍👩‍👧 학부모',
        'student': '🧒 학생'
    }
    return role_names.get(role, role)

def get_role_home_page(role):
    return f"/{role}"

def require_role(allowed_roles):
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

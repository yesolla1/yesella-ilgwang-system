"""
예설라 일광원 입학 상담 관리 시스템
Streamlit + Supabase 기반
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import bcrypt
from supabase import create_client, Client

# ============================================
# 페이지 설정
# ============================================
st.set_page_config(
    page_title="예설라 일광원 관리 시스템",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# Supabase 연결
# ============================================
@st.cache_resource
def init_supabase() -> Client:
    """Supabase 클라이언트 초기화"""
    try:
        supabase_url = st.secrets["supabase"]["url"]
        supabase_key = st.secrets["supabase"]["key"]
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        st.error(f"⚠️ Supabase 연결 실패: {e}")
        st.info("💡 .streamlit/secrets.toml 파일에 Supabase 설정을 추가해주세요.")
        st.stop()

supabase = init_supabase()

# ============================================
# 세션 상태 초기화
# ============================================
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'role' not in st.session_state:
    st.session_state.role = None

# ============================================
# 인증 함수
# ============================================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def hash_password(password: str) -> str:
    """비밀번호 해시화"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def login(username: str, password: str) -> tuple:
    """로그인 처리"""
    try:
        response = supabase.table('users').select('*').eq('username', username).eq('is_active', True).execute()
        
        if response.data and len(response.data) > 0:
            user = response.data[0]
            if verify_password(password, user['password_hash']):
                return True, user
        return False, None
    except Exception as e:
        st.error(f"로그인 오류: {e}")
        return False, None

def logout():
    """로그아웃"""
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.role = None
    st.rerun()

def can_modify():
    """수정 권한 확인"""
    if st.session_state.role == 'admin':
        return True
    if st.session_state.user and st.session_state.user.get('can_modify', False):
        return True
    return False

# ============================================
# 로그인 화면
# ============================================
def show_login_page():
    """로그인 페이지"""
    st.markdown("# 📚 예설라 일광원 관리 시스템")
    st.markdown("### 🔐 로그인")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            username = st.text_input("아이디", placeholder="admin")
            password = st.text_input("비밀번호", type="password", placeholder="********")
            submit = st.form_submit_button("로그인", use_container_width=True)
            
            if submit:
                if username and password:
                    success, user = login(username, password)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        st.session_state.role = user['role']
                        st.success(f"✅ {user['full_name']}님, 환영합니다!")
                        st.rerun()
                    else:
                        st.error("❌ 아이디 또는 비밀번호가 올바르지 않습니다.")
                else:
                    st.warning("아이디와 비밀번호를 입력해주세요.")
        
        st.markdown("---")
        st.info("""
        **기본 계정 정보**
        - 아이디: `admin`
        - 비밀번호: `admin123`
        
        ⚠️ 최초 로그인 후 반드시 비밀번호를 변경하세요.
        """)


# ============================================
# 모듈 임포트
# ============================================
from modules_students import show_dashboard, show_student_management
from modules_ocr_schedule import show_ocr_module, show_smart_schedule
from modules_users import show_user_management

# ============================================
# 메인 애플리케이션
# ============================================
def main():
    """메인 애플리케이션"""
    
    if not st.session_state.authenticated:
        show_login_page()
        return
    
    with st.sidebar:
        st.markdown(f"### 👋 {st.session_state.user['full_name']}님")
        st.markdown(f"**역할:** {'🔑 관리자' if st.session_state.role == 'admin' else '👤 직원'}")
        
        can_modify_status = False
        if st.session_state.role == 'admin':
            can_modify_status = True
        elif st.session_state.user and st.session_state.user.get('can_modify', False):
            can_modify_status = True
        
        st.markdown(f"**권한:** {'✏️ 수정 가능' if can_modify_status else '👁️ 조회 전용'}")
        st.markdown("---")
        
        menu_options = ["📊 대시보드", "👥 학생 관리", "📄 OCR 처리", "📅 스마트 시간표"]
        if st.session_state.role == 'admin':
            menu_options.append("👤 사용자 관리")
        
        menu = st.radio("메뉴", menu_options)
        
        st.markdown("---")
        
        if st.button("🚪 로그아웃", use_container_width=True):
            logout()
    
    if menu == "📊 대시보드":
        show_dashboard(supabase)
    elif menu == "👥 학생 관리":
        show_student_management(supabase)
    elif menu == "📄 OCR 처리":
        show_ocr_module(supabase)
    elif menu == "📅 스마트 시간표":
        show_smart_schedule(supabase)
    elif menu == "👤 사용자 관리":
        show_user_management(supabase)

if __name__ == "__main__":
    main()

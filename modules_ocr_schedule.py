"""
OCR 및 스마트 스케줄 모듈 (OpenAI Vision API 사용)
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import base64
import json


def can_modify():
    """수정 권한 확인"""
    if st.session_state.role == 'admin':
        return True
    if st.session_state.user and st.session_state.user.get('can_modify', False):
        return True
    return False


def process_ocr_with_openai(image_file, openai_api_key):
    """OpenAI Vision API를 사용한 OCR 처리"""
    try:
        import requests
        
        # 이미지를 base64로 인코딩
        image_bytes = image_file.read()
        image_file.seek(0)  # 파일 포인터 리셋
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # OpenAI Vision API 호출
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {openai_api_key}"
        }
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """이 이미지는 초등학교 독서 학원 입학원서입니다. 다음 정보를 추출해주세요:

1. 학생명
2. 학년 (초1~초6 형식)
3. 학부모 연락처
4. 희망 수업 시간
5. 독서 습관이나 특이사항
6. 파란색으로 표시된 중요 메모 (있는 경우)

JSON 형식으로 응답해주세요:
{
  "name": "학생명",
  "grade": "초X",
  "parent_phone": "010-XXXX-XXXX",
  "preferred_times": ["월 14:00", "화 15:00"],
  "reading_habit": "독서 습관 설명",
  "special_notes": "특이사항",
  "blue_notes": "파란색 메모"
}"""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1000
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # JSON 파싱
            try:
                # 코드 블록 제거
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()
                
                ocr_data = json.loads(content)
                return True, ocr_data, content
            except json.JSONDecodeError:
                return True, {}, content
        else:
            return False, None, f"API 오류: {response.status_code} - {response.text}"
            
    except Exception as e:
        return False, None, str(e)


def show_ocr_module(supabase):
    """OCR 처리 페이지 (OpenAI Vision API 사용)"""
    st.title("📄 수기 원서 OCR 처리")
    
    if not can_modify():
        st.warning("⚠️ 조회 전용 계정입니다. OCR 처리는 관리자 권한이 필요합니다.")
        return
    
    # OpenAI API 키 확인
    openai_api_key = st.secrets.get("openai", {}).get("api_key", "")
    
    if not openai_api_key:
        st.error("⚠️ OpenAI API 키가 설정되지 않았습니다.")
        st.info("""
        **설정 방법:**
        1. Streamlit Cloud 앱 페이지 → Settings → Secrets
        2. 다음 내용 추가:
        ```
        [openai]
        api_key = "sk-your-api-key-here"
        ```
        """)
        return
    
    st.info("💡 수기로 작성된 입학원서 이미지를 업로드하면 AI가 자동으로 정보를 추출합니다.")
    st.success("✨ **OpenAI Vision API 사용** - 높은 정확도, 파란색 글씨 자동 인식!")
    
    uploaded_file = st.file_uploader(
        "원서 이미지 업로드 (JPG, PNG)",
        type=['jpg', 'jpeg', 'png'],
        help="AI가 학생 정보, 파란색 메모 등을 자동으로 인식합니다."
    )
    
    if uploaded_file is not None:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📷 원본 이미지")
            st.image(uploaded_file, use_column_width=True)
        
        with col2:
            st.subheader("🤖 AI 분석 결과")
            
            if st.button("🚀 AI 분석 실행", type="primary", use_container_width=True):
                with st.spinner("AI가 이미지를 분석하고 있습니다... (10~20초)"):
                    success, ocr_data, raw_text = process_ocr_with_openai(uploaded_file, openai_api_key)
                    
                    if success:
                        st.success("✅ AI 분석 완료!")
                        
                        # 원본 응답 표시
                        with st.expander("📄 AI 원본 응답"):
                            st.text_area("Raw Response", raw_text, height=200)
                        
                        st.markdown("---")
                        st.subheader("✏️ AI 분석 결과 검수 및 수정")
                        
                        with st.form("ocr_review_form"):
                            review_name = st.text_input("학생명", value=ocr_data.get('name', ''))
                            review_grade = st.selectbox(
                                "학년", 
                                ["초1", "초2", "초3", "초4", "초5", "초6"],
                                index=["초1", "초2", "초3", "초4", "초5", "초6"].index(ocr_data.get('grade', '초1')) if ocr_data.get('grade') in ["초1", "초2", "초3", "초4", "초5", "초6"] else 0
                            )
                            review_phone = st.text_input("학부모 연락처", value=ocr_data.get('parent_phone', ''))
                            review_reading = st.text_area("독서 습관", value=ocr_data.get('reading_habit', ''), height=100)
                            review_notes = st.text_area("특이사항", value=ocr_data.get('special_notes', ''), height=100)
                            review_blue = st.text_area("파란색 메모", value=ocr_data.get('blue_notes', ''), height=100)
                            
                            # 희망 시간대
                            preferred_times = ocr_data.get('preferred_times', [])
                            if preferred_times:
                                st.info(f"🕐 희망 시간대: {', '.join(preferred_times)}")
                            
                            col_btn1, col_btn2 = st.columns(2)
                            with col_btn1:
                                approve = st.form_submit_button("✅ 승인 및 저장", type="primary", use_container_width=True)
                            with col_btn2:
                                reject = st.form_submit_button("❌ 거부", use_container_width=True)
                            
                            if approve:
                                ocr_record = {
                                    'image_url': f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}",
                                    'ocr_raw_text': raw_text,
                                    'ocr_structured_data': {
                                        'name': review_name,
                                        'grade': review_grade,
                                        'parent_phone': review_phone,
                                        'reading_habit': review_reading,
                                        'preferred_times': preferred_times
                                    },
                                    'blue_text_notes': review_blue,
                                    'review_status': 'approved',
                                    'reviewed_by': st.session_state.user['id'],
                                    'reviewed_at': datetime.now().isoformat()
                                }
                                
                                try:
                                    ocr_response = supabase.table('ocr_applications').insert(ocr_record).execute()
                                    
                                    student_data = {
                                        'name': review_name,
                                        'grade': review_grade,
                                        'parent_phone': review_phone,
                                        'reading_habit': review_reading,
                                        'special_notes': f"{review_notes}\n\n[파란색 메모] {review_blue}" if review_blue else review_notes,
                                        'created_by': st.session_state.user['id']
                                    }
                                    
                                    student_response = supabase.table('students').insert(student_data).execute()
                                    
                                    st.success("✅ OCR 데이터가 승인되고 학생이 등록되었습니다!")
                                    st.balloons()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ 저장 오류: {e}")
                            
                            if reject:
                                st.warning("❌ AI 분석 결과가 거부되었습니다.")
                                st.rerun()
                    else:
                        st.error(f"❌ AI 분석 실패: {raw_text}")
                        st.info("💡 OpenAI API 키를 확인해주세요.")
    
    st.markdown("---")
    st.subheader("📋 OCR 처리 이력")
    
    try:
        ocr_history = supabase.table('ocr_applications').select('*').order('created_at', desc=True).limit(10).execute()
        
        if ocr_history.data:
            df = pd.DataFrame(ocr_history.data)
            st.dataframe(
                df[['id', 'review_status', 'reviewed_at', 'created_at']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("OCR 처리 이력이 없습니다.")
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")


def show_smart_schedule(supabase):
    """스마트 시간표 페이지"""
    st.title("📅 스마트 시간표 스케줄링")
    
    st.info("""
    💡 **스마트 스케줄링 기능**
    - 특정 시간대 신청 인원이 **3명 이상**일 때 강조 표시
    - 시간대별 가용 학생 목록 및 우선순위 자동 계산
    - 우선순위: 입금 선착순 > 기존생 > 형제 > 일반 선착순
    """)
    
    try:
        schedule_view = supabase.table('smart_schedule').select('*').execute()
        
        if schedule_view.data:
            df = pd.DataFrame(schedule_view.data)
            
            st.subheader("📊 시간대별 신청 현황")
            
            selected_day = st.selectbox(
                "요일 선택",
                ["전체", "월", "화", "수", "목", "금", "토", "일"]
            )
            
            if selected_day != "전체":
                df_filtered = df[df['day_of_week'] == selected_day]
            else:
                df_filtered = df
            
            df_filtered['강조'] = df_filtered['should_highlight'].apply(lambda x: '⭐' if x else '')
            
            display_df = df_filtered[['day_of_week', 'time_slot', 'applicant_count', '강조', 'student_names']].copy()
            display_df.columns = ['요일', '시간대', '신청 인원', '개설 추천', '학생 목록']
            
            def highlight_rows(row):
                if row['개설 추천'] == '⭐':
                    return ['background-color: #FEF3C7'] * len(row)
                return [''] * len(row)
            
            styled_df = display_df.style.apply(highlight_rows, axis=1)
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.subheader("🔍 시간대별 학생 상세 목록")
            
            time_slots = df_filtered[['day_of_week', 'time_slot', 'applicant_count']].apply(
                lambda x: f"{x['day_of_week']} {x['time_slot']} ({x['applicant_count']}명)", axis=1
            ).tolist()
            
            selected_slot = st.selectbox("시간대 선택", time_slots)
            
            if selected_slot:
                parts = selected_slot.split()
                sel_day = parts[0]
                sel_time = parts[1]
                
                students_query = supabase.table('available_times').select(
                    'student_id, priority, students(name, grade, payment_status, payment_date, is_existing_student, has_sibling)'
                ).eq('day_of_week', sel_day).eq('time_slot', sel_time).execute()
                
                if students_query.data:
                    st.success(f"📋 {sel_day} {sel_time} 시간대 가용 학생 목록")
                    
                    student_list = []
                    for item in students_query.data:
                        student = item['students']
                        priority_score = 0
                        
                        if student['payment_status'] == 'paid':
                            priority_score += 1000000
                            
                            if student['payment_date']:
                                from datetime import datetime
                                payment_time = datetime.fromisoformat(student['payment_date'].replace('Z', '+00:00'))
                                priority_score += (10000 - int((datetime.now(payment_time.tzinfo) - payment_time).total_seconds()))
                        
                        if student['is_existing_student']:
                            priority_score += 5000
                        
                        if student['has_sibling']:
                            priority_score += 3000
                        
                        student_list.append({
                            '이름': student['name'],
                            '학년': student['grade'],
                            '입금상태': student['payment_status'],
                            '기존생': '✓' if student['is_existing_student'] else '',
                            '형제': '✓' if student['has_sibling'] else '',
                            '우선순위점수': priority_score,
                            '시간우선순위': item['priority']
                        })
                    
                    student_df = pd.DataFrame(student_list)
                    student_df = student_df.sort_values('우선순위점수', ascending=False)
                    student_df['배정순번'] = range(1, len(student_df) + 1)
                    
                    st.dataframe(
                        student_df[['배정순번', '이름', '학년', '입금상태', '기존생', '형제', '우선순위점수']],
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("해당 시간대에 신청한 학생이 없습니다.")
        else:
            st.info("시간표 데이터가 없습니다. 학생의 가용 시간을 먼저 등록해주세요.")
            
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        st.info("💡 Supabase에서 'smart_schedule' 뷰가 생성되었는지 확인해주세요.")

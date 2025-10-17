import streamlit as st
import requests
import logging
import json
import uuid
from datetime import datetime
from src.client import chat_with_context, chat_with_context_stream

# 서버 설정
SERVER_CHAT_API = "http://localhost:9393/v1/chat/completions"
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# 마크다운 이스케이프 함수
def escape_markdown(text):
    """사용자 입력에서 마크다운 특수문자를 이스케이프 처리"""
    if not text:
        return text
    
    # 마크다운 특수문자들을 이스케이프
    markdown_chars = ['*', '_', '`', '#', '[', ']', '(', ')', '>', '!', '|', '\\', '~', '^']
    for char in markdown_chars:
        text = text.replace(char, f'\\{char}')
    
    # 수학 수식 방지 ($로 둘러싸인 부분)
    text = text.replace('$', '\\$')
    
    return text

# 세션 상태 초기화
defaults = {
    "session_id": str(uuid.uuid4()),
    "chat_history": [],
    "recent_inputs": [],
    "conversation_context": [],  # 대화 맥락 저장용
    "show_welcome": True,
    "last_response": ""
}
for key, val in defaults.items():
    st.session_state.setdefault(key, val)

# --- 신규: 채팅 제출 처리 함수 ---
def handle_chat_submission(prompt):
    """사용자 입력을 받아 LLM 응답을 처리하고 표시하는 통합 함수"""
    st.session_state.show_welcome = False
    
    # 사용자 메시지 표시 및 저장
    with st.chat_message("user"):
        st.text(prompt)
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    st.session_state.recent_inputs.append(prompt)
    if len(st.session_state.recent_inputs) > 10:
        st.session_state.recent_inputs = st.session_state.recent_inputs[-10:]

    # CoT 처리
    processed_prompt = prompt
    if st.session_state.get("use_cot"):
        processed_prompt += "\n\n**Chain of Thought 요청:** 생각하는 과정을 단계별로 서술한 뒤, 마지막에 핵심 내용을 요약해주세요."

    # 어시스턴트 응답
    with st.chat_message("assistant"):
        full_response = ""
        try:
            if st.session_state.get("use_streaming", True):
                # 스트리밍 응답
                response_placeholder = st.empty()
                for chunk in chat_with_context_stream(
                    message=processed_prompt,
                    conversation_history=st.session_state.conversation_context,
                    server_url=SERVER_CHAT_API,
                    model_name=st.session_state.get("model_name", "gpt-4o"),
                    temperature=st.session_state.get("temperature", 0.7),
                    max_tokens=st.session_state.get("max_tokens", 1024)
                ):
                    if chunk:
                        full_response += chunk
                        response_placeholder.markdown(full_response + "▌")
                response_placeholder.markdown(full_response)
            else:
                # 일반 응답
                with st.spinner("응답 생성 중..."):
                    full_response = chat_with_context(
                        message=processed_prompt,
                        conversation_history=st.session_state.conversation_context,
                        server_url=SERVER_CHAT_API,
                        model_name=st.session_state.get("model_name", "gpt-4o"),
                        temperature=st.session_state.get("temperature", 0.7),
                        max_tokens=st.session_state.get("max_tokens", 1024)
                    )
                    st.markdown(full_response)
        except Exception as e:
            full_response = f"[오류] 응답 생성 중 오류 발생: {e}"
            st.markdown(full_response)

    # 응답 및 대화 맥락 저장
    st.session_state.chat_history.append({"role": "assistant", "content": full_response})
    st.session_state.last_response = full_response
    st.session_state.conversation_context.append({"role": "user", "content": prompt})
    st.session_state.conversation_context.append({"role": "assistant", "content": full_response})
    if len(st.session_state.conversation_context) > 20:
        st.session_state.conversation_context = st.session_state.conversation_context[-20:]

# 페이지 기본 설정
st.set_page_config(
    page_title="Isolated Chat",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 기본 CSS 스타일
st.markdown("""
    <style>
.welcome-container {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 2rem;
    border-radius: 1rem;
    text-align: center;
    color: white;
    margin-bottom: 2rem;
}
.feature-card {
    background-color: #f8f9fa;
    border: 1px solid #e9ecef;
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 0.5rem 0;
}
.stButton > button {
    width: 100%;
    border-radius: 4px;
    font-size: 13px;
    padding: 4px 8px;
    height: 32px;
    }
    </style>

<script>
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        // 성공 시 알림 표시
        const toast = document.createElement('div');
        toast.textContent = '✅ 복사되었습니다!';
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #28a745;
            color: white;
            padding: 10px 15px;
            border-radius: 5px;
            z-index: 9999;
            font-size: 14px;
        `;
        document.body.appendChild(toast);
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 2000);
    }, function(err) {
        console.error('복사 실패: ', err);
        alert('복사에 실패했습니다. 브라우저가 클립보드 API를 지원하지 않을 수 있습니다.');
    });
}
</script>
""", unsafe_allow_html=True)

# 헤더
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("<h1 style='text-align: center; margin-bottom: 1rem;'>🤖 Isolated Chat</h1>", unsafe_allow_html=True)

# 환영 페이지
if st.session_state.show_welcome and not st.session_state.chat_history:
    st.markdown("""
    <div class="welcome-container">
        <h2>👋 안녕하세요! Isolated Chat입니다</h2>
        <p>폐쇄망 환경에서 안전하게 LLM을 활용한 대화를 시작하세요</p>
        <br>
        <div style="display: flex; justify-content: center; gap: 2rem; flex-wrap: wrap;">
            <div style="text-align: center;">
                <div style="font-size: 2rem;">🔒</div>
                <strong>보안</strong><br>
                <small>폐쇄망 내부 환경</small>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 2rem;">⚡</div>
                <strong>빠른 응답</strong><br>
                <small>실시간 스트리밍</small>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 2rem;">💡</div>
                <strong>다양한 활용</strong><br>
                <small>질문, 분석, 작성</small>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 2rem;">🎯</div>
                <strong>맥락 이해</strong><br>
                <small>대화 기억 유지</small>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 💬 질문을 입력하여 대화를 시작하세요")
    st.markdown("**예시 질문:**")
    st.markdown("- 코드 리뷰 및 개선 방법 제안")
    st.markdown("- 데이터 분석 및 인사이트 도출")
    st.markdown("- 문서 작성 및 번역")
    st.markdown("- 기술적 문제 해결 방법")

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 설정")
    
    st.session_state.model_name = st.selectbox(
        "🧠 모델", 
        [
            "gpt-4o", 
            "gpt-4o-mini",
            "gpt-4.1"
        ], 
        index=0
    )
    
    with st.expander("🔧 고급 설정", expanded=False):
        st.session_state.temperature = st.slider("🔥 Temperature", 0.0, 1.5, 0.7, 0.1, help="응답의 창의성 조절")
        st.session_state.max_tokens = st.slider("🧱 Max Tokens", 50, 4096, 1024, step=10, help="최대 응답 길이")
        st.session_state.use_cot = st.checkbox("🧠 Chain of Thought", value=False, help="단계별 사고 과정 요청")
        st.session_state.use_streaming = st.checkbox("🌊 스트리밍 응답", value=True, help="실시간 응답 표시")
    
    st.divider()
    
    # 대화 관리
    st.subheader("💬 대화 관리")
    if st.button("🧹 대화 초기화", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.conversation_context = []
        st.session_state.show_welcome = True
        st.success("대화가 초기화되었습니다!")
        st.rerun()

# 메인 채팅 인터페이스
if st.session_state.chat_history:
    st.session_state.show_welcome = False
    
    # 채팅 기록 표시
    for i, message in enumerate(st.session_state.chat_history):
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                # 사용자 입력은 마크다운 없이 그대로 표시
                st.text(message["content"])
            else:
                # 어시스턴트 응답은 마크다운 렌더링
                st.markdown(message["content"])
                

# 채팅 입력
if prompt := st.chat_input("질문을 입력하세요..."):
    handle_chat_submission(prompt)

# 최근 질문 (하단에 표시)
if st.session_state.recent_inputs and not st.session_state.show_welcome:
    with st.expander("📌 최근 질문", expanded=False):
        for i, recent_q in enumerate(reversed(st.session_state.recent_inputs[-5:])):
            if st.button(f"🔄 {recent_q[:50]}{'...' if len(recent_q) > 50 else ''}", 
                        key=f"recent_{i}", use_container_width=True):
                # 통합 함수 호출 (st.rerun() 제거)
                handle_chat_submission(recent_q)
                st.rerun() # UI 즉시 업데이트를 위해 rerun 추가

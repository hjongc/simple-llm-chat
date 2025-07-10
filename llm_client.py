import requests
import logging
import json

# 챗봇 성능 향상을 위한 시스템 프롬프트
SYSTEM_PROMPT = """You are a professional AI assistant specialized in MI (Management Information) projects and IT infrastructure. Follow these guidelines:

LANGUAGE: Always respond in Korean unless the user specifically requests another language.

EXPERTISE AREAS:
- Database management and troubleshooting (Oracle, SQL Server, MySQL)
- Control-M job scheduling and automation
- System administration and server management
- Data analysis and reporting
- IT infrastructure and network management

RESPONSE STYLE:
- Be concise but comprehensive
- Use bullet points or numbered lists for complex information
- Include practical examples when explaining technical concepts
- Provide step-by-step instructions for procedures
- Use appropriate technical terminology in Korean

PROBLEM-SOLVING APPROACH:
- Ask clarifying questions if the request is ambiguous
- Provide multiple solution options when applicable
- Include potential risks or considerations
- Suggest best practices and preventive measures

FORMATTING:
- Use markdown formatting for better readability
- Include code blocks for SQL queries, scripts, or commands
- Use tables for structured data comparison
- Highlight important warnings or notes

Remember: You are helping with MI project tasks, so prioritize accuracy, clarity, and practical applicability in your responses."""

# LLM 서버 호출 함수 (재사용용)
def chat_with_api(message, server_url="http://150.6.15.80/v1/chat/completions", model_name="gpt-4o", timeout=60, temperature=0.7, max_tokens=4096):
    """
    LLM 서버에 단일 메시지를 보내고 응답을 받는다.
    :param message: 사용자 메시지
    :param server_url: LLM 서버 API 주소
    :param model_name: 사용할 모델명
    :param timeout: 요청 타임아웃(초)
    :param temperature: 응답의 창의성 조절 (0.0-1.5)
    :param max_tokens: 최대 응답 길이
    :return: LLM 응답 텍스트
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": message}
    ]
    
    payload = {
        "model": model_name,
        "messages": messages,
        "stream": False,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    try:
        response = requests.post(server_url, json=payload, timeout=timeout)
        response.raise_for_status()
        result = response.json()
        answer = result.get("choices", [{}])[0].get("message", {}).get("content", "❌ 응답 없음")
        return answer
    except Exception as e:
        logging.error(f"❌ LLM 서버 호출 오류: {e}")
        return "[오류] 서버 응답 실패"

# 대화 맥락을 포함한 고급 채팅 함수
def chat_with_context(message, conversation_history=None, server_url="http://150.6.15.80/v1/chat/completions", model_name="gpt-4o", timeout=60, temperature=0.7, max_tokens=2048):
    """
    대화 맥락을 포함하여 LLM 서버에 요청을 보낸다.
    :param message: 현재 사용자 메시지
    :param conversation_history: 이전 대화 내역 [{"role": "user/assistant", "content": "..."}]
    :param server_url: LLM 서버 API 주소
    :param model_name: 사용할 모델명
    :param timeout: 요청 타임아웃(초)
    :param temperature: 응답의 창의성 조절 (0.0-1.5)
    :param max_tokens: 최대 응답 길이
    :return: LLM 응답 텍스트
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # 대화 맥락 추가 (최근 6개 메시지만 유지)
    if conversation_history:
        messages.extend(conversation_history[-6:])
    
    # 현재 메시지 추가
    messages.append({"role": "user", "content": message})
    
    payload = {
        "model": model_name,
        "messages": messages,
        "stream": False,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    try:
        response = requests.post(server_url, json=payload, timeout=timeout)
        response.raise_for_status()
        result = response.json()
        answer = result.get("choices", [{}])[0].get("message", {}).get("content", "❌ 응답 없음")
        return answer
    except Exception as e:
        logging.error(f"❌ LLM 서버 호출 오류: {e}")
        return "[오류] 서버 응답 실패"

# 스트리밍 응답을 위한 함수
def chat_with_context_stream(message, conversation_history=None, server_url="http://localhost:9393/v1/chat/completions", model_name="gpt-4o", timeout=60, temperature=0.7, max_tokens=2048):
    """
    스트리밍 방식으로 대화 맥락을 포함하여 LLM 서버에 요청을 보낸다.
    :param message: 현재 사용자 메시지
    :param conversation_history: 이전 대화 내역 [{"role": "user/assistant", "content": "..."}]
    :param server_url: LLM 서버 API 주소
    :param model_name: 사용할 모델명
    :param timeout: 요청 타임아웃(초)
    :param temperature: 응답의 창의성 조절 (0.0-1.5)
    :param max_tokens: 최대 응답 길이
    :return: 스트리밍 응답 제너레이터
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # 대화 맥락 추가 (최근 6개 메시지만 유지)
    if conversation_history:
        messages.extend(conversation_history[-6:])
    
    # 현재 메시지 추가
    messages.append({"role": "user", "content": message})
    
    payload = {
        "model": model_name,
        "messages": messages,
        "stream": True,  # 스트리밍 활성화
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    try:
        response = requests.post(server_url, json=payload, timeout=timeout, stream=True)
        response.raise_for_status()
        
        full_response = ""
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]  # 'data: ' 제거
                    if data.strip() == '[DONE]':
                        break
                    try:
                        json_data = json.loads(data)
                        if 'choices' in json_data and json_data['choices']:
                            delta = json_data['choices'][0].get('delta', {})
                            if 'content' in delta:
                                content = delta['content']
                                full_response += content
                                yield content
                    except json.JSONDecodeError:
                        continue
        
        return full_response
    except Exception as e:
        logging.error(f"❌ 스트리밍 LLM 서버 호출 오류: {e}")
        yield "[오류] 서버 응답 실패"

# MSTR 설계표 분석용 프롬프트 생성 함수
def get_mstr_design_prompt(sql: str) -> str:
    """
    MSTR 설계표 분석을 위한 프롬프트를 생성한다.
    :param sql: 분석할 SQL 문자열
    :return: LLM에 전달할 프롬프트 문자열
    """
    return f"""
너는 MicroStrategy(MSTR) 개발자야.
아래는 Oracle 기반의 복잡한 웹 리포트용 SQL이다.
아래 SQL을 분석하여 MSTR 설계 문서 형식으로 표로 정리해줘.
특히 다음 사항을 꼭 반영해줘:


--------------------------------------------------------------------------------
✅ 1. MSTR 문서 포맷으로 정리
출력 형식은 다음 표 구조를 따라야 해:
Object Type (예: Attribute, Metric, Prompt)
Object Name (항목명)
Mapped Column / Expression (SQL 컬럼명 또는 계산식)
Source Table (해당 컬럼이 참조된 팩트 또는 조인 테이블, 알리아스명이 아닌 실제 테이블명)
Lookup Table (Attribute의 경우 명칭 정보가 있는 테이블, 알리아스명이 아닌 실제 테이블명)
Description (의미 및 치환 조건, 필터 조건 등 포함 설명)
--------------------------------------------------------------------------------
✅ 2. Attribute는 개별적으로 Lookup/Facts 테이블 구분
각 Attribute가 어떤 테이블에서 유래했고, 어떤 테이블을 명칭 조회용으로 참조하는지 명확히 정리해줘(알리아스명이 아닌 실제 테이블명)
예: T5.MKT_DIV_ORG_CD는 팩트 테이블에는 없고 MMAP_SHOP_D에서 참조하므로 Lookup Table로 명시
--------------------------------------------------------------------------------
✅ 3. Metric은 계산식과 함께 분모 0 체크, NVL 사용 여부 등 주의사항 포함
예: 해지율, 정지율 등은 분모 > 0일 경우만 계산되도록 구성됨
--------------------------------------------------------------------------------
✅ 4. WHERE 절 및 주석(/* 치환: ... */)을 참고하여 Prompt 항목 도출
시작일, 종료일, 판매유형코드, 채널코드, 조직코드 등은 Prompt로 분리해줘
치환 조건(/* 치환: 상권코드가 존재할 경우... */)이 존재하는 경우, 설명에 해당 조건을 반드시 적어줘
--------------------------------------------------------------------------------
✅ 5. SQL 전체를 분석해서 설계서만 출력하고, SQL을 그대로 출력하지 말 것
✅ 6. 한글로 작성할 것
아래 SQL을 분석해줘:
{sql}
""" 

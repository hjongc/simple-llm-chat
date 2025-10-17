from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import httpx
import time
import uuid
import logging
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager
import json
from src.config import (
    API_KEY,
    LLM_API_BASE_URL,
    FASTAPI_HOST,
    FASTAPI_PORT,
    API_TIMEOUT,
    API_MAX_RETRIES,
    API_RETRY_DELAY,
    LOG_LEVEL,
    LOG_DIR,
    CORS_ORIGINS,
    validate_config
)
import os

# 로그 디렉토리 생성
os.makedirs(LOG_DIR, exist_ok=True)

# 로그 설정
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'{LOG_DIR}/fastapi_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 설정 검증
try:
    validate_config()
    logger.info("✅ 설정 검증 완료")
except ValueError as e:
    logger.error(f"❌ 설정 오류: {e}")
    raise

# HTTP 클라이언트 설정
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 HTTP 클라이언트 생성
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(API_TIMEOUT),
        limits=httpx.Limits(max_keepalive_connections=10, max_connections=100)
    )
    logger.info(f"FastAPI 서버가 시작되었습니다. (포트: {FASTAPI_PORT})")
    yield
    # 종료 시 HTTP 클라이언트 정리
    await app.state.http_client.aclose()
    logger.info("FastAPI 서버가 종료되었습니다.")

# FastAPI 앱 생성
app = FastAPI(
    title="Isolated Chat API",
    description="폐쇄망 환경을 위한 LLM 프록시 채팅 API 서버",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 요청/응답 모델 정의
class Message(BaseModel):
    role: str = Field(..., description="메시지 역할 (user, assistant, system)")
    content: str = Field(..., description="메시지 내용")

class ChatCompletionRequest(BaseModel):
    model: str = Field(..., description="사용할 모델명")
    messages: List[Message] = Field(..., description="대화 메시지 목록")
    stream: bool = Field(False, description="스트리밍 여부")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="응답 창의성 조절")
    max_tokens: Optional[int] = Field(1024, ge=1, le=4096, description="최대 토큰 수")
    top_p: Optional[float] = Field(1.0, ge=0.0, le=1.0, description="nucleus sampling")
    frequency_penalty: Optional[float] = Field(0.0, ge=-2.0, le=2.0, description="빈도 페널티")
    presence_penalty: Optional[float] = Field(0.0, ge=-2.0, le=2.0, description="존재 페널티")

class ChatCompletionResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, int]] = None

# 전역 변수 (통계 수집용)
request_count = 0
error_count = 0
total_response_time = 0.0

# 유틸리티 함수 import
from src.utils import generate_chat_id, validate_model

async def call_llm_api_with_retry(client: httpx.AsyncClient, payload: dict, retries: int = API_MAX_RETRIES) -> dict:
    """재시도 로직이 포함된 LLM API 호출"""
    last_exception = None

    for attempt in range(retries):
        try:
            logger.info(f"LLM API 호출 시도 {attempt + 1}/{retries}")

            response = await client.post(
                LLM_API_BASE_URL,
                headers={
                    "Authorization": API_KEY,
                    "Content-Type": "application/json",
                    "User-Agent": "Isolated-Chat/1.0"
                },
                json=payload
            )
            
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"LLM API 호출 성공 (시도 {attempt + 1})")
            return result

        except httpx.TimeoutException as e:
            last_exception = e
            logger.warning(f"LLM API 타임아웃 (시도 {attempt + 1}/{retries}): {e}")

        except httpx.HTTPStatusError as e:
            last_exception = e
            logger.error(f"LLM API HTTP 오류 (시도 {attempt + 1}/{retries}): {e.response.status_code} - {e.response.text}")

            # 4xx 에러는 재시도하지 않음
            if 400 <= e.response.status_code < 500:
                break

        except Exception as e:
            last_exception = e
            logger.error(f"LLM API 호출 오류 (시도 {attempt + 1}/{retries}): {e}")

        # 마지막 시도가 아니면 잠시 대기
        if attempt < retries - 1:
            await asyncio.sleep(API_RETRY_DELAY * (attempt + 1))
    
    # 모든 재시도 실패
    raise last_exception

# 미들웨어 - 요청 로깅
@app.middleware("http")
async def log_requests(request: Request, call_next):
    global request_count, total_response_time
    
    start_time = time.time()
    request_count += 1
    
    # 요청 정보 로깅
    logger.info(f"요청 시작: {request.method} {request.url}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        total_response_time += process_time
        
        logger.info(f"요청 완료: {request.method} {request.url} - {response.status_code} - {process_time:.3f}s")
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
        
    except Exception as e:
        global error_count
        error_count += 1
        process_time = time.time() - start_time
        logger.error(f"요청 실패: {request.method} {request.url} - {process_time:.3f}s - {e}")
        raise

# 헬스체크 엔드포인트
@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# 통계 엔드포인트
@app.get("/stats")
async def get_stats():
    """서버 통계 정보"""
    avg_response_time = total_response_time / request_count if request_count > 0 else 0
    
    return {
        "total_requests": request_count,
        "total_errors": error_count,
        "error_rate": error_count / request_count if request_count > 0 else 0,
        "average_response_time": round(avg_response_time, 3),
        "uptime": time.time() - start_time if 'start_time' in globals() else 0
    }

# 메인 채팅 엔드포인트
@app.post("/v1/chat/completions")
async def chat_completion(req: ChatCompletionRequest):
    """채팅 완성 API - OpenAI 호환 (스트리밍 지원)"""
    
    # 입력 검증
    if not req.messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="메시지가 비어있습니다."
        )
    
    if not validate_model(req.model):
        logger.warning(f"지원하지 않는 모델 요청: {req.model}")
        # 지원하지 않는 모델이어도 일단 진행 (SKT API에서 처리)
    
    # 요청 로깅
    logger.info(f"채팅 요청: 모델={req.model}, 메시지 수={len(req.messages)}, 스트리밍={req.stream}")
    
    # SKT API 호출용 페이로드 구성
    skt_payload = {
                    "model": req.model,
        "messages": [{"role": m.role, "content": m.content} for m in req.messages],
        "stream": req.stream
    }
    
    # 선택적 매개변수 추가
    if req.temperature is not None:
        skt_payload["temperature"] = req.temperature
    if req.max_tokens is not None:
        skt_payload["max_tokens"] = req.max_tokens
    if req.top_p is not None:
        skt_payload["top_p"] = req.top_p
    if req.frequency_penalty is not None:
        skt_payload["frequency_penalty"] = req.frequency_penalty
    if req.presence_penalty is not None:
        skt_payload["presence_penalty"] = req.presence_penalty
    
    try:
        if req.stream:
            # 스트리밍 응답 처리
            return StreamingResponse(
                stream_chat_response(skt_payload, req.model),
                media_type="text/plain"
            )
        else:
            # 일반 응답 처리
            return await handle_normal_response(skt_payload, req.model)
            
    except httpx.HTTPStatusError as e:
        logger.error(f"SKT API HTTP 오류: {e.response.status_code} - {e.response.text}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"외부 API 오류: {e.response.status_code}"
        )
        
    except httpx.TimeoutException:
        logger.error("SKT API 타임아웃")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="외부 API 응답 시간 초과"
        )
        
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 내부 오류가 발생했습니다."
        )

async def handle_normal_response(llm_payload: dict, model: str) -> ChatCompletionResponse:
    """일반 응답 처리"""
    llm_data = await call_llm_api_with_retry(app.state.http_client, llm_payload)
    
    # 응답 데이터 추출
    choices = llm_data.get("choices", [])
    if not choices:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM API에서 유효한 응답을 받지 못했습니다."
        )

    reply_content = choices[0].get("message", {}).get("content", "")
    if not reply_content:
        logger.warning("LLM API 응답이 비어있습니다.")
        reply_content = "죄송합니다. 응답을 생성할 수 없습니다."
    
    # OpenAI 호환 응답 포맷 구성
    response_data = {
        "id": generate_chat_id(),
                "object": "chat.completion",
                "created": int(time.time()),
        "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                    "content": reply_content
                },
                "finish_reason": choices[0].get("finish_reason", "stop")
            }
        ],
        "usage": llm_data.get("usage", {
            "prompt_tokens": sum(len(str(m.get("content", "")).split()) for m in llm_payload.get("messages", [])),
            "completion_tokens": len(reply_content.split()),
            "total_tokens": sum(len(str(m.get("content", "")).split()) for m in llm_payload.get("messages", [])) + len(reply_content.split())
        })
    }
    
    logger.info(f"채팅 응답 성공: 토큰 수={len(reply_content)}")
    return response_data

async def stream_chat_response(llm_payload: dict, model: str):
    """스트리밍 응답 처리"""
    chat_id = generate_chat_id()
    created = int(time.time())

    try:
        # LLM API에 스트리밍 요청
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            async with client.stream(
                "POST",
                LLM_API_BASE_URL,
                headers={
                    "Authorization": API_KEY,
                    "Content-Type": "application/json",
                    "User-Agent": "Isolated-Chat/1.0"
                },
                json=llm_payload
            ) as response:
                
                response.raise_for_status()
                
                # 스트리밍 응답 처리
                buffer = ""
                async for chunk in response.aiter_bytes():
                    buffer += chunk.decode('utf-8')
                    
                    # 완전한 라인들을 처리
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        
                        if line.startswith('data: '):
                            data_str = line[6:]  # 'data: ' 제거
                            
                            if data_str.strip() == '[DONE]':
                                # 스트리밍 종료 신호
                                yield "data: [DONE]\n\n"
                                return
                            
                            try:
                                # SKT API 응답 파싱
                                data = json.loads(data_str)
                                
                                if 'choices' in data and data['choices']:
                                    choice = data['choices'][0]
                                    
                                    # OpenAI 호환 스트리밍 응답 포맷
                                    stream_response = {
                                        "id": chat_id,
                                        "object": "chat.completion.chunk",
                                        "created": created,
                                        "model": model,
                                        "choices": [
                                            {
                                                "index": 0,
                                                "delta": choice.get("delta", {}),
                                                "finish_reason": choice.get("finish_reason")
                                            }
                                        ]
                                    }
                                    
                                    # 클라이언트에 전송
                                    yield f"data: {json.dumps(stream_response, ensure_ascii=False)}\n\n"
                                    
                            except json.JSONDecodeError:
                                # JSON 파싱 오류는 무시하고 계속
                                continue
                        
                        elif line == '':
                            # 빈 라인은 무시
                            continue
                
    except Exception as e:
        logger.error(f"스트리밍 응답 오류: {e}")
        # 오류 발생 시 오류 메시지 전송
        error_response = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": f"[오류] 스트리밍 응답 실패: {str(e)}"},
                    "finish_reason": "stop"
                }
            ]
        }
        yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

# 전역 예외 처리기
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"전역 예외 발생: {request.method} {request.url} - {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "서버 내부 오류가 발생했습니다."}
    )

# 서버 시작 시간 기록
start_time = time.time()

if __name__ == "__main__":
    import uvicorn
    from src.config import print_config

    print_config()
    uvicorn.run(app, host=FASTAPI_HOST, port=FASTAPI_PORT, log_level=LOG_LEVEL.lower())

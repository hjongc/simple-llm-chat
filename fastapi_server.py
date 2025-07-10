from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import httpx
import os
import time
import uuid
from dotenv import load_dotenv
import logging
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager
import json

# ✅ 로그 설정 개선
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fastapi_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ✅ .env 로딩
env_loaded = load_dotenv()
logger.info(f".env 파일 로딩 여부: {env_loaded}")

# ✅ API_KEY 확인 및 검증
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    logger.error("❌ API_KEY가 설정되지 않았습니다!")
    raise ValueError("API_KEY 환경변수가 필요합니다.")

# SKT API 기본 설정
SKT_API_BASE_URL = "https://aihub-api.sktelecom.com/aihub/v2/sandbox/chat/completions"
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 1

# HTTP 클라이언트 설정
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 HTTP 클라이언트 생성
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(DEFAULT_TIMEOUT),
        limits=httpx.Limits(max_keepalive_connections=10, max_connections=100)
    )
    logger.info("FastAPI 서버가 시작되었습니다.")
    yield
    # 종료 시 HTTP 클라이언트 정리
    await app.state.http_client.aclose()
    logger.info("FastAPI 서버가 종료되었습니다.")

# FastAPI 앱 생성
app = FastAPI(
    title="MI Project Chat API",
    description="SKT AI Hub API를 프록시하는 채팅 API 서버",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 구체적인 도메인 지정
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

# 유틸리티 함수들
def generate_chat_id() -> str:
    """고유한 채팅 ID 생성"""
    return f"chatcmpl-{uuid.uuid4().hex[:8]}"

def validate_model(model: str) -> bool:
    """지원하는 모델인지 확인"""
    supported_models = ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo", "gpt-4"]
    return model in supported_models

async def call_skt_api_with_retry(client: httpx.AsyncClient, payload: dict, retries: int = MAX_RETRIES) -> dict:
    """재시도 로직이 포함된 SKT API 호출"""
    last_exception = None
    
    for attempt in range(retries):
        try:
            logger.info(f"SKT API 호출 시도 {attempt + 1}/{retries}")
            
            response = await client.post(
                SKT_API_BASE_URL,
                headers={
                    "Authorization": API_KEY,
                    "Content-Type": "application/json",
                    "User-Agent": "MI-Project-Chat-API/1.0"
                },
                json=payload
            )
            
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"SKT API 호출 성공 (시도 {attempt + 1})")
            return result
            
        except httpx.TimeoutException as e:
            last_exception = e
            logger.warning(f"SKT API 타임아웃 (시도 {attempt + 1}/{retries}): {e}")
            
        except httpx.HTTPStatusError as e:
            last_exception = e
            logger.error(f"SKT API HTTP 오류 (시도 {attempt + 1}/{retries}): {e.response.status_code} - {e.response.text}")
            
            # 4xx 에러는 재시도하지 않음
            if 400 <= e.response.status_code < 500:
                break
                
        except Exception as e:
            last_exception = e
            logger.error(f"SKT API 호출 오류 (시도 {attempt + 1}/{retries}): {e}")
        
        # 마지막 시도가 아니면 잠시 대기
        if attempt < retries - 1:
            await asyncio.sleep(RETRY_DELAY * (attempt + 1))
    
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

async def handle_normal_response(skt_payload: dict, model: str) -> ChatCompletionResponse:
    """일반 응답 처리"""
    skt_data = await call_skt_api_with_retry(app.state.http_client, skt_payload)
    
    # 응답 데이터 추출
    choices = skt_data.get("choices", [])
    if not choices:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="SKT API에서 유효한 응답을 받지 못했습니다."
        )
    
    reply_content = choices[0].get("message", {}).get("content", "")
    if not reply_content:
        logger.warning("SKT API 응답이 비어있습니다.")
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
        "usage": skt_data.get("usage", {
            "prompt_tokens": sum(len(str(m.get("content", "")).split()) for m in skt_payload.get("messages", [])),
            "completion_tokens": len(reply_content.split()),
            "total_tokens": sum(len(str(m.get("content", "")).split()) for m in skt_payload.get("messages", [])) + len(reply_content.split())
        })
    }
    
    logger.info(f"채팅 응답 성공: 토큰 수={len(reply_content)}")
    return response_data

async def stream_chat_response(skt_payload: dict, model: str):
    """스트리밍 응답 처리"""
    chat_id = generate_chat_id()
    created = int(time.time())
    
    try:
        # SKT API에 스트리밍 요청
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            async with client.stream(
                "POST",
                SKT_API_BASE_URL,
                headers={
                    "Authorization": API_KEY,
                    "Content-Type": "application/json",
                    "User-Agent": "MI-Project-Chat-API/1.0"
                },
                json=skt_payload
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
    uvicorn.run(app, host="0.0.0.0", port=9393, log_level="info")

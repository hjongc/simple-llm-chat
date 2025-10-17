"""
Configuration settings for Isolated Chat
환경 변수를 통해 모든 설정을 관리합니다.
"""
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# API 설정
API_KEY = os.getenv("API_KEY", "")
LLM_API_BASE_URL = os.getenv("LLM_API_BASE_URL", "https://your-llm-api.com/v1/chat/completions")

# 서버 설정
FASTAPI_HOST = os.getenv("FASTAPI_HOST", "0.0.0.0")
FASTAPI_PORT = int(os.getenv("FASTAPI_PORT", "9393"))

STREAMLIT_HOST = os.getenv("STREAMLIT_HOST", "0.0.0.0")
STREAMLIT_PORT = int(os.getenv("STREAMLIT_PORT", "9191"))

# API 타임아웃 및 재시도 설정
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))
API_MAX_RETRIES = int(os.getenv("API_MAX_RETRIES", "3"))
API_RETRY_DELAY = int(os.getenv("API_RETRY_DELAY", "1"))

# 로깅 설정
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = os.getenv("LOG_DIR", "logs")

# 모델 설정
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o")
SUPPORTED_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo", "gpt-4", "gpt-4.1"]

# CORS 설정
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# 검증 함수
def validate_config():
    """필수 설정 검증"""
    if not API_KEY:
        raise ValueError("API_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")

    if not LLM_API_BASE_URL or LLM_API_BASE_URL == "https://your-llm-api.com/v1/chat/completions":
        raise ValueError("LLM_API_BASE_URL 환경변수를 실제 LLM API 주소로 설정하세요.")

# 설정값 출력 (디버깅용)
def print_config():
    """현재 설정값 출력 (민감 정보 제외)"""
    print("=" * 50)
    print("Isolated Chat Configuration")
    print("=" * 50)
    print(f"LLM API Base URL: {LLM_API_BASE_URL}")
    print(f"FastAPI Server: {FASTAPI_HOST}:{FASTAPI_PORT}")
    print(f"Streamlit App: {STREAMLIT_HOST}:{STREAMLIT_PORT}")
    print(f"Default Model: {DEFAULT_MODEL}")
    print(f"API Timeout: {API_TIMEOUT}s")
    print(f"Max Retries: {API_MAX_RETRIES}")
    print(f"Log Level: {LOG_LEVEL}")
    print(f"CORS Origins: {CORS_ORIGINS}")
    print("=" * 50)

"""
Helper utility functions
"""
import uuid
from src.config import SUPPORTED_MODELS


def generate_chat_id() -> str:
    """고유한 채팅 ID 생성"""
    return f"chatcmpl-{uuid.uuid4().hex[:8]}"


def validate_model(model: str) -> bool:
    """지원하는 모델인지 확인"""
    return model in SUPPORTED_MODELS

# Simple LLM Chat

> 내부 LLM 서버를 활용하는 간단한 채팅 앱 (통신사 폐쇄망 환경에서 실제 사용 중)
> Simple chat app using internal LLM server (Actually used in telecom isolated network)

<div align="center">

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)

**[한국어](#-소개)** | **[English](#english-version)**

</div>

## 📝 소개

**Simple LLM Chat**은 내부 LLM API 서버를 활용한 채팅 서비스를 제공하는 경량 애플리케이션입니다.
통신사 폐쇄망 환경에서 실제로 사용할 목적으로 개발되었으며, 구성원들이 매우 편하게 사용하고 있습니다.

### 🎯 사용 사례

이 프로젝트는 다음과 같은 환경에서 사용하도록 설계되었습니다:

- **내부 LLM 서버 활용**: 기업 내부에 LLM API 프록시 서버가 구축되어 있는 경우
- **OpenAI 호환 API**: 내부 서버가 OpenAI Chat Completion API 형식을 지원하는 경우

**실제 구성 예시:**
```
[사용자 PC] → [Simple LLM Chat] → [내부 LLM 프록시 서버] → [LLM 모델]
                  (본 앱)              (내부 인프라)          (GPT-4 등)
```

### 주요 특징

- 🚀 **간단한 구성**: FastAPI 프록시 + Streamlit UI로 구성된 심플한 아키텍처
- 🔄 **OpenAI 호환 API**: OpenAI Chat Completion API와 호환되는 인터페이스
- 💬 **실시간 스트리밍**: 스트리밍 응답을 지원하여 실시간으로 답변 확인 가능
- 🎨 **직관적인 UI**: Streamlit 기반의 사용하기 쉬운 채팅 인터페이스
- 📊 **대화 맥락 유지**: 이전 대화 내용을 기억하여 연속적인 대화 가능

## 🏗️ 아키텍처

### 시스템 구성도

```
┌─────────────────────────────────────────────────────────┐
│                    내부 네트워크                          │
│                                                         │
│  ┌─────────────────┐                                   │
│  │  Streamlit UI   │  (Port 9191)                      │
│  │   (Web Chat)    │  - 사용자 인터페이스               │
│  └────────┬────────┘  - 채팅 기능 제공                  │
│           │                                             │
│           ↓ HTTP Request                                │
│  ┌─────────────────┐                                   │
│  │  FastAPI Server │  (Port 9393)                      │
│  │  (API Proxy)    │  - OpenAI 호환 API                │
│  └────────┬────────┘  - 스트리밍 지원                   │
│           │                                             │
│           ↓ API Call (내부망)                           │
│  ┌─────────────────────────────┐                       │
│  │   내부 LLM 프록시 서버         │                      │
│  │  (예: Azure OpenAI Service) │                      │
│  └─────────────────────────────┘                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 동작 방식

1. **사용자 → Streamlit UI**: 직원이 웹 브라우저로 채팅 인터페이스 접속
2. **Streamlit → FastAPI**: UI가 로컬 FastAPI 서버(9393 포트)로 요청 전송
3. **FastAPI → 내부 LLM 서버**: FastAPI가 기업 내부 LLM API 서버로 프록시
4. **LLM 응답 → 사용자**: 스트리밍 방식으로 실시간 응답 전달

### 필수 요구사항

이 앱을 사용하려면 다음이 필요합니다:

- ✅ **내부 LLM API 서버**: OpenAI Chat Completion API와 호환되는 내부 서버 필요
- ✅ **API 인증 키**: 내부 LLM 서버 접근을 위한 인증 키
- ✅ **네트워크 접근**: 폐쇄망 내에서 내부 LLM 서버로의 HTTP/HTTPS 통신 가능해야 함

**지원하는 LLM API 서버 예시:**
- Azure OpenAI Service (기업 전용)
- AWS Bedrock (VPC 내부)
- 자체 구축 LLM Gateway
- OpenAI API 프록시 서버

## 📦 설치

### 필수 요구사항

- Python 3.8 이상
- pip

### 의존성 패키지 설치

```bash
pip install -r requirements.txt
```

## ⚙️ 설정

### 1. 환경 변수 설정

`.env.example` 파일을 복사하여 `.env` 파일을 생성합니다:

```bash
cp .env.example .env
```

`.env` 파일을 편집하여 필요한 정보를 입력합니다:

```env
# LLM API 인증 키 (필수)
API_KEY=your_api_key_here

# LLM API 엔드포인트 URL (필수)
LLM_API_BASE_URL=https://your-internal-llm-api.com/v1/chat/completions

# 서버 포트 설정 (선택사항)
FASTAPI_PORT=9393
STREAMLIT_PORT=9191
```

**주요 환경 변수:**
- `API_KEY`: LLM API 인증 키 (필수)
- `LLM_API_BASE_URL`: 내부 LLM API 서버 주소 (필수)
- `FASTAPI_PORT`: FastAPI 서버 포트 (기본값: 9393)
- `STREAMLIT_PORT`: Streamlit 앱 포트 (기본값: 9191)
- `API_TIMEOUT`: API 타임아웃 초 (기본값: 30)
- `LOG_LEVEL`: 로그 레벨 (기본값: INFO)

전체 환경 변수 목록은 [.env.example](.env.example) 파일을 참고하세요.

## 🚀 실행

### 1. FastAPI 프록시 서버 시작

```bash
bash scripts/start_server.sh
```

서버는 `http://localhost:9393`에서 실행됩니다.

### 2. Streamlit 웹 앱 시작

```bash
bash scripts/start_app.sh
```

웹 앱은 `http://localhost:9191`에서 실행됩니다.

### 3. 브라우저에서 접속

```
http://localhost:9191
```

## 🛑 중지

### FastAPI 서버 중지

```bash
bash scripts/stop_server.sh
```

### Streamlit 앱 중지

```bash
bash scripts/stop_app.sh
```

## 📖 사용법

### 기본 채팅

1. 웹 브라우저에서 `http://localhost:9191` 접속
2. 화면 하단의 채팅 입력창에 질문 입력
3. 실시간으로 스트리밍되는 답변 확인

### 설정 변경

사이드바에서 다음 설정을 조정할 수 있습니다:

- **모델 선택**: gpt-4o, gpt-4o-mini 등
- **Temperature**: 응답의 창의성 조절 (0.0 ~ 1.5)
- **Max Tokens**: 최대 응답 길이 (50 ~ 4096)
- **Chain of Thought**: 단계별 사고 과정 요청
- **스트리밍 응답**: 실시간 응답 표시 On/Off

### 대화 초기화

사이드바의 "🧹 대화 초기화" 버튼을 클릭하여 대화 내역을 초기화할 수 있습니다.

## 🔧 고급 설정

모든 설정은 `.env` 파일을 통해 관리됩니다.

### 주요 설정 항목

**API 설정:**
```env
API_TIMEOUT=30           # API 호출 타임아웃 (초)
API_MAX_RETRIES=3        # 최대 재시도 횟수
API_RETRY_DELAY=1        # 재시도 대기 시간 (초)
```

**포트 설정:**
```env
FASTAPI_PORT=9393        # FastAPI 서버 포트
STREAMLIT_PORT=9191      # Streamlit 앱 포트
```

**로깅 설정:**
```env
LOG_LEVEL=INFO           # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_DIR=logs             # 로그 파일 저장 디렉토리
```

**CORS 설정:**
```env
CORS_ORIGINS=*           # 허용할 출처 (콤마로 구분)
# 프로덕션 예시: CORS_ORIGINS=https://your-domain.com,https://app.your-domain.com
```

설정 변경 후 서버를 재시작하면 즉시 적용됩니다.

## 📂 프로젝트 구조

```
simple-llm-chat/
├── README.md              # 프로젝트 문서
├── requirements.txt       # Python 패키지 의존성
├── .env                   # 환경 변수 (git에서 제외)
├── .env.example          # 환경 변수 템플릿
├── .gitignore            # Git 제외 파일
├── src/
│   ├── __init__.py       # 패키지 초기화
│   ├── config.py         # 설정 관리
│   ├── server.py         # FastAPI 프록시 서버
│   ├── client.py         # LLM API 클라이언트 모듈
│   ├── app.py            # Streamlit 웹 채팅 UI
│   └── utils/            # 유틸리티 함수
│       ├── __init__.py
│       └── helpers.py
├── scripts/
│   ├── start_server.sh   # FastAPI 서버 시작
│   ├── start_app.sh      # Streamlit 앱 시작
│   ├── stop_server.sh    # FastAPI 서버 중지
│   └── stop_app.sh       # Streamlit 앱 중지
└── logs/                 # 로그 파일 저장 디렉토리 (자동 생성)
```

## 🔍 API 엔드포인트

### POST /v1/chat/completions

OpenAI Chat Completion API와 호환되는 채팅 완성 엔드포인트

**요청 예시:**

```json
{
  "model": "gpt-4o",
  "messages": [
    {"role": "user", "content": "안녕하세요"}
  ],
  "stream": false,
  "temperature": 0.7,
  "max_tokens": 1024
}
```

**응답 예시:**

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "gpt-4o",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "안녕하세요! 무엇을 도와드릴까요?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 15,
    "total_tokens": 25
  }
}
```

### GET /health

서버 상태 확인 엔드포인트

### GET /stats

서버 통계 정보 확인 엔드포인트

## 🛠️ 트러블슈팅

### 서버가 시작되지 않는 경우

1. 포트가 이미 사용 중인지 확인:
   ```bash
   lsof -i :9393  # FastAPI 서버
   lsof -i :9191  # Streamlit 앱
   ```

2. 기존 프로세스 종료:
   ```bash
   bash scripts/stop_server.sh
   bash scripts/stop_app.sh
   ```

### API 키 오류

`.env` 파일에 올바른 `API_KEY`가 설정되어 있는지 확인하세요.

### 로그 확인

- **FastAPI 서버**: `logs/uvicorn_YYYY-MM-DD.log`
- **Streamlit 앱**: `logs/chat_app_YYYY-MM-DD.log`

## 🤝 기여

이슈 및 Pull Request는 언제든 환영합니다!

## 📧 문의

프로젝트 관련 문의사항은 이슈로 등록해주세요.

---

<div align="center">
Made with ❤️ for Internal LLM Server Environments
</div>

---
---

# English Version

> Simple chat app using internal LLM server

## 📝 Introduction

**Simple LLM Chat** is a lightweight chat application using internal LLM API server.
Originally developed for use in a telecom company's isolated network, it has been successfully adopted by team members for daily use.

### 🎯 Use Case

This project is designed for environments with:

- **Internal LLM Server**: Organizations with in-house LLM API infrastructure
- **OpenAI-Compatible API**: Internal servers supporting OpenAI Chat Completion API format

**Real-world Architecture:**
```
[User PC] → [Simple LLM Chat] → [Internal LLM Proxy] → [LLM Model]
              (This App)          (Internal Infra)      (GPT-4, etc.)
```

### Key Features

- 🚀 **Simple Architecture**: FastAPI proxy + Streamlit UI
- 🔄 **OpenAI Compatible**: Compatible with OpenAI Chat Completion API
- 💬 **Real-time Streaming**: Supports streaming responses for instant feedback
- 🎨 **Intuitive UI**: Easy-to-use Streamlit-based chat interface
- 📊 **Context Awareness**: Maintains conversation history for continuous dialogue

## 🏗️ Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   Internal Network                      │
│                                                         │
│  ┌─────────────────┐                                   │
│  │  Streamlit UI   │  (Port 9191)                      │
│  │   (Web Chat)    │  - User Interface                 │
│  └────────┬────────┘  - Chat Features                  │
│           │                                             │
│           ↓ HTTP Request                                │
│  ┌─────────────────┐                                   │
│  │  FastAPI Server │  (Port 9393)                      │
│  │  (API Proxy)    │  - OpenAI Compatible              │
│  └────────┬────────┘  - Streaming Support              │
│           │                                             │
│           ↓ API Call (Internal Network)                │
│  ┌─────────────────────────────┐                       │
│  │   Internal LLM Proxy Server  │                      │
│  │  (e.g., Azure OpenAI)        │                      │
│  └─────────────────────────────┘                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### How It Works

1. **User → Streamlit UI**: Employee accesses chat interface via web browser
2. **Streamlit → FastAPI**: UI sends requests to local FastAPI server (port 9393)
3. **FastAPI → Internal LLM**: FastAPI proxies to internal LLM API server
4. **LLM Response → User**: Streaming response delivered in real-time

### Requirements

To use this app, you need:

- ✅ **Internal LLM API Server**: OpenAI Chat Completion API compatible server
- ✅ **API Authentication Key**: Credentials for internal LLM server access
- ✅ **Network Access**: HTTP/HTTPS connectivity to internal LLM server within airgap

**Supported LLM API Servers:**
- Azure OpenAI Service (Enterprise)
- AWS Bedrock (VPC Internal)
- Self-hosted LLM Gateway
- OpenAI API Proxy Server

## 📦 Installation

### Prerequisites

- Python 3.8+
- pip

### Install Dependencies

```bash
pip install -r requirements.txt
```

## ⚙️ Configuration

### 1. Environment Variables

Copy `.env.example` to create `.env`:

```bash
cp .env.example .env
```

Edit `.env` file with your configuration:

```env
# LLM API Authentication Key (Required)
API_KEY=your_api_key_here

# LLM API Endpoint URL (Required)
LLM_API_BASE_URL=https://your-internal-llm-api.com/v1/chat/completions

# Server Port Configuration (Optional)
FASTAPI_PORT=9393
STREAMLIT_PORT=9191
```

**Key Environment Variables:**
- `API_KEY`: LLM API authentication key (Required)
- `LLM_API_BASE_URL`: Internal LLM API server address (Required)
- `FASTAPI_PORT`: FastAPI server port (Default: 9393)
- `STREAMLIT_PORT`: Streamlit app port (Default: 9191)
- `API_TIMEOUT`: API timeout in seconds (Default: 30)
- `LOG_LEVEL`: Log level (Default: INFO)

See [.env.example](.env.example) for complete list of environment variables.

## 🚀 Usage

### 1. Start FastAPI Proxy Server

```bash
bash scripts/start_server.sh
```

Server runs at `http://localhost:9393`

### 2. Start Streamlit Web App

```bash
bash scripts/start_app.sh
```

Web app runs at `http://localhost:9191`

### 3. Access in Browser

```
http://localhost:9191
```

## 🛑 Stop Services

### Stop FastAPI Server

```bash
bash scripts/stop_server.sh
```

### Stop Streamlit App

```bash
bash scripts/stop_app.sh
```

## 📖 User Guide

### Basic Chat

1. Access `http://localhost:9191` in web browser
2. Enter your question in the chat input at the bottom
3. View streaming response in real-time

### Settings

Adjust settings in the sidebar:

- **Model Selection**: gpt-4o, gpt-4o-mini, etc.
- **Temperature**: Control response creativity (0.0 ~ 1.5)
- **Max Tokens**: Maximum response length (50 ~ 4096)
- **Chain of Thought**: Request step-by-step reasoning
- **Streaming Response**: Toggle real-time display On/Off

### Clear Conversation

Click "🧹 Clear Conversation" button in sidebar to reset chat history.

## 🔧 Advanced Configuration

All settings are managed via `.env` file.

### Key Configuration Items

**API Settings:**
```env
API_TIMEOUT=30           # API call timeout (seconds)
API_MAX_RETRIES=3        # Maximum retry attempts
API_RETRY_DELAY=1        # Retry delay (seconds)
```

**Port Settings:**
```env
FASTAPI_PORT=9393        # FastAPI server port
STREAMLIT_PORT=9191      # Streamlit app port
```

**Logging Settings:**
```env
LOG_LEVEL=INFO           # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_DIR=logs             # Log file directory
```

**CORS Settings:**
```env
CORS_ORIGINS=*           # Allowed origins (comma-separated)
# Production example: CORS_ORIGINS=https://your-domain.com,https://app.your-domain.com
```

Changes take effect after server restart.

## 📂 Project Structure

```
isolated-chat/
├── README.md              # Project documentation
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (gitignored)
├── .env.example          # Environment variable template
├── .gitignore            # Git ignore rules
├── src/
│   ├── __init__.py       # Package initialization
│   ├── config.py         # Configuration management
│   ├── server.py         # FastAPI proxy server
│   ├── client.py         # LLM API client
│   ├── app.py            # Streamlit web UI
│   └── utils/            # Utility functions
│       ├── __init__.py
│       └── helpers.py
├── scripts/
│   ├── start_server.sh   # Start FastAPI server
│   ├── start_app.sh      # Start Streamlit app
│   ├── stop_server.sh    # Stop FastAPI server
│   └── stop_app.sh       # Stop Streamlit app
└── logs/                 # Log directory (auto-created)
```

## 🔍 API Endpoints

### POST /v1/chat/completions

OpenAI Chat Completion API compatible endpoint

**Request Example:**

```json
{
  "model": "gpt-4o",
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "stream": false,
  "temperature": 0.7,
  "max_tokens": 1024
}
```

**Response Example:**

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "gpt-4o",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 15,
    "total_tokens": 25
  }
}
```

### GET /health

Server health check endpoint

### GET /stats

Server statistics endpoint

## 🛠️ Troubleshooting

### Server Won't Start

1. Check if port is already in use:
   ```bash
   lsof -i :9393  # FastAPI server
   lsof -i :9191  # Streamlit app
   ```

2. Stop existing processes:
   ```bash
   bash scripts/stop_server.sh
   bash scripts/stop_app.sh
   ```

### API Key Error

Verify correct `API_KEY` is set in `.env` file.

### Check Logs

- **FastAPI Server**: `logs/uvicorn_YYYY-MM-DD.log`
- **Streamlit App**: `logs/chat_app_YYYY-MM-DD.log`

## 🤝 Contributing

Issues and Pull Requests are welcome!

## 📧 Contact

Please submit issues for any questions or feedback.

---

<div align="center">
Made with ❤️ for Internal LLM Server Environments
</div>

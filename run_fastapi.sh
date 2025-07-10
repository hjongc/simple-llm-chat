#!/bin/bash
# ▶️ 실행 날짜 기준 로그 디렉토리 설정
LOG_DIR="logs"
LOG_FILE="$LOG_DIR/uvicorn_$(date '+%Y-%m-%d').log"
PID_FILE="$LOG_DIR/fastapi.pid"
mkdir -p "$LOG_DIR"

# ▶️ 중복 실행 방지 체크
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "⚠️ FastAPI 서버가 이미 실행 중입니다. (PID: $PID)"
        echo "👉 먼저 기존 프로세스를 종료해주세요."
        exit 1
    else
        echo "🧹 기존 PID 파일 정리 중..."
        rm "$PID_FILE"
    fi
fi

# ▶️ 로그 출력
echo "🚀 FastAPI 서버 시작: $(date)"
echo "📄 로그 파일: $LOG_FILE"

# ▶️ 백그라운드 실행 (stdout+stderr를 로그파일에 저장)
nohup uvicorn fastapi_server:app --host 0.0.0.0 --port 9393 --reload >> "$LOG_FILE" 2>&1 &

# ▶️ PID 저장
echo $! > "$PID_FILE"
echo "🔢 PID: $(cat $PID_FILE)"
echo "✅ FastAPI 서버가 백그라운드에서 실행 중입니다."
#!/bin/bash
# 로그 디렉토리 생성
LOG_DIR="./logs"
mkdir -p $LOG_DIR

# 날짜 기반 로그 파일명
LOG_FILE="$LOG_DIR/chat_app_$(date +%Y-%m-%d).log"
PID_FILE="$LOG_DIR/chat_app.pid"

# 중복 실행 방지 체크
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "⚠️ Streamlit 앱이 이미 실행 중입니다. (PID: $PID)"
        echo "👉 먼저 기존 프로세스를 종료해주세요."
        exit 1
    else
        echo "🧹 기존 PID 파일 정리 중..."
        rm "$PID_FILE"
    fi
fi

# 백그라운드 실행
echo "🚀 MI Project Agent (chat_app.py)를 9191 포트에서 백그라운드 실행 중..."
nohup streamlit run chat_app.py --server.port 9191 --server.headless true > "$LOG_FILE" 2>&1 &

# PID 저장
echo $! > "$PID_FILE"
echo "📄 로그 파일: $LOG_FILE"
echo "🔢 PID: $(cat $PID_FILE)"
echo "✅ Streamlit 앱이 백그라운드에서 실행 중입니다."
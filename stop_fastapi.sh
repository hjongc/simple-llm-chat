#!/bin/bash
PID_FILE="./logs/fastapi.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    echo "🛑 FastAPI 서버 종료 중... (PID: $PID)"
    
    # 프로세스가 실제로 실행 중인지 확인
    if kill -0 "$PID" 2>/dev/null; then
        # 일반 종료 시도
        kill "$PID"
        
        # 3초 대기 후 강제 종료 확인
        sleep 3
        if kill -0 "$PID" 2>/dev/null; then
            echo "⚠️ 일반 종료 실패. 강제 종료 시도 중..."
            kill -9 "$PID"
            sleep 1
            
            if kill -0 "$PID" 2>/dev/null; then
                echo "❌ 강제 종료도 실패했습니다. 수동으로 확인해주세요."
                exit 1
            else
                echo "✅ 강제 종료 완료"
            fi
        else
            echo "✅ 종료 완료"
        fi
        
        rm "$PID_FILE"
    else
        echo "⚠️ 해당 PID의 프로세스가 이미 종료되었습니다."
        echo "🧹 PID 파일 정리 중..."
        rm "$PID_FILE"
    fi
else
    echo "⚠️ 실행 중인 FastAPI 서버의 PID 정보를 찾을 수 없습니다."
    echo "👉 'logs/fastapi.pid' 파일이 존재하지 않습니다."
    echo "🔍 수동으로 프로세스를 확인해보세요:"
    echo "   ps aux | grep uvicorn"
fi 
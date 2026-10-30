#!/usr/bin/env bash
# 서버 실행 (작업 공간 루트에서: bash ui/run.sh)
# 미리보기·컨테이너 환경은 기본값 0.0.0.0, 혼자 쓰는 로컬 PC 는 HOST=127.0.0.1 bash ui/run.sh
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8501}"
echo "listening on $HOST:$PORT"
exec python -m streamlit run ui/app.py --server.address "$HOST" --server.port "$PORT" \
  --server.headless true --browser.gatherUsageStats false

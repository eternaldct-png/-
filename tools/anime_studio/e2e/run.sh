#!/bin/bash
# コマドリの E2E（ブラウザで通しで操作する）。文章AIは「AIなし」、声なしで動かす。
#   bash tools/anime_studio/e2e/run.sh
set -euo pipefail
cd "$(dirname "$0")/../../.."
DATA="$(mktemp -d)"
PORT="${PORT:-5097}"
KOMADORI_DIR="$DATA" python3 tools/anime_studio/run.py --no-browser --port "$PORT" > "$DATA/server.log" 2>&1 &
PID=$!
trap 'kill $PID 2>/dev/null; rm -rf "$DATA"' EXIT
for _ in $(seq 1 50); do curl -s -o /dev/null "http://127.0.0.1:$PORT/" && break; sleep 0.2; done
curl -s -X POST -H "X-Komadori: 1" -H "Content-Type: application/json" -d '{"ai_engine":"simple","voice_engine":"none"}' "http://127.0.0.1:$PORT/api/settings" > /dev/null
BASE="http://127.0.0.1:$PORT" SHOTS="${SHOTS:-}" node tools/anime_studio/e2e/flows.e2e.cjs

#!/usr/bin/env bash
# E2E を毎回まっさらなデータで動かす: bash tools/meeting_notes/e2e/run.sh [スクショの保存先]
set -euo pipefail
cd "$(dirname "$0")/../../.."
DATA="$(mktemp -d)"
PORT="${PORT:-5099}"
python3 tools/meeting_notes/e2e/fake_server.py --port "$PORT" --data "$DATA" >"$DATA/server.log" 2>&1 &
PID=$!
trap 'kill $PID 2>/dev/null || true; rm -rf "$DATA"' EXIT
for _ in $(seq 1 30); do curl -sf -o /dev/null "http://127.0.0.1:$PORT/" && break; sleep 0.5; done
NODE_PATH="${NODE_PATH:-$(npm root -g)}" node tools/meeting_notes/e2e/flows.e2e.cjs "http://127.0.0.1:$PORT" "${1:-}"

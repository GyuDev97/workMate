#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3를 설치한 뒤 다시 실행해 주세요."
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "Node.js와 npm을 설치한 뒤 다시 실행해 주세요."
  exit 1
fi

PYTHON_ENV="${WORKMATE_PYTHON_ENV:-/Users/bizntech/Desktop/python/.venv}"
PYTHON_BIN="$PYTHON_ENV/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python 가상환경을 찾을 수 없습니다: $PYTHON_ENV"
  echo "WORKMATE_PYTHON_ENV 환경 변수로 가상환경 위치를 지정해 주세요."
  exit 1
fi

if ! "$PYTHON_BIN" -c 'import fastapi, pypdf, docx, openpyxl' >/dev/null 2>&1; then
  echo "백엔드 의존성을 설치합니다..."
  "$PYTHON_BIN" -m pip install -r backend/requirements.txt
fi

if [[ ! -d node_modules ]]; then
  echo "프런트엔드 의존성을 설치합니다..."
  npm install
fi

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID"
  fi
}
trap cleanup EXIT INT TERM

echo "WorkMate 백엔드를 시작합니다..."
(cd backend && "$PYTHON_BIN" -m uvicorn server.main:app --port 8765) &
BACKEND_PID=$!

echo "WorkMate 데스크톱 앱을 시작합니다..."
npm run dev

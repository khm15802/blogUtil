#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3.11 이상이 필요합니다. https://www.python.org/downloads/macos/ 에서 설치해 주세요."
    read -r -p "Enter를 누르면 종료합니다."
    exit 1
fi

if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
    echo "Python 3.11 이상이 필요합니다. 현재 버전: $(python3 --version 2>&1)"
    read -r -p "Enter를 누르면 종료합니다."
    exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
    python3 -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'

if [ ! -f ".env" ]; then
    cp .env.example .env
fi

echo
echo "설치가 완료되었습니다. active-log-desktop.command를 더블클릭해 실행하세요."
read -r -p "Enter를 누르면 종료합니다."

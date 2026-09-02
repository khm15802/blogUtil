#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -x ".venv/bin/python" ]; then
    echo "Active Log가 설치되지 않았습니다. install-macos.command를 먼저 실행해 주세요."
    read -r -p "Enter를 누르면 종료합니다."
    exit 1
fi

exec .venv/bin/python -m active_log.desktop

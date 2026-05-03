#!/bin/sh
# 在线安装步骤（可独立调用，假设已有 Python 环境和 venv）
# 用法：sh scripts/install_online.sh [python可执行路径]

set -e

PYTHON="${1:-python3}"

cd "$(dirname "$0")/.."

echo "[online] 升级 pip..."
"$PYTHON" -m pip install --upgrade pip -q

echo "[online] 安装依赖..."
"$PYTHON" -m pip install -r requirements.txt -q

echo "[online] 完成"

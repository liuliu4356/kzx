#!/bin/sh
# 三思GDB巡检平台 — 自动安装脚本（POSIX sh）
# 支持 Linux / macOS，Python 3.10+
# 用法：sh scripts/install.sh

set -e

PYTHON=""
for cmd in python3.12 python3.11 python3.10 python3 python; do
  if command -v "$cmd" >/dev/null 2>&1; then
    ver=$("$cmd" -c 'import sys; print(sys.version_info >= (3, 10))' 2>/dev/null || echo "False")
    if [ "$ver" = "True" ]; then
      PYTHON="$cmd"
      break
    fi
  fi
done

if [ -z "$PYTHON" ]; then
  echo "[ERROR] 未找到 Python 3.10+，请先安装 Python 3.10 或更高版本。"
  echo "        下载：https://www.python.org/downloads/"
  exit 1
fi

echo "[OK] 使用 Python：$($PYTHON --version)"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

if [ ! -f "requirements.txt" ]; then
  echo "[ERROR] 未找到 requirements.txt，请在项目根目录运行此脚本。"
  exit 1
fi

echo "[1/3] 创建虚拟环境..."
if [ ! -d "venv" ]; then
  "$PYTHON" -m venv venv
  echo "      已创建 venv/"
else
  echo "      venv/ 已存在，跳过创建"
fi

if [ -f "venv/bin/activate" ]; then
  . venv/bin/activate
else
  . venv/Scripts/activate 2>/dev/null || true
fi

echo "[2/3] 安装依赖（在线）..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "      依赖安装完成"

echo "[3/3] 初始化配置..."
if [ ! -f "config.yaml" ] && [ -f "config.example.yaml" ]; then
  cp config.example.yaml config.yaml
  echo "      已生成 config.yaml（请按需修改）"
else
  echo "      config.yaml 已存在，跳过"
fi

echo ""
echo "=============================="
echo " 安装完成！"
echo "=============================="
echo ""
echo " 启动 Web 界面："
echo "   source venv/bin/activate   # Linux/macOS"
echo "   python -m src.main web"
echo ""
echo " 或直接运行："
echo "   python -m src.main web --host 0.0.0.0 --port 8000"
echo ""

#!/bin/sh
# 离线安装脚本 — 从 packages/ 目录安装依赖（无需联网）
# 用法：sh scripts/install_offline.sh [python可执行路径]
#
# 前提：已解压 offline_packages.tar.gz 到当前目录，
#       packages/ 目录含所有 whl 文件。

set -e

PYTHON="${1:-python3}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

PACKAGES_DIR="$PROJECT_DIR/packages"

if [ ! -d "$PACKAGES_DIR" ]; then
  echo "[ERROR] 未找到 packages/ 目录。"
  echo "        请先解压离线包：tar xzf offline_packages.tar.gz"
  exit 1
fi

echo "[offline] 检测 Python 版本..."
"$PYTHON" -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10+ required'" || {
  echo "[ERROR] 需要 Python 3.10+"
  exit 1
}
echo "          $($PYTHON --version)"

echo "[offline] 创建/激活虚拟环境..."
if [ ! -d "venv" ]; then
  "$PYTHON" -m venv venv
fi
if [ -f "venv/bin/activate" ]; then
  . venv/bin/activate
else
  . venv/Scripts/activate 2>/dev/null || true
fi

echo "[offline] 安装依赖（无需网络）..."
pip install --no-index --find-links="$PACKAGES_DIR" -r requirements.txt -q
echo "          完成"

echo "[offline] 初始化配置..."
if [ ! -f "config.yaml" ] && [ -f "config.example.yaml" ]; then
  cp config.example.yaml config.yaml
  echo "          已生成 config.yaml"
fi

echo ""
echo "=============================="
echo " 离线安装完成！"
echo "=============================="
echo " 启动：python -m src.main web"
echo ""

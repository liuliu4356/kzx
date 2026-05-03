#!/bin/sh
# 构建离线安装包（在有网络的环境运行）
# 用法：sh scripts/build_offline_package.sh
#
# 产物：offline_packages.tar.gz（包含所有 whl + 安装脚本）
#
# 注意：--platform 参数针对 Linux x86_64 manylinux2014。
#       如需 ARM64 或 Windows，请修改 --platform 参数。

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

PACKAGES_DIR="$PROJECT_DIR/packages"
OUTPUT="$PROJECT_DIR/offline_packages.tar.gz"

echo "[build] 清理旧包..."
rm -rf "$PACKAGES_DIR"
mkdir -p "$PACKAGES_DIR"

echo "[build] 下载依赖包（Linux x86_64, Python 3.10）..."
pip download \
  -r requirements.txt \
  --platform manylinux2014_x86_64 \
  --python-version 310 \
  --only-binary :all: \
  -d "$PACKAGES_DIR"

echo "[build] 打包离线安装包..."
tar czf "$OUTPUT" \
  packages/ \
  requirements.txt \
  scripts/install_offline.sh \
  config.example.yaml

echo ""
echo "[build] 完成！"
echo "        离线包路径：$OUTPUT"
echo "        大小：$(du -sh "$OUTPUT" | cut -f1)"
echo ""
echo "使用方法（目标机器）："
echo "  1. 上传 offline_packages.tar.gz 到目标机器"
echo "  2. tar xzf offline_packages.tar.gz"
echo "  3. sh scripts/install_offline.sh"
echo ""

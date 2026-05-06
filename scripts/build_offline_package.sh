#!/bin/sh
# 构建完整离线安装包（在有网络的环境运行）
# 用法：sh scripts/build_offline_package.sh [arch]
#
# arch 参数（可选）：
#   x86_64  — Intel/AMD 架构（默认）
#   aarch64 — ARM64 架构（麒麟+鲲鹏/飞腾）
#   both    — 同时打包两种架构
#
# 产物：
#   kzx-offline-x86_64.tar.gz   — x86_64 完整离线包
#   kzx-offline-aarch64.tar.gz  — ARM64 完整离线包（arch=aarch64 或 both 时生成）
#
# 包内容：源代码 + 依赖 whl + 一键启动脚本 + 配置模板

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

ARCH="${1:-x86_64}"
PY_VER="310"

G='\033[0;32m'; Y='\033[1;33m'; N='\033[0m'
ok()   { printf "${G}[OK]${N}  %s\n" "$1"; }
info() { printf "${Y}[>>]${N} %s\n" "$1"; }

# ── 检测 pip ──────────────────────────────────────────────────────
command -v pip >/dev/null 2>&1 || { echo "[ERROR] 未找到 pip，请先安装 Python 及 pip"; exit 1; }

_build_arch() {
    local target_arch="$1"
    local platform=""
    local output="$PROJECT_DIR/kzx-offline-${target_arch}.tar.gz"
    local pkgs_dir="$PROJECT_DIR/packages-${target_arch}"

    case "$target_arch" in
        x86_64)  platform="manylinux2014_x86_64" ;;
        aarch64) platform="manylinux2014_aarch64" ;;
        *) echo "[ERROR] 不支持的架构：$target_arch（支持 x86_64 / aarch64）"; exit 1 ;;
    esac

    info "构建 ${target_arch} 离线包..."

    # 下载 whl
    rm -rf "$pkgs_dir"
    mkdir -p "$pkgs_dir"

    info "下载依赖（Linux ${target_arch}, Python ${PY_VER}）..."
    pip download \
        -r requirements.txt \
        --platform "$platform" \
        --python-version "$PY_VER" \
        --only-binary :all: \
        -d "$pkgs_dir" -q \
        || {
            echo "[ERROR] 部分包无法以二进制形式下载，尝试补充下载..."
            pip download \
                -r requirements.txt \
                --platform "$platform" \
                --python-version "$PY_VER" \
                -d "$pkgs_dir" -q || true
        }

    ok "依赖下载完成，共 $(ls "$pkgs_dir" | wc -l) 个文件"

    # 打包：代码 + 依赖 + 启动脚本 + 配置
    info "打包中..."
    tar czf "$output" \
        --transform "s|^packages-${target_arch}|packages|" \
        "packages-${target_arch}/" \
        src/ \
        requirements.txt \
        quick-start.sh \
        scripts/install_offline.sh \
        config.example.yaml \
        --exclude="*.pyc" \
        --exclude="__pycache__" \
        --exclude=".git" \
        2>/dev/null || \
    tar czf "$output" \
        "packages-${target_arch}/" \
        src/ \
        requirements.txt \
        quick-start.sh \
        scripts/install_offline.sh \
        config.example.yaml

    rm -rf "$pkgs_dir"

    ok "完成：$output  ($(du -sh "$output" | cut -f1))"
}

echo ""
echo "================================================"
echo "  三思GDB巡检平台 — 离线包构建"
echo "================================================"
echo ""

case "$ARCH" in
    x86_64)  _build_arch x86_64 ;;
    aarch64) _build_arch aarch64 ;;
    both)
        _build_arch x86_64
        _build_arch aarch64
        ;;
    *) echo "[ERROR] 未知架构：$ARCH（可选：x86_64 / aarch64 / both）"; exit 1 ;;
esac

echo ""
echo "================================================"
echo "  部署方法（在麒麟内网目标机器上）："
echo ""
echo "  1. 上传对应架构的 kzx-offline-<arch>.tar.gz"
echo "  2. tar xzf kzx-offline-<arch>.tar.gz"
echo "  3. sh quick-start.sh"
echo ""
echo "  即可自动完成安装并启动 Web 服务，终端输出访问地址。"
echo "================================================"
echo ""

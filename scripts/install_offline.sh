#!/bin/sh
# 离线安装脚本 — 从 packages/ 目录安装依赖（无需联网）
# 用法：sh scripts/install_offline.sh [python可执行路径]
#
# 前提：已解压 kzx-offline-<arch>.tar.gz，packages/ 目录含所有 whl 文件

set -e

PYTHON="${1:-python3}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

PACKAGES_DIR="$PROJECT_DIR/packages"

G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; N='\033[0m'
ok()   { printf "${G}[✓]${N} %s\n" "$1"; }
warn() { printf "${Y}[!]${N} %s\n" "$1"; }
die()  { printf "${R}[✗] %s${N}\n" "$1" >&2; exit 1; }

echo ""
echo "=============================="
echo " 三思GDB巡检平台 — 离线安装"
echo "=============================="
echo ""

# ── 检查 packages/ ────────────────────────────────────────────────
[ -d "$PACKAGES_DIR" ] || die "未找到 packages/ 目录。\n  请先解压离线包：tar xzf kzx-offline-<arch>.tar.gz"

# ── 检测 Python ───────────────────────────────────────────────────
ok "检测 Python 版本..."
"$PYTHON" -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10+ required'" 2>/dev/null \
    || die "需要 Python 3.10+\n  麒麟系统安装：sudo yum install python3 -y"
ok "$($PYTHON --version)"

# ── 创建虚拟环境 ──────────────────────────────────────────────────
if [ ! -d "venv" ]; then
    "$PYTHON" -m venv venv || die "创建虚拟环境失败\n  请安装 venv：sudo yum install python3-venv -y"
    ok "虚拟环境已创建"
else
    ok "虚拟环境已存在，跳过"
fi

[ -f "venv/bin/activate" ] || die "虚拟环境激活失败"
. venv/bin/activate

# ── 离线安装依赖 ──────────────────────────────────────────────────
ok "安装依赖（离线，无需网络）..."
pip install --no-index --find-links="$PACKAGES_DIR" -r requirements.txt -q \
    || die "安装失败。packages/ 与当前系统架构不匹配？\n  请使用对应架构的离线包（x86_64 或 aarch64）"
ok "依赖安装完成"

# ── 初始化配置 ────────────────────────────────────────────────────
if [ ! -f "config.yaml" ] && [ -f "config.example.yaml" ]; then
    cp config.example.yaml config.yaml
    ok "已生成 config.yaml"
else
    ok "config.yaml 已存在，跳过"
fi

# ── 检测本机 IP ───────────────────────────────────────────────────
LOCAL_IP=$(ip route get 1.2.3.4 2>/dev/null | awk '/src/{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1);exit}}') || true
[ -z "$LOCAL_IP" ] && LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}') || true
[ -z "$LOCAL_IP" ] && LOCAL_IP="<本机IP>"

WEB_PORT=$(python -c "
import yaml
try:
    cfg = yaml.safe_load(open('config.yaml', encoding='utf-8')) or {}
    print(cfg.get('web', {}).get('port', 8000))
except: print(8000)
" 2>/dev/null || echo 8000)

echo ""
echo "=============================="
echo " 安装完成！"
echo "=============================="
echo ""
echo " 启动服务（推荐）："
echo "   sh quick-start.sh"
echo ""
echo " 或手动启动："
echo "   . venv/bin/activate"
echo "   python -m src.main web --host 0.0.0.0 --port ${WEB_PORT}"
echo ""
echo " 访问地址："
echo "   http://127.0.0.1:${WEB_PORT}"
echo "   http://${LOCAL_IP}:${WEB_PORT}"
echo ""

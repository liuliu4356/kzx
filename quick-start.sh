#!/bin/sh
# 三思GDB巡检平台 — 一键启动脚本
# 适用于麒麟 Linux 内网环境（x86_64 / ARM64）
# 用法：sh quick-start.sh
#
# 流程：检测Python → 创建虚拟环境 → 安装依赖（优先离线）→ 初始化配置 → 启动Web → 输出地址

set -e

# ── 颜色输出 ──────────────────────────────────────────────────────
G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; B='\033[1;34m'; N='\033[0m'
ok()   { printf "${G}[✓]${N} %s\n" "$1"; }
warn() { printf "${Y}[!]${N} %s\n" "$1"; }
die()  { printf "${R}[✗] %s${N}\n" "$1" >&2; exit 1; }

# ── 定位项目根目录 ────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
[ -f "$PROJECT_DIR/requirements.txt" ] || PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
[ -f "$PROJECT_DIR/requirements.txt" ] || die "找不到 requirements.txt，请在项目根目录运行：sh quick-start.sh"
cd "$PROJECT_DIR"

echo ""
printf "${B}======================================================${N}\n"
printf "${B}   三思GDB巡检平台 — 一键快速启动${N}\n"
printf "${B}======================================================${N}\n"
echo ""

# ── 1. 检测 Python 3.10+ ──────────────────────────────────────────
PYTHON=""
for cmd in python3.12 python3.11 python3.10 python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
        ver=$("$cmd" -c 'import sys; print(sys.version_info >= (3,10))' 2>/dev/null || echo "False")
        if [ "$ver" = "True" ]; then PYTHON="$cmd"; break; fi
    fi
done

if [ -z "$PYTHON" ]; then
    printf "${R}[✗] 未找到 Python 3.10+${N}\n" >&2
    echo ""
    echo "  麒麟系统安装 Python 3："
    echo "    sudo yum install python3 -y"
    echo "  或"
    echo "    sudo apt-get install python3 -y"
    exit 1
fi
ok "Python：$($PYTHON --version)"

# ── 2. 检测 venv 模块 ────────────────────────────────────────────
if ! "$PYTHON" -c "import venv" >/dev/null 2>&1; then
    printf "${R}[✗] 缺少 venv 模块${N}\n" >&2
    echo "  麒麟系统安装：sudo yum install python3-venv -y"
    exit 1
fi

# ── 3. 创建 / 复用虚拟环境 ───────────────────────────────────────
if [ ! -d "venv" ]; then
    "$PYTHON" -m venv venv
    ok "虚拟环境已创建：venv/"
else
    ok "虚拟环境已存在，复用"
fi

if [ -f "venv/bin/activate" ]; then
    . venv/bin/activate
else
    die "虚拟环境激活失败，请检查 Python 安装是否正常"
fi

# ── 4. 安装依赖（离线优先，回退在线）────────────────────────────
PACKAGES_DIR="$PROJECT_DIR/packages"

if [ -d "$PACKAGES_DIR" ] && ls "$PACKAGES_DIR"/*.whl >/dev/null 2>&1; then
    ok "发现离线安装包 packages/，使用离线模式"
    pip install --no-index --find-links="$PACKAGES_DIR" -r requirements.txt -q 2>&1 \
        || die "离线安装失败。\n  请确认 packages/ 是在相同架构（x86_64 或 ARM64）上构建的。\n  重新构建：sh scripts/build_offline_package.sh"
    ok "依赖安装完成（离线）"
else
    warn "未发现 packages/ 离线包，尝试联网安装..."
    warn "纯内网环境请先在联网机器运行：sh scripts/build_offline_package.sh"
    pip install --upgrade pip -q
    pip install -r requirements.txt -q \
        || die "依赖安装失败，请检查网络连接或准备离线包"
    ok "依赖安装完成（在线）"
fi

# ── 5. 初始化配置文件 ────────────────────────────────────────────
if [ ! -f "config.yaml" ]; then
    [ -f "config.example.yaml" ] || die "缺少 config.example.yaml，项目文件不完整"
    cp config.example.yaml config.yaml
    ok "已生成初始配置：config.yaml"
    echo ""
    warn "提示：如需对接真实 Prometheus/ES，请编辑 config.yaml 中的 url 地址"
    warn "      默认配置可直接启动，用于 Mock 演示和 Web 界面体验"
else
    ok "配置文件已存在：config.yaml"
fi

# ── 6. 读取端口配置 ──────────────────────────────────────────────
WEB_PORT=$(python -c "
import yaml, sys
try:
    cfg = yaml.safe_load(open('config.yaml', encoding='utf-8')) or {}
    print(cfg.get('web', {}).get('port', 8000))
except Exception:
    print(8000)
" 2>/dev/null || echo 8000)

# ── 7. 检测本机内网 IP ───────────────────────────────────────────
LOCAL_IP=""
LOCAL_IP=$(ip route get 1.2.3.4 2>/dev/null | awk '/src/{for(i=1;i<=NF;i++) if($i=="src") {print $(i+1); exit}}') \
    2>/dev/null || true
[ -z "$LOCAL_IP" ] && LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}') || true
[ -z "$LOCAL_IP" ] && LOCAL_IP="<本机IP>"

# ── 8. 启动 Web 服务 ─────────────────────────────────────────────
echo ""
printf "${B}======================================================${N}\n"
printf "${B}   服务启动中...${N}\n"
printf "${B}======================================================${N}\n"
echo ""
echo "  本机访问：http://127.0.0.1:${WEB_PORT}"
echo "  内网访问：http://${LOCAL_IP}:${WEB_PORT}"
echo ""
echo "  首次访问：注册管理员账号后即可使用"
echo "  停止服务：Ctrl + C"
echo ""
printf "${B}======================================================${N}\n"
echo ""

python -m src.main web --host 0.0.0.0 --port "$WEB_PORT"

#!/usr/bin/env bash
# ==============================================================
# 智能简历筛选工具 — 服务管理脚本
# 用法：bash deploy/scripts/start.sh [start|stop|restart|health]
# ==============================================================

set -euo pipefail

# ── 配置项（按需修改）──────────────────────────────────────────
PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
SERVER_DIR="$PROJECT_DIR/server"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WORKERS="${WORKERS:-1}"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/app.log"
PID_FILE="$LOG_DIR/app.pid"
HEALTH_URL="http://127.0.0.1:${PORT}/api/health"
HEALTH_TIMEOUT=10   # 秒
START_TIMEOUT=15    # 等待进程启动的最长秒数
# ──────────────────────────────────────────────────────────────

# ANSI 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
log_step()  { echo -e "${CYAN}[----]${NC}  $*"; }

# ── 准备日志目录 ─────────────────────────────────────────────
mkdir -p "$LOG_DIR"

# ── 查找 Python ──────────────────────────────────────────────
find_python() {
    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            echo "$cmd"
            return 0
        fi
    done
    log_error "未找到 Python，请先安装 Python 3.8+"
    exit 1
}

# ── 检查 uvicorn ─────────────────────────────────────────────
check_uvicorn() {
    local python="$1"
    if ! "$python" -m uvicorn --version &>/dev/null; then
        log_warn "未检测到 uvicorn，尝试安装依赖..."
        "$python" -m pip install -r "$SERVER_DIR/requirements.txt" --quiet
    fi
}

# ── 读取 PID（返回空串表示未运行）────────────────────────────
get_pid() {
    [[ -f "$PID_FILE" ]] || { echo ""; return; }
    local pid
    pid=$(<"$PID_FILE")
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        echo "$pid"
    else
        # PID 文件残留，清理
        rm -f "$PID_FILE"
        echo ""
    fi
}

# ── start ────────────────────────────────────────────────────
do_start() {
    local pid
    pid=$(get_pid)
    if [[ -n "$pid" ]]; then
        log_warn "服务已在运行中 (PID=$pid)，无需重复启动。"
        return 0
    fi

    local python
    python=$(find_python)
    check_uvicorn "$python"

    log_step "启动服务：$python -m uvicorn main:app  ($HOST:$PORT)"
    log_step "日志输出：$LOG_FILE"

    # 切换到 server 目录后台运行
    (
        cd "$SERVER_DIR"
        nohup "$python" -m uvicorn main:app \
            --host "$HOST" \
            --port "$PORT" \
            --workers "$WORKERS" \
            --log-level info \
            >>"$LOG_FILE" 2>&1 &
        echo $! > "$PID_FILE"
    )

    # 等待进程启动
    local waited=0
    while [[ $waited -lt $START_TIMEOUT ]]; do
        pid=$(get_pid)
        if [[ -n "$pid" ]]; then
            # 再探健康接口
            if _http_health &>/dev/null; then
                log_info "服务启动成功 ✓  PID=$pid  地址=http://$HOST:$PORT"
                return 0
            fi
        fi
        sleep 1
        (( waited++ )) || true
    done

    # 超时仍未健康
    pid=$(get_pid)
    if [[ -n "$pid" ]]; then
        log_warn "进程已启动 (PID=$pid)，但健康接口暂时未响应，请稍后执行 health 检查。"
    else
        log_error "服务启动失败，请查看日志：$LOG_FILE"
        exit 1
    fi
}

# ── stop ─────────────────────────────────────────────────────
do_stop() {
    local pid
    pid=$(get_pid)
    if [[ -z "$pid" ]]; then
        log_warn "服务未在运行。"
        return 0
    fi

    log_step "正在停止服务 (PID=$pid)..."
    kill -TERM "$pid" 2>/dev/null || true

    # 等待进程退出（最多 10 秒）
    local waited=0
    while kill -0 "$pid" 2>/dev/null && [[ $waited -lt 10 ]]; do
        sleep 1
        (( waited++ )) || true
    done

    if kill -0 "$pid" 2>/dev/null; then
        log_warn "进程未响应 SIGTERM，发送 SIGKILL..."
        kill -KILL "$pid" 2>/dev/null || true
    fi

    rm -f "$PID_FILE"
    log_info "服务已停止 ✓"
}

# ── restart ───────────────────────────────────────────────────
do_restart() {
    log_step "重启服务..."
    do_stop
    sleep 1
    do_start
}

# ── health ────────────────────────────────────────────────────
_http_health() {
    # 优先 curl，其次 wget
    if command -v curl &>/dev/null; then
        curl -sf --max-time "$HEALTH_TIMEOUT" "$HEALTH_URL"
    elif command -v wget &>/dev/null; then
        wget -qO- --timeout="$HEALTH_TIMEOUT" "$HEALTH_URL"
    else
        log_error "未找到 curl 或 wget，无法执行 HTTP 健康检查"
        return 1
    fi
}

do_health() {
    local pid
    pid=$(get_pid)

    echo -e "${CYAN}===== 健康检查 =====${NC}"

    if [[ -z "$pid" ]]; then
        log_error "进程状态：未运行（PID 文件不存在或进程已退出）"
        exit 1
    fi
    log_info "进程状态：运行中 (PID=$pid)"

    # 内存/CPU（macOS & Linux 兼容）
    if command -v ps &>/dev/null; then
        local ps_info
        ps_info=$(ps -p "$pid" -o pid=,pcpu=,pmem=,etime= 2>/dev/null || true)
        if [[ -n "$ps_info" ]]; then
            printf "  %-8s %-8s %-8s %s\n" "PID" "CPU%" "MEM%" "运行时长"
            printf "  %-8s %-8s %-8s %s\n" $ps_info
        fi
    fi

    # HTTP 健康接口
    log_step "探测接口：$HEALTH_URL"
    local body
    body=$(_http_health 2>/dev/null) || {
        log_error "HTTP 健康接口无响应"
        exit 1
    }
    log_info "HTTP 响应：$body"
    echo -e "${GREEN}===== 服务健康 ✓ =====${NC}"
}

# ── 入口 ──────────────────────────────────────────────────────
case "${1:-}" in
    start)   do_start   ;;
    stop)    do_stop    ;;
    restart) do_restart ;;
    health)  do_health  ;;
    *)
        echo "用法：$0 {start|stop|restart|health}"
        echo ""
        echo "  start    — 启动服务（后台运行）"
        echo "  stop     — 优雅停止服务"
        echo "  restart  — 停止后重新启动"
        echo "  health   — 检查进程状态与 HTTP 健康接口"
        exit 1
        ;;
esac

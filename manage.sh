#!/bin/bash

# --- 配置区 ---
WORKSPACE_DIR="$HOME/dofi_workspace"
MAC_SERVER_SCRIPT="mac_server.py"
DOCKER_CONTAINER="dofi"
DOCKER_BOT_SCRIPT="/app/workspace/tg_bot.py"
LOG_FILE="$WORKSPACE_DIR/dofi.log"
PID_FILE="$WORKSPACE_DIR/dofi.pid"

# --- 颜色定义 ---
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function start_dofi() {
    echo -e "${YELLOW}🐶 dofi 正在打卡上班...${NC}"

    # 1. 启动 Mac 本地服务 (Backend)
    if pgrep -f "$MAC_SERVER_SCRIPT" > /dev/null; then
        echo -e "   - 手 (Mac Server) 已经在运行了。"
    else
        echo -e "   - 正在启动 手 (Mac Server)..."
        cd "$WORKSPACE_DIR"
        # 后台运行并将日志输出到文件
        nohup ~/myenv3.13/bin/python3.13 "$MAC_SERVER_SCRIPT" > "$LOG_FILE" 2>&1 &
        echo $! > "$PID_FILE"
        sleep 2
    fi

    # 2. 启动 Docker 机器人 (Brain)
    echo -e "   - 正在唤醒 脑 (Docker Bot)..."
    # 确保容器是活着的
    docker start "$DOCKER_CONTAINER" > /dev/null 2>&1
    
    # 杀掉容器里可能残留的旧进程，防止重复回复
    docker exec "$DOCKER_CONTAINER" pkill -f tg_bot.py > /dev/null 2>&1
    
    # 后台启动新进程
    docker exec -d "$DOCKER_CONTAINER" python3 "$DOCKER_BOT_SCRIPT"
    
    echo -e "${GREEN}✅ dofi 已就位！随时待命。${NC}"
    echo -e "   (日志监控: tail -f $LOG_FILE)"
}

function stop_dofi() {
    echo -e "${YELLOW}💤 正在安排 dofi 下班...${NC}"

    # 1. 停止 Mac 服务
    if [ -f "$PID_FILE" ]; then
        kill $(cat "$PID_FILE") > /dev/null 2>&1
        rm "$PID_FILE"
        echo -e "   - 手 (Mac Server) 已停止。"
    else
        # 双重保险：按文件名杀
        pkill -f "$MAC_SERVER_SCRIPT" > /dev/null 2>&1 && echo -e "   - 手 (Mac Server) 已停止。"
    fi

    # 2. 停止 Docker 里的进程
    docker exec "$DOCKER_CONTAINER" pkill -f tg_bot.py > /dev/null 2>&1
    echo -e "   - 脑 (Docker Bot) 已休眠。"

    echo -e "${GREEN}👋 dofi 已退出。${NC}"
}

function status_dofi() {
    echo -e "${YELLOW}🔍 检查 dofi 状态:${NC}"
    
    # 检查 Mac Server
    if pgrep -f "$MAC_SERVER_SCRIPT" > /dev/null; then
        echo -e "   - ✋ 手 (Mac Server): ${GREEN}运行中${NC} (Port 5001)"
    else
        echo -e "   - ✋ 手 (Mac Server): ${RED}未运行${NC}"
    fi

    # 检查 Docker Bot
    if docker exec "$DOCKER_CONTAINER" pgrep -f tg_bot.py > /dev/null 2>&1; then
        echo -e "   - 🧠 脑 (Docker Bot): ${GREEN}运行中${NC}"
    else
        echo -e "   - 🧠 脑 (Docker Bot): ${RED}未运行${NC}"
    fi
}

function show_log() {
    echo -e "${YELLOW}📄 正在查看 dofi 的工作日志 (按 Ctrl+C 退出)...${NC}"
    tail -f "$LOG_FILE"
}

# --- 命令行参数解析 ---
case "$1" in
    start)
        start_dofi
        ;;
    stop)
        stop_dofi
        ;;
    restart)
        stop_dofi
        sleep 1
        start_dofi
        ;;
    status)
        status_dofi
        ;;
    log)
        show_log
        ;;
    *)
        echo "用法: dofi {start|stop|restart|status|log}"
        echo "示例: dofi start  (叫它上班)"
        echo "      do f i stop   (叫它下班)"
        exit 1
        ;;
esac
#!/bin/bash

# --- 配置区 ---
# --- 1. 加载配置文件 ---
# --- 1. 智能定位 (解决找不到配置文件的关键) ---
# 获取脚本所在的真实目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CONF_FILE="$SCRIPT_DIR/dofi.conf"

get_pid() {
    if [ -f "$PID_FILE" ]; then
        cat "$PID_FILE"
    fi
}

# --- 2. 加载配置 ---
if [ -f "$CONF_FILE" ]; then
    # 进入项目目录运行，防止相对路径出错
    cd "$SCRIPT_DIR"
    source "$CONF_FILE"
else
    echo "❌ 错误: 找不到配置文件: $CONF_FILE"
    exit 1
fi

# --- 2.1 加载 .env 环境变量（供监控脚本等使用） ---
ENV_FILE="$SCRIPT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    # 过滤掉注释行
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi
# --- 2. 检查必要变量是否加载 ---
if [ -z "$WORKSPACE_DIR" ]; then
    echo "❌ 配置错误: WORKSPACE_DIR 未定义"
    exit 1
fi

# --- 颜色定义 ---
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function start_dofi() {
    echo -e "${YELLOW}🐶 dofi 正在打卡上班...${NC}"

    # 1. 启动 Mac 本地服务 (Backend)
    if pgrep -f "$MAC_SERVER_SCRIPT" > /dev/null; then
        echo -e "   - 手 (Server) 已经在运行了。"
    else
        echo -e "   - 正在启动 手 (Server)..."
        cd "$WORKSPACE_DIR"
        # 后台运行并将日志输出到文件
        nohup ~/myenv3.13/bin/python3.13 "$MAC_SERVER_SCRIPT" > "$LOG_FILE" 2>&1 &
        echo $! > "$PID_FILE"
        sleep 2
    fi

    # 1.1 启动 Flink 监控脚本
    if pgrep -f "$FLINK_MONITOR_SCRIPT" > /dev/null; then
        echo -e "   - Flink 监控脚本 已经在运行了。"
    else
        echo -e "   - 正在启动 Flink 监控脚本..."
        cd "$WORKSPACE_DIR"
        nohup ~/myenv3.13/bin/python3.13 "$FLINK_MONITOR_SCRIPT" > "$FLINK_MONITOR_LOG_FILE" 2>&1 &
        echo $! > "$FLINK_MONITOR_PID_FILE"
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
        echo -e "   - 手 (Server) 已停止。"
    else
        # 双重保险：按文件名杀
        pkill -f "$MAC_SERVER_SCRIPT" > /dev/null 2>&1 && echo -e "   - 手 (Server) 已停止。"
    fi

    # 1.1 停止 Flink 监控脚本
    if [ -f "$FLINK_MONITOR_PID_FILE" ]; then
        kill $(cat "$FLINK_MONITOR_PID_FILE") > /dev/null 2>&1
        rm "$FLINK_MONITOR_PID_FILE"
        echo -e "   - Flink 监控脚本 已停止。"
    else
        pkill -f "$FLINK_MONITOR_SCRIPT" > /dev/null 2>&1 && echo -e "   - Flink 监控脚本 已停止。"
    fi

    # 2. 停止 Docker 里的进程
    docker exec "$DOCKER_CONTAINER" pkill -f tg_bot.py > /dev/null 2>&1
    echo -e "   - 脑 (Docker Bot) 已休眠。"

    echo -e "${GREEN}👋 dofi 已退出。${NC}"
}

function status_dofi() {
             echo "🔍 检查 dofi 状态:"

             # --- 1. 检查手 (Server) ---
             PID=$(get_pid)
             if [ -n "$PID" ] && ps -p "$PID" > /dev/null; then
                 echo -e "   - ✋ 手 (Server): ${GREEN}运行中 (PID $PID)${NC}"
             else
                 echo -e "   - ✋ 手 (Server): ${RED}未运行${NC}"
             fi

             # --- 1.1 检查 Flink 监控脚本 ---
             if [ -f "$FLINK_MONITOR_PID_FILE" ] && ps -p "$(cat "$FLINK_MONITOR_PID_FILE")" > /dev/null 2>&1; then
                 echo -e "   - 📈 Flink 监控: ${GREEN}运行中 (PID $(cat "$FLINK_MONITOR_PID_FILE"))${NC}"
             elif pgrep -f "$FLINK_MONITOR_SCRIPT" > /dev/null 2>&1; then
                 echo -e "   - 📈 Flink 监控: ${GREEN}运行中 (通过进程名检测)${NC}"
             else
                 echo -e "   - 📈 Flink 监控: ${RED}未运行${NC}"
             fi

             # --- 2. 检查脑 (Docker Bot) ---
             # 修复逻辑：使用 docker top 而不是 docker exec ps
             # 只要容器里有 python 进程在跑 bot 脚本，就算运行中
             BOT_FILENAME=$(basename "$DOCKER_BOT_SCRIPT") # 获取文件名, 如 bot.py

             # 先看容器活着没
             if ! docker ps | grep -q "$DOCKER_CONTAINER"; then
                  echo -e "   - 🧠 脑 (Docker Bot): ${RED}容器未启动${NC}"
                  return
             fi

             # 再看进程 (docker top 不需要容器内安装 ps)
             if docker top "$DOCKER_CONTAINER" | grep -q "$BOT_FILENAME"; then
                 echo -e "   - 🧠 脑 (Docker Bot): ${GREEN}运行中${NC}"
             else
                 echo -e "   - 🧠 脑 (Docker Bot): ${RED}未运行${NC} (容器活着，但 Python 脚本挂了)"
                 echo "     建议查看日志: dog log"
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
        echo "     dofi stop   (叫它下班)"
        exit 1
        ;;
esac
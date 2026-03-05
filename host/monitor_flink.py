import os
import time
import requests

# 1. 强制加载 .env 环境变量
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(env_path)
except ImportError:
    pass

# 2. 引入你刚才修改的执行器脚本 (需要和 monitor_flink.py 在同一个目录下)
import restartflinkjob

TG_TOKEN = os.getenv("TG_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("ALLOWED_USER_ID")
FLINK_JOBMANAGER_URL = os.getenv("FLINK_JOBMANAGER_URL", "http://localhost:8081")
JOB_MAPPING_FILE = os.path.join(os.path.dirname(__file__), "job_mapping.txt")

def send_telegram_message(text: str) -> None:
    """发送 Telegram 消息"""
    if not TG_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": str(TELEGRAM_CHAT_ID), "text": text, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"❌ Telegram 通知异常: {e}")

def get_app_id_by_name(job_name: str):
    """读取 job_mapping.txt 获取 APP_ID"""
    if not os.path.exists(JOB_MAPPING_FILE):
        return None
    with open(JOB_MAPPING_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            parts = line.split("=")
            if len(parts) == 2 and parts[0].strip() == job_name:
                return parts[1].strip()
    return None

def check_and_autorestart():
    """核心逻辑：获取状态 -> 查配置文件 -> 调用 restartflinkjob -> 返回战报"""
    try:
        url = f"{FLINK_JOBMANAGER_URL.rstrip('/')}/jobs/overview"
        jobs = requests.get(url, timeout=5).json().get("jobs", [])
    except Exception as e:
        return f"❌ 获取 Flink 任务列表失败: {e}"

    # 捕捉运行中的任务，防止历史同名失败任务产生干扰
    running_jobs = [j for j in jobs if j.get("state") == "RUNNING"]
    failed_raw = [j for j in jobs if j.get("state") in ("FAILED", "CANCELED", "FAILING")]
    
    running_names = {j.get("name") for j in running_jobs}
    failed_jobs = [j for j in failed_raw if j.get("name") not in running_names]

    if not failed_jobs:
        return "✅ 正常"

    msg_lines = [
        "🚨 **[Flink 任务监控告警]** 🚨",
        f"发现 {len(failed_jobs)} 个任务停止运行，开始自愈流程："
    ]

    for j in failed_jobs:
        job_name = j.get("name")
        state = j.get("state")
        msg_lines.append(f"\n⚠️ **任务离线**: {job_name} (当前状态: {state})")
        
        # 1. 获取映射配置
        app_id = get_app_id_by_name(job_name)
        
        if not app_id:
            msg_lines.append("└─ ❌ 跳过: 未在 `job_mapping.txt` 中找到该任务对应的 AppID。")
            continue
            
        msg_lines.append(f"└─ 🔍 匹配到 AppID: {app_id}，正在调用重启模块...")
        
        # 2. 调用 restartflinkjob.py
        restart_result = restartflinkjob.restart_job(app_id, job_name)
        
        # 3. 记录结果
        msg_lines.append(f"└─ 📝 **重启日志**:\n{restart_result}")

    return "\n".join(msg_lines)

def loop_monitor(interval_seconds: int = 60) -> None:
    """循环监控主函数"""
    startup_msg = f"🚀 [Dofi 监控中心]\nFlink 自动巡检与自愈程序已启动！\n频率: 每 {interval_seconds} 秒一次"
    print(startup_msg)
    send_telegram_message(startup_msg)

    while True:
        try:
            result_text = check_and_autorestart()
            current_time = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{current_time}] {result_text}")

            # 只要包含告警符号，就发送 Telegram
            if "🚨" in result_text or "❌" in result_text:
                send_telegram_message(f"[{current_time}]\n{result_text}")
                
        except Exception as e:
            current_time = time.strftime('%Y-%m-%d %H:%M:%S')
            err_msg = f"❌ Flink 监控崩溃: {e}"
            print(f"[{current_time}] {err_msg}")
            send_telegram_message(f"[{current_time}]\n{err_msg}")

        time.sleep(interval_seconds)

if __name__ == "__main__":
    loop_monitor(interval_seconds=60)
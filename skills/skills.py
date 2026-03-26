import os
import time
import subprocess
import requests
import pyautogui
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ==========================================
# ⚙️ 配置区
# ==========================================
FLINK_JOBMANAGER_URL = os.getenv("FLINK_JOBMANAGER_URL", "http://localhost:8081")

# StreamPark 配置 (必须在 .env 中配置正确的 URL 和 TOKEN)
STREAM_PARK_URL = os.getenv("STREAM_PARK_URL", "http://localhost:10000")
STREAMPARK_TOKEN = os.getenv("STREAMPARK_TOKEN", "")

# 映射文件路径: host/job_mapping.txt
JOB_MAPPING_FILE = os.path.join(os.path.dirname(__file__), "job_mapping.txt")

def _get_retry_session():
    session = requests.Session()
    retry = Retry(connect=3, read=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def _flink_get(path, timeout=5):
    url = f"{FLINK_JOBMANAGER_URL.rstrip('/')}{path}"
    session = _get_retry_session()
    return session.get(url, timeout=timeout)

def get_app_id_by_name(job_name):
    """从 job_mapping.txt 获取 APP_ID"""
    if not os.path.exists(JOB_MAPPING_FILE):
        return None
    with open(JOB_MAPPING_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("=")
            if len(parts) == 2 and parts[0].strip() == job_name:
                return parts[1].strip()
    return None

def _restart_via_streampark(job_name, app_id):
    """调用 StreamPark API 停止并重启任务"""
    if not STREAMPARK_TOKEN:
        return "❌ 缺少 STREAMPARK_TOKEN 环境变量，无法调用接口！"

    headers = {
        "Authorization": f"Bearer {STREAMPARK_TOKEN}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    session = _get_retry_session()
    
    try:
        # 1. 停止任务并触发 Savepoint
        # ⚠️ 核心修复：Python 布尔值必须写成小写字符串 "true"/"false"，否则 StreamPark(Java) 会报错
        cancel_url = f"{STREAM_PARK_URL}/api/flink/app/cancel"
        cancel_data = {"id": str(app_id), "savePointed": "true", "drain": "false"}
        
        cancel_res = session.post(cancel_url, headers=headers, data=cancel_data, timeout=10)
        if cancel_res.status_code != 200:
            return f"❌ 停止指令失败 (HTTP {cancel_res.status_code}): {cancel_res.text}"
        
        # 2. 阻塞等待 Savepoint 完成
        time.sleep(15)
        
        # 3. 重新启动
        start_url = f"{STREAM_PARK_URL}/api/flink/app/start"
        start_data = {"id": str(app_id), "allowNonRestored": "false"}
        
        start_res = session.post(start_url, headers=headers, data=start_data, timeout=10)
        if start_res.status_code == 200:
            return f"✅ 任务 [{job_name}] 重启指令发送成功！(AppID: {app_id})"
        else:
            return f"❌ 启动指令失败 (HTTP {start_res.status_code}): {start_res.text}"
            
    except Exception as e:
        return f"❌ 请求 StreamPark 发生网络异常: {str(e)}"

# ==========================================
# 🚀 Dofi Skills
# ==========================================

def restart_container(container_name):
    cmd = f"/usr/local/bin/docker restart {container_name}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        return f"✅ 容器 {container_name} 重启成功"
    else:
        return f"❌ 重启失败: {result.stderr}"

def get_flink_status():
    try:
        overview = _flink_get("/overview").json()
        jobs = _flink_get("/jobs/overview").json().get("jobs", [])
    except Exception as e:
        return f"❌ 获取 Flink 状态失败: {e}"

    running_jobs = [j for j in jobs if j.get("state") == "RUNNING"]
    failed = [j for j in jobs if j.get("state") in ("FAILED", "CANCELED", "FAILING")]

    lines = [
        f"🌐 JobManager: {FLINK_JOBMANAGER_URL}",
        f"TaskManagers: {overview.get('taskmanagers')}, Slots: {overview.get('slots-total')}",
        f"当前任务总数: {len(jobs)}, 运行中: {len(running_jobs)}, 异常: {len(failed)}",
    ]
    if jobs:
        lines.append("\n📋 任务列表:")
        for j in jobs:
            mark = " [⚠️异常]" if j in failed else ""
            lines.append(f"- {j.get('name')} | 状态: {j.get('state')} | JID: {j.get('jid')}{mark}")
    return "\n".join(lines)

def check_flink_and_autorestart():
    """监控任务状态 -> 获取 APP_ID -> 重启 -> 生成 Telegram 战报"""
    try:
        jobs = _flink_get("/jobs/overview", timeout=5).json().get("jobs", [])
    except Exception as e:
        return f"❌ 监控获取任务列表失败: {e}"

    running_jobs = [j for j in jobs if j.get("state") == "RUNNING"]
    # ⚠️ 核心修复：扩大捕捉范围，捕捉 FAILING 状态
    failed_raw = [j for j in jobs if j.get("state") in ("FAILED", "CANCELED", "FAILING")]

    # 排除正在运行的同名历史废弃任务
    running_names = {j.get("name") for j in running_jobs}
    failed_jobs = [j for j in failed_raw if j.get("name") not in running_names]
    
    if not failed_jobs:
        return "✅ 正常" # 返回纯文本，monitor.py 看到不包含 🚨 就会保持安静

    msg_lines = [
        "🚨 **[Flink 任务告警与自愈]** 🚨",
        f"探测到 {len(failed_jobs)} 个任务异常离线，正在介入处理："
    ]

    for j in failed_jobs:
        job_name = j.get("name")
        state = j.get("state")
        
        # 1. 查映射表
        app_id = get_app_id_by_name(job_name)
        
        if app_id:
            msg_lines.append(f"\n🔄 **开始重启**: {job_name} \n├─ 当前状态: {state}\n├─ 映射 AppID: {app_id}")
            # 2. 执行重启
            restart_msg = _restart_via_streampark(job_name, app_id)
            # 3. 记录重启结果
            msg_lines.append(f"└─ **执行结果**: {restart_msg}")
        else:
            msg_lines.append(f"\n⚠️ **跳过**: {job_name} \n└─ 原因: 未在 job_mapping.txt 找到对应的 AppID，请补充。")

    return "\n".join(msg_lines)

import datetime

def convert_time(time_input):
    """
    [技能] 时间戳与日期时间双向互转
    """
    try:
        time_input = str(time_input).strip()
        result_str = "" # 用一个变量接住结果
        
        if time_input.lower() == 'now':
            now = datetime.datetime.now()
            ts = int(now.timestamp())
            result_str = f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')} | 时间戳(秒): {ts} | 时间戳(毫秒): {ts*1000}"

        elif '-' in time_input or '/' in time_input:
            fmt = '%Y-%m-%d %H:%M:%S' if ':' in time_input else '%Y-%m-%d'
            time_input = time_input.replace('/', '-') 
            dt = datetime.datetime.strptime(time_input, fmt)
            ts = int(dt.timestamp())
            result_str = f"日期: {time_input} => 时间戳(秒): {ts} | 时间戳(毫秒): {ts*1000}"
        
        elif time_input.isdigit() or (time_input.startswith('-') and time_input[1:].isdigit()):
            ts = int(time_input)
            if ts > 1e11:  
                ts = ts / 1000.0
                unit = "毫秒"
            else:
                unit = "秒"
            dt = datetime.datetime.fromtimestamp(ts)
            result_str = f"时间戳({unit}): {time_input} => 日期时间: {dt.strftime('%Y-%m-%d %H:%M:%S')}"
        
        else:
            result_str = f"❌ 无法识别的时间格式: {time_input}。请传入时间戳、日期格式或 'now'"
            
        # ⚠️ 核心防呆：无论 AI 加没加 print()，我们自己在宿主机上先 print 一遍，确保内容能被截获
        print(result_str)
        return result_str
    
    except Exception as e:
        err = f"❌ 时间转换失败: {str(e)}"
        print(err)
        return err
import os
import requests
import time

STREAM_PARK_URL = os.getenv("STREAM_PARK_URL", "http://localhost:10000")
TOKEN = os.getenv("STREAMPARK_TOKEN")

def restart_job(app_id: str, job_name: str) -> str:
    """
    接收 app_id 和 job_name，执行 停止(Savepoint) -> 等待 -> 启动。
    """
    if not TOKEN:
        return f"❌ [{job_name}] 重启失败: 缺少 STREAMPARK_TOKEN 环境变量"

    # ⚠️ 核心修复 1：去除 "Bearer " 前缀，直接使用裸 Token
    # ⚠️ 核心修复 2：对齐 curl 中的 charset
    headers = {
        "Authorization": TOKEN,
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }
    messages = []
    
    # --- 1. 触发停止并打 Savepoint ---
    print(f"🔄 正在停止任务 {job_name} (AppID: {app_id}) 并触发 Savepoint...")
    # ⚠️ 核心修复 3：使用 openapi 路径
    cancel_url = f"{STREAM_PARK_URL.rstrip('/')}/openapi/app/cancel"
    
    cancel_data = {
        "id": str(app_id),
        "savePointed": "true",
        "drain": "false"
    }
    
    try:
        resp = requests.post(cancel_url, headers=headers, data=cancel_data, timeout=10)
        if resp.status_code == 200:
            messages.append(f"✅ [{job_name}] 停止指令成功，正在等待 Savepoint (15秒)...")
        else:
            return f"❌ [{job_name}] 停止失败 (HTTP {resp.status_code}): {resp.text}"
    except Exception as e:
        return f"❌ [{job_name}] 请求停止接口异常: {e}"

    # --- 2. 阻塞等待 ---
    time.sleep(15)
    
    # --- 3. 重新启动 ---
    print(f"🚀 正在启动任务 {job_name} (AppID: {app_id})...")
    start_url = f"{STREAM_PARK_URL.rstrip('/')}/openapi/app/start"
    
    # ⚠️ 核心修复 4：完全对齐你 curl 测试通过的参数列表
    start_data = {
        "id": str(app_id),
        "allowNonRestored": "false",
        "restoreFromSavepoint": "false",
        "argument": "",
        "savepointPath": ""
    }
    
    try:
        resp = requests.post(start_url, headers=headers, data=start_data, timeout=10)
        if resp.status_code == 200:
            messages.append(f"✅ [{job_name}] 启动指令发送成功！")
        else:
            messages.append(f"❌ [{job_name}] 启动失败 (HTTP {resp.status_code}): {resp.text}")
    except Exception as e:
        messages.append(f"❌ [{job_name}] 请求启动接口异常: {e}")
        
    return "\n".join(messages)

# 测试代码
if __name__ == "__main__":
    test_app_id = os.getenv("APP_ID", "100002")
    print(restart_job(test_app_id, "Test_Job_Name"))
# ~/clawdbot_workspace/skills.py
import os
import time
import pyautogui
import subprocess

# --- 技能 1: 打开 Flink 面板并截图 ---
def open_flink_and_screenshot():
    # 1. 强制使用 Chrome 打开，确保环境一致
    url = "http://localhost:8081"
    subprocess.run(["open", "-a", "Google Chrome", url])
    
    # 2. 等待页面加载 (根据你家网速调整)
    time.sleep(3)
    
    # 3. 截个全屏图 (AI 不需要看细节，它能看懂图)
    # 这里不需要返回图片数据，mac_server 会处理截图接口
    return "Flink Dashboard Opened"

# --- 技能 2: 重启 Docker 容器 (运维神技) ---
def restart_container(container_name):
    # 直接调用 Mac 的 docker 命令
    cmd = f"/usr/local/bin/docker restart {container_name}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        return f"✅ 容器 {container_name} 重启成功"
    else:
        return f"❌ 重启失败: {result.stderr}"

# --- 技能 3: 唤醒屏幕 (防止黑屏无法截图) ---
def wake_up_screen():
    # 模拟按一下 Shift 键唤醒
    pyautogui.press('shift')
    return "Screen Waked"
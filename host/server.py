from flask import Flask, request, jsonify, send_file
import pyautogui
import time
import os
import subprocess
import pyperclip 
import keyring
from io import BytesIO
import skills

app = Flask(__name__)

# 定义允许 AI 使用的工具库
SAFE_GLOBALS = {
    "pyautogui": pyautogui,
    "time": time,
    "os": os,
    "subprocess": subprocess,
    "pyperclip": pyperclip,
    "keyring": keyring,
    "skills": skills
    # "search": skills.send_alert
}


@app.route('/execute', methods=['POST'])
def execute_code():
    try:
        code = request.json.get('code', '')
        print(f"⚡️ 执行代码:\n{code}")
        # 执行代码
        exec(code, SAFE_GLOBALS)
        return jsonify({"status": "success", "msg": "Executed"})
    except Exception as e:
        print(f"❌ 执行报错: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500


@app.route('/screenshot', methods=['GET'])
def get_screenshot():
    try:
        img = pyautogui.screenshot()
        # --- 核心修复：如果是 RGBA 格式，强制转为 RGB ---
        if img.mode == 'RGBA':
            img = img.convert('RGB')

        img_io = BytesIO()
        img.save(img_io, 'JPEG', quality=70)
        img_io.seek(0)
        return send_file(img_io, mimetype='image/jpeg')
    except Exception as e:
        print(f"❌ 截图报错: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500


@app.route('/flink/status', methods=['GET'])
def flink_status():
    """返回 Flink 集群与任务状态的文本描述。"""
    try:
        text = skills.get_flink_status()
        return jsonify({"status": "success", "data": text})
    except Exception as e:
        print(f"❌ 获取 Flink 状态失败: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500


@app.route('/flink/check', methods=['POST'])
def flink_check():
    """
    手动触发一次检查 + 自动重启逻辑，返回文本描述。
    """
    try:
        # 允许通过 JSON 覆盖容器环境变量名，默认 FLINK_JOB_CONTAINER
        payload = request.get_json(silent=True) or {}
        container_env_var = payload.get("container_env_var", "FLINK_JOB_CONTAINER")
        text = skills.check_flink_and_autorestart(container_env_var=container_env_var)
        return jsonify({"status": "success", "data": text})
    except Exception as e:
        print(f"❌ Flink 检查失败: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500


@app.route('/')
def index():
    return """
    <html>
    <head><title>Dofi Control Panel</title></head>
    <body style="font-family: sans-serif; padding: 50px;">
        <h1>🐶 Dofi Status: <span style="color:green">Online</span></h1>
        <hr>
        <h3>🛠 已加载技能 (Skills)</h3>
        <ul>
            <li>open_flink() — 打开 Flink Dashboard</li>
            <li>restart_container(容器名)</li>
            <li>wake_up_screen()</li>
            <li>get_flink_status() — 查看 Flink 任务状态</li>
            <li>check_flink_and_autorestart() — 检查任务，失败则自动重启并返回结果</li>
        </ul>
        <p><strong>Flink 监控</strong>：由 Host 上的 <code>monitor_flink.py</code> 每 60 秒检查，状态变化时 Telegram 通知并触发自愈（需 <code>./manage.sh start</code> 一起启动）。</p>
        <hr>
        <p>手 (Mac Host): Port 5001 | 脑 (Docker Brain): 通过 API 调用本机</p>
    </body>
    </html>
    """


if __name__ == '__main__':
    print("🚀 Mac Server running on port 5001...")
    app.run(host='0.0.0.0', port=5001)
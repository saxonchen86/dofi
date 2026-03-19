from flask import Flask, request, jsonify, send_file
import pyautogui
import time
import os
import subprocess
import pyperclip
import keyring
from io import BytesIO

# 添加技能目录到 Python 路径，确保能够正确导入技能模块
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'skills'))

# 现在可以安全地导入技能模块
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
    "skills": skills,
    "convert_time": skills.convert_time
    # "search": skills.send_alert
}


import io
from contextlib import redirect_stdout
from flask import request, jsonify

# ... (其他代码保持不变) ...

@app.route('/execute', methods=['POST'])
def execute_code():
    data = request.json
    code = data.get('code', '')

    # 1. 创建一个“内存里的文本框”来接住 print 吐出来的字
    f = io.StringIO()
    
    # 2. 将所有的 print 输出强制重定向到 f 中
    with redirect_stdout(f):
        try:
            # 执行 AI 发过来的代码 (注意 SAFE_GLOBALS 是你注册技能的地方)
            exec(code, SAFE_GLOBALS)
            status = "success"
        except Exception as e:
            # 如果报错，也打印出来，这样也会被拦截并返回给 Telegram
            print(f"❌ 代码执行报错: {str(e)}")
            status = "error"

    # 3. 把拦截到的所有文字提取出来
    output_text = f.getvalue().strip()

    # 4. 连同状态一起打包，扔回给 Docker 里的 Bot
    return jsonify({
        "status": status,
        "output": output_text  # 👈 这是最关键的，把文字传回去！
    })

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
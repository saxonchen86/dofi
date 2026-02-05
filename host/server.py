from flask import Flask, request, jsonify, send_file
import pyautogui
import time
import os
import subprocess
import pyperclip 
import keyring # 导入 keyring 库 需要用到自动登录才会用到
from io import BytesIO
import skills  # <--- 1. 导入你的新文件 (确保在同一目录下)

app = Flask(__name__)

# 定义允许 AI 使用的工具库
SAFE_GLOBALS = {
    "pyautogui": pyautogui,
    "time": time,
    "os": os,
    "subprocess": subprocess,
    "pyperclip": pyperclip,
    "keyring": keyring,
    "skills": skills  # <--- 3. 核心：让 AI 能认识这个对象
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

# mac_server.py (只修改 screenshot 部分，其他不用动)

@app.route('/screenshot', methods=['GET'])
def get_screenshot():
    try:
        img = pyautogui.screenshot()
        
        # --- 核心修复：如果是 RGBA 格式，强制转为 RGB ---
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        # ---------------------------------------------

        img_io = BytesIO()
        img.save(img_io, 'JPEG', quality=70)
        img_io.seek(0)
        return send_file(img_io, mimetype='image/jpeg')
    except Exception as e:
        print(f"❌ 截图报错: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500

if __name__ == '__main__':
    # 端口 5001
    print("🚀 Mac Server running on port 5001...")
    app.run(host='0.0.0.0', port=5001)


@app.route('/')
def index():
    return """
    <html>
    <head><title>Dofi Control Panel</title></head>
    <body style="font-family: sans-serif; padding: 50px;">
        <h1>🐶 Dofi Status: <span style="color:green">Online</span></h1>
        <hr>
        <h3>🛠 已加载技能 (Skills):</h3>
        <ul>
            <li>open_flink_and_screenshot</li>
            <li>restart_container</li>
            <li>wake_up_screen</li>
        </ul>
        <hr>
        <p>Brain (Docker): Connected</p>
        <p>Hand (Mac): Running on Port 5001</p>
    </body>
    </html>
    """
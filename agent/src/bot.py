# workspace/tg_bot.py (安全确认版)
import os
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from openai import OpenAI

# --- 配置区 ---
TG_TOKEN = os.getenv("TG_TOKEN")
if not TG_TOKEN:
    # 如果没读到 Token，直接报错停止，防止瞎跑
    raise ValueError("❌ 致命错误: 环境变量 'TG_TOKEN' 未设置！请检查 .env 文件。")

# ⚠️ 关键点：环境变量读出来是字符串，必须转成整数，否则 ID 永远对不上
try:
    ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))
except ValueError:
    raise ValueError("❌ 配置错误: 'ALLOWED_USER_ID' 必须是纯数字！")

if ALLOWED_USER_ID == 0:
    print("⚠️ 警告: 未设置 ALLOWED_USER_ID，安全门禁已失效！")

# 其他配置 (带默认值，防止 .env 漏写)
MAC_SERVER_URL = os.getenv("MAC_SERVER_URL", "http://host.docker.internal:5001")
OLLAMA_URL = os.getenv("OPENAI_API_BASE", "http://host.docker.internal:11434/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3-coder:30b")

# --- 内存暂存区 (用于存放待确认的代码) ---
# 格式: {user_id: "print('hello')"}
PENDING_CODE = {}

# LLM 客户端
client = OpenAI(base_url=OLLAMA_URL, api_key="ollama")

SYSTEM_PROMPT = """
你是一个 Mac 自动化助手 Dofi。你可以通过生成 Python 代码来控制用户的电脑。
你可用的库：pyautogui, time, os, subprocess, pyperclip, keyring.

你拥有一个强大的技能库 `skills`，请优先使用它，而不是自己写底层代码。

【可用技能 Skills】:
1. 查看 Flink: skills.open_flink()
2. 重启容器: skills.restart_container("容器名")
3. 唤醒屏幕: skills.wake_up_screen()

【通用规则】:
- 如果用户问“Flink 怎么样了”，直接调用 skills.open_flink_and_screenshot()。
- 只有当没有现成技能时，才使用 pyautogui 写代码。

【安全规范】：
❌ 严禁在代码中明文写入密码！
✅ 必须使用 keyring 获取密码：
   password = keyring.get_password("system_login", "你的账号标识")
   pyautogui.write(password)

【关键规则】：
1. 输入英文：使用 pyautogui.write("text", interval=0.1)
2. 输入中文/特殊字符：必须使用粘贴法！
   pyperclip.copy("你好")
   pyautogui.hotkey("command", "v")
3. 打开软件：os.system("open -a 'Google Chrome'")
4. 按键：pyautogui.press("enter")
5. 登陆场景：先点击输入框，再 write 账号，按 tab，再 keyring 取密码 write，如果有三个输入框，还需要跟我确认实时六位数字的验证码，最后 enter。

当用户提出需求时，请直接生成可执行的 Python 代码块。
代码必须包裹在 ```python 和 ``` 之间。不要解释，直接给代码。
"""

async def send_screenshot_result(bot, chat_id):
    await bot.send_message(chat_id=chat_id, text="📸 正在获取执行结果截图...")
    try:
        res = requests.get(f"{MAC_SERVER_URL}/screenshot", timeout=15)
        if res.status_code == 200 and len(res.content) > 0:
            await bot.send_photo(chat_id=chat_id, photo=res.content)
        else:
            err_msg = res.text[:200] if res.text else "空数据"
            await bot.send_message(chat_id=chat_id, text=f"⚠️ 截图失败: {err_msg}")
    except Exception as e:
        await bot.send_message(chat_id=chat_id, text=f"❌ 截图请求异常: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # 1. 安全校验
    if user_id != ALLOWED_USER_ID:
        await context.bot.send_message(chat_id=chat_id, text="⛔️ 权限不足")
        return

    # 2. 检查是否有待确认的任务
    if user_id in PENDING_CODE:
        # 如果用户回复确认指令
        if user_text.lower() in ["ok", "确定", "yes", "执行", "go"]:
            code_to_run = PENDING_CODE.pop(user_id) # 取出并从暂存区删除
            
            await context.bot.send_message(chat_id=chat_id, text="🚀 收到确认，正在发送指令给 Mac...")
            try:
                res = requests.post(f"{MAC_SERVER_URL}/execute", json={"code": code_to_run}, timeout=30)
                if res.status_code == 200:
                    await context.bot.send_message(chat_id=chat_id, text="✅ 执行完毕")
                    await send_screenshot_result(context.bot, chat_id)
                else:
                    await context.bot.send_message(chat_id=chat_id, text=f"❌ Mac 端报错:\n{res.text}")
            except Exception as e:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ 网络请求异常: {e}")
            return # 结束本次对话
            
        else:
            # 如果回复其他内容，视为取消或新指令（这里简化为取消）
            del PENDING_CODE[user_id]
            await context.bot.send_message(chat_id=chat_id, text="🚫 已取消上一次的执行任务。正在处理新需求...")
            # 此时继续往下走，把当前文本作为新需求处理

    # 3. 处理新需求 (生成代码)
    await context.bot.send_message(chat_id=chat_id, text="🤖 正在生成方案，请稍候...")
    
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"用户需求: {user_text}\n请生成Python代码。"}
            ]
        )
        ai_reply = completion.choices[0].message.content
        
        # 提取代码
        code = ""
        if "```python" in ai_reply:
            code = ai_reply.split("```python")[1].split("```")[0].strip()
        elif "```" in ai_reply:
             code = ai_reply.split("```")[1].split("```")[0].strip()
        
        if not code:
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ AI 未返回代码，回答如下:\n{ai_reply}")
            return

        # 4. 【关键修改】不直接执行，而是存起来并发给用户确认
        PENDING_CODE[user_id] = code # 存入暂存区
        
        confirm_msg = (
            f"⚡️ **代码已生成，请审核：**\n\n"
            f"```python\n{code}\n```\n\n"
            f"👉 回复 **ok** 或 **确定** 开始执行\n"
            f"👉 回复其他内容取消"
        )
        # MarkdownV2 格式需要转义，这里用简单的 Markdown 或纯文本即可
        await context.bot.send_message(chat_id=chat_id, text=confirm_msg, parse_mode="Markdown")

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ 生成失败: {e}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TG_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("Telegram Bot (Safe Mode) is running...")
    app.run_polling()
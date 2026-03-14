# workspace/tg_bot.py (安全确认版 + 文本回传支持)
import os
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from openai import OpenAI

# ⚠️ 修复了拼写错误: promats -> prompts
PROMPT_DIR = "/app/workspace/agent/prompts"
PRIVATE_PROMPT_PATH = os.path.join(PROMPT_DIR, "system_private.txt")
DEFAULT_PROMPT_PATH = os.path.join(PROMPT_DIR, "system_default.txt")

def load_system_prompt():
    prompt_content = "你是一个 Python 助手。" # 兜底默认值

    # 优先读私有
    if os.path.exists(PRIVATE_PROMPT_PATH):
        print(f"🔒 加载私有 Prompt: {PRIVATE_PROMPT_PATH}")
        with open(PRIVATE_PROMPT_PATH, "r", encoding="utf-8") as f:
            prompt_content = f.read()
    # 其次读默认
    elif os.path.exists(DEFAULT_PROMPT_PATH):
        print(f"🌐 加载默认 Prompt: {DEFAULT_PROMPT_PATH}")
        with open(DEFAULT_PROMPT_PATH, "r", encoding="utf-8") as f:
            prompt_content = f.read()
    else:
        print(f"⚠️ 警告: 找不到 Prompt 文件！路径: {PROMPT_DIR}")

    return prompt_content

# --- 初始化 ---
SYSTEM_PROMPT = load_system_prompt()

# --- 配置区 ---
TG_TOKEN = os.getenv("TG_TOKEN")
if not TG_TOKEN:
    raise ValueError("❌ 致命错误: 环境变量 'TG_TOKEN' 未设置！请检查 .env 文件。")

try:
    ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))
except ValueError:
    raise ValueError("❌ 配置错误: 'ALLOWED_USER_ID' 必须是纯数字！")

if ALLOWED_USER_ID == 0:
    print("⚠️ 警告: 未设置 ALLOWED_USER_ID，安全门禁已失效！")

MAC_SERVER_URL = os.getenv("MAC_SERVER_URL", "http://host.docker.internal:5001")
OLLAMA_URL = os.getenv("OPENAI_API_BASE", "http://host.docker.internal:11434/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3-coder:30b")

PENDING_CODE = {}

client = OpenAI(base_url=OLLAMA_URL, api_key="ollama")

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
    
    # ✅ 特殊指令：Flink 相关
    lowered = user_text.lower().strip()
    is_flink_status = (
        lowered in ["/flink_status", "flink status", "查看flink状态"]
        or ("flink" in lowered and "状态" in user_text)
    )
    is_flink_check = (
        lowered in ["/flink_check", "flink check", "检查flink", "检查 flink"]
        or ("flink" in lowered and "检查" in user_text)
    )
    if is_flink_status:
        try:
            res = requests.get(f"{MAC_SERVER_URL}/flink/status", timeout=15)
            if res.status_code == 200:
                data = res.json()
                text = data.get("data") or "空结果"
                await context.bot.send_message(chat_id=chat_id, text=text)
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ 获取 Flink 状态失败: {res.status_code} {res.text[:200]}",
                )
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ 请求 Flink 状态异常: {e}")
        return
        
    if is_flink_check:
        if user_id != ALLOWED_USER_ID:
            await context.bot.send_message(chat_id=chat_id, text="⛔️ 仅授权用户可执行 Flink 检查/自愈。")
            return
        try:
            res = requests.post(f"{MAC_SERVER_URL}/flink/check", json={}, timeout=20)
            if res.status_code == 200:
                data = res.json()
                text = data.get("data") or "空结果"
                await context.bot.send_message(chat_id=chat_id, text=text)
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ Flink 检查失败: {res.status_code} {res.text[:200]}",
                )
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ 请求 Flink 检查异常: {e}")
        return

    # 1. 安全校验
    if user_id != ALLOWED_USER_ID:
        await context.bot.send_message(chat_id=chat_id, text="⛔️ 权限不足")
        return

    # 2. 检查是否有待确认的任务
    if user_id in PENDING_CODE:
        if user_text.lower() in ["ok", "确定", "yes", "执行", "go"]:
            code_to_run = PENDING_CODE.pop(user_id)
            
            await context.bot.send_message(chat_id=chat_id, text="🚀 收到确认，正在发送指令给 Mac...")
            try:
                res = requests.post(f"{MAC_SERVER_URL}/execute", json={"code": code_to_run}, timeout=30)
                if res.status_code == 200:
                    # ==========================================
                    # 🚀 核心修改区：解析 Mac Server 返回的 JSON 文字输出
                    # ==========================================
                    try:
                        res_data = res.json()
                        output_text = res_data.get("output", "").strip()
                        
                        if output_text:
                            # 传回了文字，用 Markdown 格式漂亮地打印出来
                            await context.bot.send_message(
                                chat_id=chat_id, 
                                text=f"📄 **执行结果**:\n`{output_text}`", 
                                parse_mode="Markdown"
                            )
                        else:
                            await context.bot.send_message(chat_id=chat_id, text="✅ 执行完毕 (无文字输出)")
                    except Exception as json_err:
                        # 兼容老版本的 Mac Server（如果还没改 server.py 的话）
                        await context.bot.send_message(chat_id=chat_id, text="✅ 执行完毕 (但解析文字返回失败)")

                    # 发完文字后，继续发送截图
                    await send_screenshot_result(context.bot, chat_id)
                    # ==========================================
                else:
                    await context.bot.send_message(chat_id=chat_id, text=f"❌ Mac 端报错:\n{res.text}")
            except Exception as e:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ 网络请求异常: {e}")
            return
            
        else:
            del PENDING_CODE[user_id]
            await context.bot.send_message(chat_id=chat_id, text="🚫 已取消上一次的执行任务。正在处理新需求...")

    # 3. 处理新需求
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
        
        code = ""
        if "```python" in ai_reply:
            code = ai_reply.split("```python")[1].split("```")[0].strip()
        elif "```" in ai_reply:
             code = ai_reply.split("```")[1].split("```")[0].strip()
        
        if not code:
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ AI 未返回代码，回答如下:\n{ai_reply}")
            return

        PENDING_CODE[user_id] = code
        
        confirm_msg = (
            f"⚡️ **代码已生成，请审核：**\n\n"
            f"```python\n{code}\n```\n\n"
            f"👉 回复 **ok** 或 **确定** 开始执行\n"
            f"👉 回复其他内容取消"
        )
        await context.bot.send_message(chat_id=chat_id, text=confirm_msg, parse_mode="Markdown")

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ 生成失败: {e}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TG_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("Telegram Bot (Safe Mode) is running...")
    app.run_polling()
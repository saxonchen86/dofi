# workspace/tg_bot.py (动态技能感知 + 架构师优化版)
import os
import sys
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from openai import OpenAI

# 1. 环境拓扑打通：确保核心库在系统路径中
BASE_DIR = "/app/workspace"
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from core.prompt_generator import PromptGenerator

# 2. 路径配置与生成器初始化
PROMPT_DIR = os.path.join(BASE_DIR, "agent/prompts")
SKILLS_DIR = os.path.join(BASE_DIR, "skills")
PRIVATE_PROMPT_PATH = os.path.join(PROMPT_DIR, "system_private.txt")
DEFAULT_PROMPT_PATH = os.path.join(PROMPT_DIR, "system_default.txt")

# 全局单例生成器，避免重复扫描 IO
generator = PromptGenerator(SKILLS_DIR)

def get_dynamic_system_prompt(user_query: str = ""):
    """
    根据用户输入的关键词，动态构建最精简、最相关的 System Prompt。
    这是 50w 年薪架构中为了降低 Token 成本和提高响应精准度的核心逻辑。
    """
    # A. 基础模板加载
    prompt_template = "你是一个 Python 助手。" 
    
    if os.path.exists(PRIVATE_PROMPT_PATH):
        with open(PRIVATE_PROMPT_PATH, "r", encoding="utf-8") as f:
            prompt_template = f.read()
    elif os.path.exists(DEFAULT_PROMPT_PATH):
        with open(DEFAULT_PROMPT_PATH, "r", encoding="utf-8") as f:
            prompt_template = f.read()
    else:
        print(f"⚠️ 警告: 找不到模板文件，使用兜底配置")

    # B. 动态分发技能 (核心升级点：按需注入)
    try:
        skills_block = generator.generate_contextual_skills(user_query)
    except Exception as e:
        print(f"❌ 动态技能生成异常: {e}")
        skills_block = "【注意】技能库加载失败，请优先使用标准库。"

    # C. 占位符替换
    placeholder = "{{SKILLS_BLOCK}}"
    if placeholder in prompt_template:
        full_prompt = prompt_template.replace(placeholder, skills_block)
    else:
        full_prompt = f"{prompt_template}\n\n{skills_block}"

    return full_prompt

# --- 配置区 ---
TG_TOKEN = os.getenv("TG_TOKEN")
if not TG_TOKEN:
    raise ValueError("❌ 致命错误: 环境变量 'TG_TOKEN' 未设置！请检查 .env 文件。")

try:
    ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))
except ValueError:
    raise ValueError("❌ 配置错误: 'ALLOWED_USER_ID' 必须是纯数字！")

MAC_SERVER_URL = os.getenv("MAC_SERVER_URL", "http://host.docker.internal:5001")
OLLAMA_URL = os.getenv("OPENAI_API_BASE", "http://host.docker.internal:11434/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3-coder:30b")

PENDING_CODE = {}
client = OpenAI(base_url=OLLAMA_URL, api_key="ollama")

async def send_screenshot_result(bot, chat_id):
    """获取并发送 Mac 端的执行截图"""
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
    
    # 1. 权限与特殊指令校验
    if user_id != ALLOWED_USER_ID:
        await context.bot.send_message(chat_id=chat_id, text="⛔️ 权限不足")
        return

    lowered = user_text.lower()
    
    # Flink 快捷指令处理
    if "flink" in lowered and ("状态" in user_text or "status" in lowered):
        try:
            res = requests.get(f"{MAC_SERVER_URL}/flink/status", timeout=15)
            text = res.json().get("data") if res.status_code == 200 else f"Error: {res.status_code}"
            await context.bot.send_message(chat_id=chat_id, text=text)
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ Flink 状态请求异常: {e}")
        return

    # 2. 任务确认逻辑 (ok/确定)
    if user_id in PENDING_CODE:
        if lowered in ["ok", "确定", "yes", "执行", "go"]:
            code_to_run = PENDING_CODE.pop(user_id)
            await context.bot.send_message(chat_id=chat_id, text="🚀 发送指令给 Mac...")
            try:
                res = requests.post(f"{MAC_SERVER_URL}/execute", json={"code": code_to_run}, timeout=30)
                if res.status_code == 200:
                    output_text = res.json().get("output", "").strip()
                    if output_text:
                        await context.bot.send_message(chat_id=chat_id, text=f"📄 **输出结果**:\n`{output_text}`", parse_mode="Markdown")
                    await send_screenshot_result(context.bot, chat_id)
                else:
                    await context.bot.send_message(chat_id=chat_id, text=f"❌ 执行失败:\n{res.text}")
            except Exception as e:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ 通讯异常: {e}")
            return
        else:
            del PENDING_CODE[user_id]
            await context.bot.send_message(chat_id=chat_id, text="🚫 任务已取消，正在重新思考...")

    # 3. 处理新需求：动态生成 Prompt 并调用 LLM
    await context.bot.send_message(chat_id=chat_id, text="🤖 正在分析需求...")
    
    try:
        # 【架构升级】：根据用户当前输入，动态加载最相关的技能
        current_system_prompt = get_dynamic_system_prompt(user_text)
        
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": current_system_prompt},
                {"role": "user", "content": f"需求: {user_text}\n请输出 Python 代码。"}
            ]
        )
        ai_reply = completion.choices[0].message.content
        
        # 代码块解析
        code = ""
        if "```python" in ai_reply:
            code = ai_reply.split("```python")[1].split("```")[0].strip()
        elif "```" in ai_reply:
             code = ai_reply.split("```")[1].split("```")[0].strip()
        
        if not code:
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ AI 未返回代码:\n{ai_reply}")
            return

        PENDING_CODE[user_id] = code
        confirm_msg = f"⚡️ **方案已就绪：**\n\n```python\n{code}\n```\n\n👉 回复 **ok** 执行，或回复其他取消。"
        await context.bot.send_message(chat_id=chat_id, text=confirm_msg, parse_mode="Markdown")

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ 生成方案失败: {e}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TG_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("🚀 Dofi 容器已启动 (动态技能模式)...")
    app.run_polling()
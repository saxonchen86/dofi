import os
import sys
from openai import OpenAI

# 1. 配置连接：指向 Orbstack 宿主机的 Ollama
client = OpenAI(
    base_url=os.getenv("OPENAI_API_BASE", "http://host.docker.internal:11434/v1"),
    api_key="ollama" # Ollama 不需要真实 Key
)

# 2. 获取模型名称（默认用你配置的 qwen3）
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3-coder:30b")

# 增加：支持从环境变量读取 System Prompt，默认为原来的配置
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "你是一个运行在Docker容器里的资深大数据开发助手。请直接生成Shell命令或Python代码，不要废话。")

def chat(prompt):
    print(f"🤖 正在思考 (Model: {MODEL_NAME})...")
    print("-" * 40)
    
    try:
        # 3. 发送请求给 Ollama
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT}, # 修改这里
                {"role": "user", "content": prompt}
            ],
            stream=True # 流式输出，像打字机一样
        )
        
        # 4. 打印结果
        full_content = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end="", flush=True)
                full_content += content
        print("\n" + "-" * 40)
        
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        print("💡 提示: 请检查 Ollama 是否在 Mac 上运行，且执行了 'launchctl setenv OLLAMA_HOST 0.0.0.0'")

if __name__ == "__main__":
    # 简单的命令行参数处理
    if len(sys.argv) < 2:
        print("使用方法: ai '你的指令'")
        sys.exit(1)
    
    user_prompt = " ".join(sys.argv[1:])
    chat(user_prompt)
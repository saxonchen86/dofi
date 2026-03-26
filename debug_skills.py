import os
import sys

# 1. 初始化路径环境 (确保与 Docker 容器内一致)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

try:
    from core.prompt_generator import PromptGenerator
    print("✅ 成功导入 PromptGenerator")
except ImportError as e:
    print(f"❌ 导入失败: {e}. 请确保 core/prompt_generator.py 存在。")
    sys.exit(1)

# 2. 配置路径
SKILLS_DIR = os.path.join(BASE_DIR, "skills")

def test_skill_scanning():
    print(f"🔍 正在扫描技能目录: {SKILLS_DIR}")
    
    if not os.path.exists(SKILLS_DIR):
        print(f"❌ 目录不存在: {SKILLS_DIR}")
        return

    # 初始化生成器
    gen = PromptGenerator(SKILLS_DIR)
    
    # --- 架构师细节：方法兼容性检查 ---
    # 检测 PromptGenerator 是旧版(generate_skills_block) 还是新版(generate_contextual_skills)
    has_new_method = hasattr(gen, 'generate_contextual_skills')
    has_old_method = hasattr(gen, 'generate_skills_block')

    if not has_new_method:
        print("\n⚠️  [版本警告]: 检测到你的 PromptGenerator 为旧版本，缺失动态过滤功能。")
        if has_old_method:
            print("💡 建议：请将 core/prompt_generator.py 更新为包含 generate_contextual_skills 的高级版本。")
            print("⏳ 降级运行：当前将尝试调用旧的 generate_skills_block 方法进行测试...")
            method_to_call = gen.generate_skills_block
        else:
            print("❌ 错误：PromptGenerator 对象没有任何可用的生成方法。")
            return
    else:
        print("🚀 检测到高级版 PromptGenerator，支持动态上下文过滤。")
        method_to_call = gen.generate_contextual_skills

    # 测试 A: 全量扫描
    print("\n--- [测试 A: 全量扫描结果] ---")
    try:
        full_block = method_to_call()
        print(full_block)
    except Exception as e:
        print(f"❌ 扫描失败: {e}")
    
    # 只有新版本才支持 B/C 测试
    if has_new_method:
        # 测试 B: 关键词命中测试 (模拟用户问 Flink)
        print("\n--- [测试 B: 关键词 'Flink' 命中测试] ---")
        flink_block = gen.generate_contextual_skills("帮我看看flink状态")
        print(flink_block)

        # 测试 C: 关键词命中测试 (模拟用户问 时间)
        print("\n--- [测试 C: 关键词 '时间' 命中测试] ---")
        time_block = gen.generate_contextual_skills("把这个时间戳转一下")
        print(time_block)
    else:
        print("\nℹ️  提示：旧版本不支持关键词动态过滤测试 (Test B/C)。")

if __name__ == "__main__":
    test_skill_scanning()
    print("\n💡 提示: 如果新函数没出现，请检查:")
    print("1. 函数名是否以 _ 开头 (会被忽略)")
    print("2. 是否写了 Docstring (函数下方的第一行字符串)")
    print("3. 文件是否同步到了容器内 (执行 ls -R skills 查看)")
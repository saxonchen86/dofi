import ast
import os
from pathlib import Path

class PromptGenerator:
    def __init__(self, skills_dir):
        self.skills_dir = Path(skills_dir).resolve()

    def _get_functions_from_file(self, file_path):
        """使用 AST 静态分析 Python 文件，提取函数名、参数和注释"""
        with open(file_path, "r", encoding="utf-8") as f:
            node = ast.parse(f.read())

        functions = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                # 忽略私有函数
                if item.name.startswith("_"):
                    continue

                # 提取参数名
                args = [arg.arg for arg in item.args.args]
                args_str = ", ".join(args)

                # 提取 docstring
                docstring = ast.get_docstring(item) or "无描述"
                # 只取第一行作为简短描述
                summary = docstring.split('\n')[0].strip()

                functions.append({
                    "name": item.name,
                    "args": args_str,
                    "summary": summary
                })
        return functions

    def generate_skills_block(self):
        """遍历目录生成最终的 Prompt 文本块"""
        output = ["【可用技能 Skills】:"]
        counter = 1

        # 递归遍历所有 .py 文件
        for path in sorted(self.skills_dir.rglob("*.py")):
            if path.name == "__init__.py":
                continue
            
            file_functions = self._get_functions_from_file(path)
            for func in file_functions:
                line = f"{counter}. {func['summary']}: skills.{func['name']}({func['args']})"
                output.append(line)
                counter += 1

        return "\n".join(output)

if __name__ == "__main__":
    # 假设当前脚本在 /core 目录下，寻找上级目录的 /skills
    current_dir = os.path.dirname(os.path.abspath(__file__))
    skills_path = os.path.join(current_dir, "../skills")
    
    gen = PromptGenerator(skills_path)
    skills_prompt = gen.generate_skills_block()
    
    print("--- 复制以下内容到你的 Dofi System Prompt ---")
    print(skills_prompt)
    print("-------------------------------------------")

    # 进阶操作：可以直接写回一个文本文件，方便 bot.py 启动时读取
    prompt_file = os.path.join(current_dir, "auto_skills_prompt.txt")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write(skills_prompt)
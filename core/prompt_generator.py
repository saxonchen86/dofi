import ast
import os
from pathlib import Path

class PromptGenerator:
    def __init__(self, skills_dir):
        self.skills_dir = Path(skills_dir).resolve()

    def _get_functions_from_file(self, file_path, category):
        """使用 AST 静态分析 Python 文件，提取函数名、参数、注释，并绑定类别"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                node = ast.parse(f.read())
        except Exception as e:
            print(f"⚠️ 无法解析文件 {file_path}: {e}")
            return []

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
                # 取第一行作为摘要，用于 Prompt 列表
                summary = docstring.split('\n')[0].strip()

                functions.append({
                    "name": item.name,
                    "args": args_str,
                    "summary": summary,
                    "category": category,
                    # 组合全文索引字段，用于后续关键词匹配
                    "search_index": f"{item.name} {summary} {category}".lower()
                })
        return functions

    def generate_contextual_skills(self, user_query: str = ""):
        """
        核心方法：基于用户查询的上下文，动态分发最相关的技能
        """
        all_skills = []
        # 1. 递归扫描所有技能，并识别类别 (基于子目录名)
        for path in sorted(self.skills_dir.rglob("*.py")):
            if path.name == "__init__.py":
                continue
            
            # 计算类别：根目录文件为 'core'，子目录文件取目录名
            rel_path = path.relative_to(self.skills_dir)
            category = rel_path.parts[0] if len(rel_path.parts) > 1 else "core"
            
            all_skills.extend(self._get_functions_from_file(path, category))

        # 2. 定义类别与关键词的映射 (语义路由表)
        category_map = {
            "flink": ["flink", "任务", "状态", "job", "checkpoint", "自愈", "autorestart"],
            "database": ["mysql", "sql", "查询", "数据库", "table", "schema", "db"],
            "docker": ["容器", "docker", "重启", "image", "restart", "container"],
            "core": ["时间", "now", "日期", "screen", "唤醒", "转换", "timestamp"]
        }

        # 3. 过滤逻辑
        query_lower = user_query.lower() if user_query else ""
        filtered_skills = []

        for skill in all_skills:
            # 命中规则：
            # - 是基础核心技能 (category == 'core')，始终包含
            # - 用户查询中包含该类别的特定关键词
            # - 用户查询直接命中了函数名或注释里的词
            is_core = skill['category'] == "core"
            is_category_hit = any(kw in query_lower for kw in category_map.get(skill['category'], []))
            is_direct_hit = query_lower and (query_lower in skill['search_index'])

            if is_core or is_category_hit or is_direct_hit:
                filtered_skills.append(skill)

        # 4. 格式化输出
        if not filtered_skills:
            return "【可用技能 Skills】: 当前无直接匹配的专用技能，请使用标准库完成任务。"

        output = ["【根据上下文推荐的可用技能 Skills】:"]
        for i, func in enumerate(filtered_skills, 1):
            line = f"{i}. {func['summary']}: skills.{func['name']}({func['args']})"
            output.append(line)

        return "\n".join(output)

    def generate_skills_block(self):
        """兼容旧版方法：直接返回所有技能"""
        return self.generate_contextual_skills(user_query="")

if __name__ == "__main__":
    # 执行自测逻辑
    current_dir = os.path.dirname(os.path.abspath(__file__))
    skills_path = os.path.join(current_dir, "../skills")
    
    gen = PromptGenerator(skills_path)
    # 模拟用户查询测试
    print(gen.generate_contextual_skills("帮我查下 Flink 的状态"))
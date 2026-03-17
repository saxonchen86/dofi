import json
import importlib.util
from pathlib import Path
from typing import Dict, Any, Callable, List

class SkillRegistry:
    def __init__(self, skills_dir: str = "/app/skills"):
        self.skills_dir = Path(skills_dir)
        # 给 Ollama 看的 JSON Schema 列表
        self.tools_schema: List[Dict[str, Any]] = []
        # Dofi 实际执行的 Python 函数映射字典
        self._tool_functions: Dict[str, Callable] = {}

    def load_all_skills(self):
        """动态扫描并加载目录下所有符合规范的 Skill"""
        if not self.skills_dir.exists():
            print(f"[Warning] 技能挂载目录不存在: {self.skills_dir}，请检查 Docker Volumes 配置。")
            return

        for skill_path in self.skills_dir.iterdir():
            # 忽略隐藏文件或非文件夹
            if not skill_path.is_dir() or skill_path.name.startswith("__"):
                continue

            schema_file = skill_path / "schema.json"
            code_file = skill_path / "tool.py"

            if not schema_file.exists() or not code_file.exists():
                print(f"[Skip] {skill_path.name}: 结构不完整，缺失 schema.json 或 tool.py")
                continue

            self._register_skill(skill_path, schema_file, code_file)

    def _register_skill(self, skill_path: Path, schema_file: Path, code_file: Path):
        # 1. 解析给 Ollama 的大纲 (Schema)
        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_content = json.load(f)
                tool_name = schema_content.get("name")
                if not tool_name:
                    raise ValueError("schema.json 中缺少核心的 'name' 字段")
        except Exception as e:
            print(f"[Error] 加载 {skill_path.name} 的 Schema 失败: {e}")
            return

        # 2. 黑魔法：动态导入 Python 模块
        try:
            module_name = f"skills.{skill_path.name}.tool"
            spec = importlib.util.spec_from_file_location(module_name, code_file)
            if spec is None or spec.loader is None:
                raise ImportError("无法构建 Module Spec")
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 强约定：tool.py 中必须有一个与 schema 中 name 完全同名的函数
            if not hasattr(module, tool_name):
                 raise AttributeError(f"tool.py 中未找到名为 '{tool_name}' 的入口函数")
            
            func = getattr(module, tool_name)
            
            # 3. 注册到 Dofi 的大脑内存中
            # 注意 Ollama 的 function calling 格式要求外层包裹 type 和 function
            self.tools_schema.append({"type": "function", "function": schema_content})
            self._tool_functions[tool_name] = func
            
            print(f"[Success] 🚀 Dofi 已成功装载技能: {tool_name}")

        except Exception as e:
            print(f"[Error] 编译/加载 {skill_path.name} 的 Python 代码失败: {e}")

    def get_ollama_tools(self) -> List[Dict[str, Any]]:
        """获取喂给 Ollama API 的工具清单"""
        return self.tools_schema

    def execute(self, tool_name: str, **kwargs) -> Any:
        """接收 LLM 的指令并触发物理世界的函数"""
        if tool_name not in self._tool_functions:
            return json.dumps({"error": f"技能 '{tool_name}' 未注册或已损坏。"})
        
        func = self._tool_functions[tool_name]
        try:
            print(f"[Execute] Dofi 正在调用技能: {tool_name}，参数: {kwargs}")
            return func(**kwargs)
        except Exception as e:
            return json.dumps({"error": f"技能执行期间发生异常: {str(e)}"})
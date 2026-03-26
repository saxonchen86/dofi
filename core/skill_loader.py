import os
import importlib.util
import sys
from pathlib import Path

class SkillLoader:
    def __init__(self, skills_dir):
        self.skills_dir = Path(skills_dir).resolve()
        # 建立一个空对象来承载技能函数
        self.skills = type('Skills', (), {})()

    def load_all(self):
        """扫描目录并动态加载所有 .py 文件中的函数"""
        # 将技能目录加入系统路径，确保 import 正常
        if str(self.skills_dir) not in sys.path:
            sys.path.append(str(self.skills_dir))
    
        # 递归扫描所有 .py 文件 (排除 __init__.py)
        for path in self.skills_dir.rglob("*.py"):
            if path.name == "__init__.py":
                continue
            
            # 计算模块名 (例如: database_query.sql_query_skill)
            relative_path = path.relative_to(self.skills_dir)
            module_name = ".".join(relative_path.with_suffix("").parts)
            
            try:
                # 动态导入模块
                spec = importlib.util.spec_from_file_location(module_name, path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # 将模块中不以 _ 开头的函数注入到 skills 对象中
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if callable(attr) and not attr_name.startswith("_"):
                        # 架构师细节：如果存在同名函数，后加载的会覆盖先加载的
                        setattr(self.skills, attr_name, attr)
                        
            except Exception as e:
                print(f"❌ 技能加载失败 [{module_name}]: {e}")
        
        return self.skills

# 实例化
loader = SkillLoader(os.path.join(os.path.dirname(__file__), "../skills"))
skills = loader.load_all()
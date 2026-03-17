"""
表格关联查询技能的工具文件
"""
from skills.table_schema_query_skill import table_schema_query_skill

# 这个文件只需要导出技能函数，让 skill_loader.py 能够加载
__all__ = ["table_schema_query_skill"]
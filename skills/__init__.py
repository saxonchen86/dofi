"""
技能模块入口文件
用于统一管理所有技能
"""
# 导入所有技能模块
from skills.dorker_management.docker_management_skill import SKILL_NAME as docker_skill_name, SKILL_DESCRIPTION as docker_skill_description, SKILL_FUNCTIONS as docker_skill_functions
from skills.table_schema_query_skill import SKILL_NAME as table_schema_skill_name, SKILL_DESCRIPTION as table_schema_skill_description, SKILL_FUNCTIONS as table_schema_skill_functions
from skills.sql_query_skill import SKILL_NAME as sql_query_skill_name, SKILL_DESCRIPTION as sql_query_skill_description, SKILL_FUNCTIONS as sql_query_skill_functions

# 所有技能的集合
SKILLS = {
    "docker_management": {
        "name": docker_skill_name,
        "description": docker_skill_description,
        "functions": docker_skill_functions
    },
    "table_schema_query": {
        "name": table_schema_skill_name,
        "description": table_schema_skill_description,
        "functions": table_schema_skill_functions
    },
    "sql_query": {
        "name": sql_query_skill_name,
        "description": sql_query_skill_description,
        "functions": sql_query_skill_functions
    }
}

# 为兼容旧版本，导出一些常用函数
from skills.dorker_management.docker_management import docker_management_skill
from skills.table_schema_query_skill import table_schema_query_skill
from skills.sql_query_skill import sql_query_skill

# 为了使技能可以被 server.py 直接调用，导出函数
from skills.time_utils import convert_time
from skills.dorker_management.docker_management import get_docker_containers, get_container_status, start_container, stop_container, restart_container, get_container_logs, get_docker_images
from skills.dorker_management.docker_management import docker_management_skill as docker_management

# 为兼容性保留旧的函数名
get_flink_status = table_schema_query_skill
check_flink_and_autorestart = sql_query_skill

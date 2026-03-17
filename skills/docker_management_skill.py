"""
Docker 管理技能
用于监控和管理 Docker 容器状态
"""

from skills.docker_management import docker_management_skill

# 技能配置
SKILL_NAME = "docker_management"
SKILL_DESCRIPTION = "Docker 容器状态管理技能，支持查看容器状态、启动、停止、重启容器等操作"
SKILL_FUNCTIONS = {
    "docker_management": {
        "function": docker_management_skill,
        "description": "Docker 容器管理技能",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "要执行的操作",
                    "enum": ["get_containers", "get_container_status", "start_container", "stop_container", "restart_container", "get_container_logs", "get_images"]
                },
                "container_name": {
                    "type": "string",
                    "description": "容器名称"
                },
                "lines": {
                    "type": "integer",
                    "description": "获取日志时显示的行数",
                    "default": 20
                }
            },
            "required": ["action"]
        }
    }
}
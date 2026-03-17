import subprocess
import json
from typing import List, Dict, Any

def get_docker_containers() -> str:
    """获取所有 Docker 容器的状态信息"""
    try:
        # 获取容器列表
        cmd = "/usr/local/bin/docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.RunningFor}}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)

        # 获取容器详细信息
        cmd = "/usr/local/bin/docker ps -a --format 'json'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)

        containers = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                try:
                    container = json.loads(line)
                    containers.append(container)
                except json.JSONDecodeError:
                    continue

        if not containers:
            return "没有找到任何容器"

        output = "Docker 容器状态:\n"
        output += "-" * 80 + "\n"
        output += f"{'容器名称':<20} {'状态':<20} {'镜像':<30} {'运行时间':<15}\n"
        output += "-" * 80 + "\n"

        for container in containers:
            name = container.get('Names', 'N/A')
            status = container.get('Status', 'N/A')
            image = container.get('Image', 'N/A')
            running_for = container.get('RunningFor', 'N/A')
            output += f"{name:<20} {status:<20} {image:<30} {running_for:<15}\n"

        return output
    except subprocess.CalledProcessError as e:
        return f"获取容器状态失败: {e.stderr}"
    except Exception as e:
        return f"获取容器状态时发生错误: {str(e)}"

def get_container_status(container_name: str) -> str:
    """获取指定容器的状态"""
    try:
        cmd = f"/usr/local/bin/docker ps -a --filter name={container_name} --format 'json'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)

        if not result.stdout.strip():
            return f"容器 {container_name} 未找到"

        container = json.loads(result.stdout.strip())
        status = container.get('Status', 'N/A')
        image = container.get('Image', 'N/A')
        created = container.get('CreatedAt', 'N/A')

        return f"容器 {container_name} 状态:\n状态: {status}\n镜像: {image}\n创建时间: {created}"
    except subprocess.CalledProcessError as e:
        return f"获取容器状态失败: {e.stderr}"
    except Exception as e:
        return f"获取容器状态时发生错误: {str(e)}"

def start_container(container_name: str) -> str:
    """启动指定的 Docker 容器"""
    try:
        cmd = f"/usr/local/bin/docker start {container_name}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return f"✅ 成功启动容器 {container_name}"
    except subprocess.CalledProcessError as e:
        return f"❌ 启动容器失败: {e.stderr}"
    except Exception as e:
        return f"启动容器时发生错误: {str(e)}"

def stop_container(container_name: str) -> str:
    """停止指定的 Docker 容器"""
    try:
        cmd = f"/usr/local/bin/docker stop {container_name}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return f"✅ 成功停止容器 {container_name}"
    except subprocess.CalledProcessError as e:
        return f"❌ 停止容器失败: {e.stderr}"
    except Exception as e:
        return f"停止容器时发生错误: {str(e)}"

def restart_container(container_name: str) -> str:
    """重启指定的 Docker 容器"""
    try:
        cmd = f"/usr/local/bin/docker restart {container_name}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return f"✅ 成功重启容器 {container_name}"
    except subprocess.CalledProcessError as e:
        return f"❌ 重启容器失败: {e.stderr}"
    except Exception as e:
        return f"重启容器时发生错误: {str(e)}"

def get_container_logs(container_name: str, lines: int = 20) -> str:
    """获取指定容器的日志"""
    try:
        cmd = f"/usr/local/bin/docker logs --tail {lines} {container_name}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        logs = result.stdout.strip()

        if not logs:
            return f"容器 {container_name} 没有日志"

        return f"容器 {container_name} 的日志 (最近 {lines} 行):\n{logs}"
    except subprocess.CalledProcessError as e:
        return f"获取容器日志失败: {e.stderr}"
    except Exception as e:
        return f"获取容器日志时发生错误: {str(e)}"

def get_docker_images() -> str:
    """获取所有 Docker 镜像"""
    try:
        cmd = "/usr/local/bin/docker images --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)

        return f"Docker 镜像列表:\n{result.stdout}"
    except subprocess.CalledProcessError as e:
        return f"获取镜像列表失败: {e.stderr}"
    except Exception as e:
        return f"获取镜像列表时发生错误: {str(e)}"

# 为技能系统提供接口
def docker_management_skill(action: str, container_name: str = "", lines: int = 20) -> str:
    """
    Docker 管理技能

    参数:
    - action: 要执行的操作 (get_containers, get_container_status, start_container,
              stop_container, restart_container, get_container_logs, get_images)
    - container_name: 容器名称 (用于 start, stop, restart, logs 等操作)
    - lines: 获取日志时显示的行数 (默认 20)

    返回:
    - 操作结果
    """
    if action == "get_containers":
        return get_docker_containers()
    elif action == "get_container_status":
        return get_container_status(container_name)
    elif action == "start_container":
        return start_container(container_name)
    elif action == "stop_container":
        return stop_container(container_name)
    elif action == "restart_container":
        return restart_container(container_name)
    elif action == "get_container_logs":
        return get_container_logs(container_name, lines)
    elif action == "get_images":
        return get_docker_images()
    else:
        return "❌ 未知的 Docker 操作，请使用: get_containers, get_container_status, start_container, stop_container, restart_container, get_container_logs, get_images"

# 示例使用方式
if __name__ == "__main__":
    # 测试不同的操作
    print("获取所有容器:")
    print(docker_management_skill("get_containers"))

    print("\n获取镜像列表:")
    print(docker_management_skill("get_images"))
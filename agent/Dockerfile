# filename: Dockerfile
FROM python:3.13-slim

# 1. 安装基础工具
# 修改点：将 openjdk-17 改为 default-jre-headless，解决构建报错
RUN apt-get update && apt-get install -y \
    curl \
    default-jre-headless \
    docker.io \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# 2. 安装 Python 依赖
# 包含 openai 库用于连接本地 Ollama
RUN pip install --no-cache-dir \
    openai \
    anthropic \
    docker \
    pyflink \
    kafka-python \
    pandas \
    sqlalchemy \
    pymysql \
    requests \
    python-telegram-bot

# 3. 设置工作目录
WORKDIR /app

# 4. 保持容器运行
CMD ["tail", "-f", "/dev/null"]
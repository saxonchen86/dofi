# 🐶 Dofi: Your AI Digital Employee on Mac

Dofi is an AI Agent architecture designed for **Mac M-series chips**. It separates the "Brain" (Dockerized LLM) from the "Hand" (Local Host Execution), allowing you to control your Mac remotely via Telegram using natural language, with strict security boundaries.

## 🚀 Features

- **Dockerized Brain**: Powered by local LLMs (Ollama/Qwen), keeping your data private.
- **Host Execution**: Can operate mouse/keyboard, take screenshots, and manage Docker containers via a secure local server.
- **Skill System**: Customizable Python functions (e.g., "Restart Flink", "Join Zoom").
- **Secure**: Human-in-the-loop confirmation required for code execution.

## 🛠 Architecture

[Telegram] <--> [Dofi Brain (Docker)] <--(HTTP)--> [Mac Hand (Local Server)] <--> [MacOS]

## ⚡️ Quick Start

### 1. Prerequisites
- MacBook (M-series recommended)
- Orbstack (or Docker Desktop)
- Python 3.10+
- Telegram Bot Token

### 2. Installation

```bash
# Clone the repo
git clone [https://github.com/your-username/dofi.git](https://github.com/your-username/dofi.git)
cd dofi

# Configure
cp .env.example .env
# Edit .env with your Token and ID
nano .env

# Install Host Dependencies
pip install -r host/requirements.txt

# Start Dofi
./manage.sh start
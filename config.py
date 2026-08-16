"""
Configuration for dumbproxy telegram bot
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))

# Balancer
BALANCER_IP = os.getenv("BALANCER_IP", "127.0.0.1")
BALANCER_PATH = os.getenv("BALANCER_PATH", "/opt/dumbproxy-balancer")

# Proxy Servers
PROXY_SERVERS = {
    "proxy1": {
        "ip": os.getenv("PROXY1_IP", "127.0.0.1"),
        "path": os.getenv("PROXY1_PATH", "/opt/dumbproxy-proxy"),
        "name": os.getenv("PROXY1_NAME", "Proxy #1"),
    },
    "proxy2": {
        "ip": os.getenv("PROXY2_IP", "127.0.0.1"),
        "path": os.getenv("PROXY2_PATH", "/opt/dumbproxy-proxy"),
        "name": os.getenv("PROXY2_NAME", "Proxy #2"),
    },
    "proxy3": {
        "ip": os.getenv("PROXY3_IP", "127.0.0.1"),
        "path": os.getenv("PROXY3_PATH", "/opt/dumbproxy-proxy"),
        "name": os.getenv("PROXY3_NAME", "Proxy #3"),
    },
}

# SSH
SSH_USER = os.getenv("SSH_USER", "root")
SSH_TIMEOUT = int(os.getenv("SSH_TIMEOUT", "10"))
SSH_KEY_PATH = os.getenv("SSH_KEY_PATH", os.path.expanduser("~/.ssh/id_rsa"))

# Monitoring
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Features
ENABLE_HEALTH_CHECKS = os.getenv("ENABLE_HEALTH_CHECKS", "true").lower() == "true"
ENABLE_AUTO_RESTART = os.getenv("ENABLE_AUTO_RESTART", "false").lower() == "true"
ENABLE_NOTIFICATIONS = os.getenv("ENABLE_NOTIFICATIONS", "true").lower() == "true"

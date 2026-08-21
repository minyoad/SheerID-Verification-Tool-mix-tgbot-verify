"""全局配置文件

环境变量统一由 load_env_file() 从 .env 文件加载（不经过 docker-compose 插值解析）：
  - Docker 部署：读取挂载卷 /app/data/.env
  - 本机直接运行：读取项目根目录 .env
"""
import os
from pathlib import Path

from dotenv import load_dotenv


def load_env_file() -> None:
    """加载 .env 配置文件，Docker 优先读 /app/data/.env，本地读项目根目录 .env"""
    docker_env = Path("/app/data/.env")
    if docker_env.is_file():
        load_dotenv(docker_env)
        return
    load_dotenv(Path(__file__).resolve().parent / ".env")


load_env_file()

# ==================== Telegram Bot 配置 ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "pk_oa")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/pk_oa")

# 管理员配置
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "123456789"))

# ==================== 积分配置 ====================
VERIFY_COST = int(os.getenv("VERIFY_COST", "1"))  # 验证消耗的积分
CHECKIN_REWARD = int(os.getenv("CHECKIN_REWARD", "1"))  # 签到奖励积分
INVITE_REWARD = int(os.getenv("INVITE_REWARD", "2"))  # 邀请奖励积分
REGISTER_REWARD = int(os.getenv("REGISTER_REWARD", "1"))  # 注册奖励积分

# ==================== 帮助链接 ====================
HELP_NOTION_URL = "https://rhetorical-era-3f3.notion.site/dd78531dbac745af9bbac156b51da9cc"

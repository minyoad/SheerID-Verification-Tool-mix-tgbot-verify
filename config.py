"""全局配置文件"""
import os
from pathlib import Path

from dotenv import load_dotenv


def load_env_file() -> None:
    """加载 .env 配置文件（由代码直接读取，不经过 docker-compose 插值解析）。

    - Docker 部署：优先读取挂载卷 /app/data/.env（宿主机对应 docker-compose.yml
      中 ${DATA_DIR:-/docker/sheerid}/data/.env），修改配置只需编辑宿主机该文件
      后重启容器；2CAPTCHA_API_KEY 等数字开头的变量名也可正常写入文件。
    - 本地直接运行：读取项目根目录 .env。
    """
    docker_env = Path("/app/data/.env")
    if docker_env.is_file():
        load_dotenv(docker_env)
        return
    load_dotenv(Path(__file__).resolve().parent / ".env")


load_env_file()

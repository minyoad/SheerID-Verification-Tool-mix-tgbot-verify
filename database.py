"""数据库统一入口

通过环境变量 DB_TYPE 选择数据库实现：
  DB_TYPE=sqlite（默认，Python 内置 sqlite3，零依赖，推荐单机部署）
  DB_TYPE=mysql（需要 MySQL 服务，参考 docker-compose.yml 中注释的 mysql 服务）

示例：
  DB_TYPE=sqlite SQLITE_PATH=/app/data/bot.db python bot.py
  DB_TYPE=mysql MYSQL_HOST=... python bot.py
"""
import os

from config import load_env_file

load_env_file()

DB_TYPE = os.getenv('DB_TYPE', 'sqlite').strip().lower()

if DB_TYPE == 'mysql':
    from database_mysql import Database
else:
    from database_sqlite import Database

__all__ = ['Database', 'DB_TYPE']

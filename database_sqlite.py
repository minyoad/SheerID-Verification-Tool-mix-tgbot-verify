"""SQLite 数据库实现

使用 Python 内置 sqlite3，零外部依赖，部署更简单。
接口与 database_mysql.py 完全一致，可通过环境变量 DB_TYPE 切换：
  DB_TYPE=sqlite（默认）或 DB_TYPE=mysql
"""
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class SQLiteDatabase:
    """SQLite 数据库管理类（与 MySQLDatabase 接口完全一致）"""

    def __init__(self):
        """初始化数据库连接"""
        self.db_path = os.getenv('SQLITE_PATH', 'bot.db')

        # 确保数据目录存在
        db_dir = os.path.dirname(os.path.abspath(self.db_path))
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        logger.info(f"SQLite 数据库初始化: {self.db_path}")
        self.init_database()

    def get_connection(self):
        """获取数据库连接（每次操作新建连接，避免线程问题）"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """初始化数据库表结构"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 用户表
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    balance INTEGER DEFAULT 1,
                    is_blocked INTEGER DEFAULT 0,
                    invited_by INTEGER,
                    created_at TEXT DEFAULT (datetime('now', 'localtime')),
                    last_checkin TEXT
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_username ON users(username)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_invited_by ON users(invited_by)")

            # 邀请记录表
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS invitations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    inviter_id INTEGER NOT NULL,
                    invitee_id INTEGER NOT NULL,
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_inviter ON invitations(inviter_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_invitee ON invitations(invitee_id)")

            # 验证记录表
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS verifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    verification_type TEXT NOT NULL,
                    verification_url TEXT,
                    verification_id TEXT,
                    status TEXT NOT NULL,
                    result TEXT,
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_v_user ON verifications(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_v_type ON verifications(verification_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_v_created ON verifications(created_at)")

            # 卡密表
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS card_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_code TEXT UNIQUE NOT NULL,
                    balance INTEGER NOT NULL,
                    max_uses INTEGER DEFAULT 1,
                    current_uses INTEGER DEFAULT 0,
                    expire_at TEXT,
                    created_by INTEGER,
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_key_code ON card_keys(key_code)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_by ON card_keys(created_by)")

            # 卡密使用记录
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS card_key_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_code TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    used_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cku_key ON card_key_usage(key_code)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cku_user ON card_key_usage(user_id)")

            conn.commit()
            logger.info("SQLite 数据库表初始化完成")

        except Exception as e:
            logger.error(f"初始化数据库失败: {e}")
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def create_user(
        self, user_id: int, username: str, full_name: str, invited_by: Optional[int] = None
    ) -> bool:
        """创建新用户"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO users (user_id, username, full_name, invited_by, created_at)
                VALUES (?, ?, ?, ?, datetime('now', 'localtime'))
                """,
                (user_id, username, full_name, invited_by),
            )

            if invited_by:
                cursor.execute(
                    "UPDATE users SET balance = balance + 2 WHERE user_id = ?",
                    (invited_by,),
                )

                cursor.execute(
                    """
                    INSERT INTO invitations (inviter_id, invitee_id, created_at)
                    VALUES (?, ?, datetime('now', 'localtime'))
                    """,
                    (invited_by, user_id),
                )

            conn.commit()
            return True

        except sqlite3.IntegrityError:
            conn.rollback()
            return False
        except Exception as e:
            logger.error(f"创建用户失败: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()

    def get_user(self, user_id: int) -> Optional[Dict]:
        """获取用户信息"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()

            if row:
                return dict(row)
            return None

        finally:
            cursor.close()
            conn.close()

    def user_exists(self, user_id: int) -> bool:
        """检查用户是否存在"""
        return self.get_user(user_id) is not None

    def is_user_blocked(self, user_id: int) -> bool:
        """检查用户是否被拉黑"""
        user = self.get_user(user_id)
        return user and user["is_blocked"] == 1

    def block_user(self, user_id: int) -> bool:
        """拉黑用户"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("UPDATE users SET is_blocked = 1 WHERE user_id = ?", (user_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"拉黑用户失败: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()

    def unblock_user(self, user_id: int) -> bool:
        """取消拉黑用户"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("UPDATE users SET is_blocked = 0 WHERE user_id = ?", (user_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"取消拉黑失败: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()

    def get_blacklist(self) -> List[Dict]:
        """获取黑名单列表"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM users WHERE is_blocked = 1")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()

    def add_balance(self, user_id: int, amount: int) -> bool:
        """增加用户积分"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (amount, user_id),
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"增加积分失败: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()

    def deduct_balance(self, user_id: int, amount: int) -> bool:
        """扣除用户积分"""
        user = self.get_user(user_id)
        if not user or user["balance"] < amount:
            return False

        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                (amount, user_id),
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"扣除积分失败: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()

    def can_checkin(self, user_id: int) -> bool:
        """检查用户今天是否可以签到"""
        user = self.get_user(user_id)
        if not user:
            return False

        last_checkin = user.get("last_checkin")
        if not last_checkin:
            return True

        last_date = datetime.fromisoformat(last_checkin).date()
        today = datetime.now().date()

        return last_date < today

    def checkin(self, user_id: int) -> bool:
        """用户签到（修复无限签到bug）"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 使用SQL原子操作，避免竞态条件
            # 只有当 last_checkin 是NULL 或者日期 < 今天时才更新
            cursor.execute(
                """
                UPDATE users
                SET balance = balance + 1, last_checkin = datetime('now', 'localtime')
                WHERE user_id = ? 
                AND (
                    last_checkin IS NULL 
                    OR date(last_checkin) < date('now', 'localtime')
                )
                """,
                (user_id,),
            )
            conn.commit()

            # 检查是否真的更新了（rowcount > 0 表示签到成功）
            success = cursor.rowcount > 0
            return success

        except Exception as e:
            logger.error(f"签到失败: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()

    def add_verification(
        self, user_id: int, verification_type: str, verification_url: str,
        status: str, result: str = "", verification_id: str = ""
    ) -> bool:
        """添加验证记录"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO verifications
                (user_id, verification_type, verification_url, verification_id, status, result, created_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
                """,
                (user_id, verification_type, verification_url, verification_id, status, result),
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"添加验证记录失败: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()

    def get_user_verifications(self, user_id: int) -> List[Dict]:
        """获取用户的验证记录"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT * FROM verifications
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()

    def create_card_key(
        self, key_code: str, balance: int, created_by: int,
        max_uses: int = 1, expire_days: Optional[int] = None
    ) -> bool:
        """创建卡密"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            expire_at = None
            if expire_days:
                expire_at = (datetime.now() + timedelta(days=expire_days)).strftime('%Y-%m-%d %H:%M:%S')

            cursor.execute(
                """
                INSERT INTO card_keys (key_code, balance, max_uses, created_by, created_at, expire_at)
                VALUES (?, ?, ?, ?, datetime('now', 'localtime'), ?)
                """,
                (key_code, balance, max_uses, created_by, expire_at),
            )
            conn.commit()
            return True

        except sqlite3.IntegrityError:
            logger.error(f"卡密已存在: {key_code}")
            conn.rollback()
            return False
        except Exception as e:
            logger.error(f"创建卡密失败: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()

    def use_card_key(self, key_code: str, user_id: int) -> Optional[int]:
        """使用卡密，返回获得的积分数量"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # 查询卡密
            cursor.execute(
                "SELECT * FROM card_keys WHERE key_code = ?",
                (key_code,),
            )
            card = cursor.fetchone()

            if not card:
                return None

            # 检查是否过期
            if card["expire_at"] and datetime.now() > datetime.fromisoformat(card["expire_at"]):
                return -2

            # 检查使用次数
            if card["current_uses"] >= card["max_uses"]:
                return -1

            # 检查用户是否已使用过此卡密
            cursor.execute(
                "SELECT COUNT(*) as count FROM card_key_usage WHERE key_code = ? AND user_id = ?",
                (key_code, user_id),
            )
            count = cursor.fetchone()
            if count['count'] > 0:
                return -3

            # 更新使用次数
            cursor.execute(
                "UPDATE card_keys SET current_uses = current_uses + 1 WHERE key_code = ?",
                (key_code,),
            )

            # 记录使用记录
            cursor.execute(
                "INSERT INTO card_key_usage (key_code, user_id, used_at) VALUES (?, ?, datetime('now', 'localtime'))",
                (key_code, user_id),
            )

            # 增加用户积分
            cursor.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (card["balance"], user_id),
            )

            conn.commit()
            return card["balance"]

        except Exception as e:
            logger.error(f"使用卡密失败: {e}")
            conn.rollback()
            return None
        finally:
            cursor.close()
            conn.close()

    def get_card_key_info(self, key_code: str) -> Optional[Dict]:
        """获取卡密信息"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM card_keys WHERE key_code = ?", (key_code,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            cursor.close()
            conn.close()

    def get_all_card_keys(self, created_by: Optional[int] = None) -> List[Dict]:
        """获取所有卡密（可按创建者筛选）"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            if created_by:
                cursor.execute(
                    "SELECT * FROM card_keys WHERE created_by = ? ORDER BY created_at DESC",
                    (created_by,),
                )
            else:
                cursor.execute("SELECT * FROM card_keys ORDER BY created_at DESC")

            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()

    def get_all_user_ids(self) -> List[int]:
        """获取所有用户ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT user_id FROM users")
            rows = cursor.fetchall()
            return [row[0] for row in rows]
        finally:
            cursor.close()
            conn.close()


# 与 database_mysql.py 保持一致的别名
Database = SQLiteDatabase

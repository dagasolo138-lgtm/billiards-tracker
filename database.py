"""数据库初始化与基础数据访问。

当前版本目标：
1. 初始化 SQLite 数据库。
2. 创建台球练球记录所需的 4 张核心表。
3. 写入默认档位与预设训练项目。
4. 提供后续 Flask 路由会用到的基础数据库函数。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

# 项目根目录下的数据库文件。
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "billiards.db"

# 预设训练项目。
# 说明：
# - 1、2、3、4 档按需求写入默认数据。
# - 5~8 档暂不强制预设，保留给后续扩展或用户自定义。
PRESET_DRILLS = {
    1: [
        {
            "name": "三分点定杆",
            "default_target_count": 100,
            "default_set_size": 15,
        }
    ],
    2: [
        {
            "name": "五分点定杆",
            "default_target_count": 100,
            "default_set_size": 15,
        },
        {
            "name": "五分点高杆",
            "default_target_count": 50,
            "default_set_size": 15,
        },
        {
            "name": "五分点低杆",
            "default_target_count": 50,
            "default_set_size": 15,
        },
    ],
    3: [
        {
            "name": "五分点分离角训练",
            "default_target_count": 60,
            "default_set_size": 15,
        },
        {
            "name": "基础走位练习",
            "default_target_count": 60,
            "default_set_size": 15,
        },
    ],
    4: [
        {
            "name": "进阶分离角训练",
            "default_target_count": 80,
            "default_set_size": 15,
        },
        {
            "name": "连续走位练习",
            "default_target_count": 80,
            "default_set_size": 15,
        },
    ],
}


def get_connection() -> sqlite3.Connection:
    """创建数据库连接，并启用字典式行访问。"""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def init_db() -> None:
    """初始化数据库结构并写入预设数据。"""
    with get_connection() as connection:
        cursor = connection.cursor()

        # 单用户设置表。
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                current_level INTEGER NOT NULL CHECK (current_level BETWEEN 1 AND 8),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # 练习主记录表。
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                practice_date TEXT NOT NULL,
                total_duration_minutes INTEGER NOT NULL DEFAULT 0 CHECK (total_duration_minutes >= 0),
                state_rating INTEGER NOT NULL CHECK (state_rating BETWEEN 1 AND 5),
                note TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # 训练项目定义表。
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS drills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                default_target_count INTEGER NOT NULL CHECK (default_target_count > 0),
                default_set_size INTEGER NOT NULL DEFAULT 15 CHECK (default_set_size > 0),
                level INTEGER NOT NULL CHECK (level BETWEEN 1 AND 8),
                is_custom INTEGER NOT NULL DEFAULT 0 CHECK (is_custom IN (0, 1)),
                is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, level)
            );
            """
        )

        # 每次训练中的项目记录表。
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS drill_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                drill_id INTEGER NOT NULL,
                set_count INTEGER NOT NULL DEFAULT 1 CHECK (set_count > 0),
                success_rate REAL NOT NULL DEFAULT 0 CHECK (success_rate BETWEEN 0 AND 100),
                subjective_difficulty INTEGER NOT NULL CHECK (subjective_difficulty BETWEEN 1 AND 5),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (drill_id) REFERENCES drills(id) ON DELETE CASCADE
            );
            """
        )

        # 单用户默认设置：初始档位为 1。
        cursor.execute(
            """
            INSERT OR IGNORE INTO users_settings (id, current_level)
            VALUES (1, 1);
            """
        )

        # 写入默认训练项目。
        for level, drills in PRESET_DRILLS.items():
            for drill in drills:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO drills (
                        name,
                        default_target_count,
                        default_set_size,
                        level,
                        is_custom,
                        is_active
                    )
                    VALUES (?, ?, ?, ?, 0, 1);
                    """,
                    (
                        drill["name"],
                        drill["default_target_count"],
                        drill["default_set_size"],
                        level,
                    ),
                )

        connection.commit()


def get_user_settings() -> Optional[sqlite3.Row]:
    """读取单用户设置。"""
    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM users_settings WHERE id = 1;"
        ).fetchone()


def update_user_level(level: int) -> None:
    """更新当前档位。"""
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE users_settings
            SET current_level = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = 1;
            """,
            (level,),
        )
        connection.commit()


def get_drills_by_level(level: int):
    """按档位读取启用中的训练项目。"""
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT *
            FROM drills
            WHERE level = ? AND is_active = 1
            ORDER BY is_custom ASC, id ASC;
            """,
            (level,),
        ).fetchall()


def create_custom_drill(
    name: str,
    default_target_count: int,
    level: int,
    default_set_size: int = 15,
) -> None:
    """创建自定义训练项目。"""
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO drills (
                name,
                default_target_count,
                default_set_size,
                level,
                is_custom,
                is_active
            )
            VALUES (?, ?, ?, ?, 1, 1);
            """,
            (name, default_target_count, default_set_size, level),
        )
        connection.commit()


def create_session(
    practice_date: str,
    total_duration_minutes: int,
    state_rating: int,
    note: str,
) -> int:
    """创建一条练习主记录，并返回 session_id。"""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO sessions (
                practice_date,
                total_duration_minutes,
                state_rating,
                note
            )
            VALUES (?, ?, ?, ?);
            """,
            (practice_date, total_duration_minutes, state_rating, note),
        )
        connection.commit()
        return cursor.lastrowid


def get_recent_sessions(limit: int = 10):
    """读取最近练习记录。"""
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT *
            FROM sessions
            ORDER BY practice_date DESC, id DESC
            LIMIT ?;
            """,
            (limit,),
        ).fetchall()


def get_session_by_id(session_id: int) -> Optional[sqlite3.Row]:
    """按 id 读取单条练习主记录。"""
    with get_connection() as connection:
        return connection.execute(
            "SELECT * FROM sessions WHERE id = ?;",
            (session_id,),
        ).fetchone()


def create_drill_log(
    session_id: int,
    drill_id: int,
    set_count: int,
    success_rate: float,
    subjective_difficulty: int,
) -> int:
    """创建单条训练项目记录，并返回 drill_log_id。"""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO drill_logs (
                session_id,
                drill_id,
                set_count,
                success_rate,
                subjective_difficulty
            )
            VALUES (?, ?, ?, ?, ?);
            """,
            (
                session_id,
                drill_id,
                set_count,
                success_rate,
                subjective_difficulty,
            ),
        )
        connection.commit()
        return cursor.lastrowid


def get_drill_logs_by_session(session_id: int):
    """读取某次练习下的全部项目记录。"""
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT
                drill_logs.*,
                drills.name AS drill_name,
                drills.default_target_count,
                drills.default_set_size
            FROM drill_logs
            INNER JOIN drills ON drill_logs.drill_id = drills.id
            WHERE drill_logs.session_id = ?
            ORDER BY drill_logs.id ASC;
            """,
            (session_id,),
        ).fetchall()


def delete_drill_logs_by_session(session_id: int) -> None:
    """删除某次练习下已有的项目记录。"""
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM drill_logs WHERE session_id = ?;",
            (session_id,),
        )
        connection.commit()


if __name__ == "__main__":
    init_db()
    print(f"数据库已初始化：{DB_PATH}")

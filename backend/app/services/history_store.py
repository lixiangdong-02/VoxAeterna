"""历史记录持久化 —— 本地 SQLite 存储，按 user_id 隔离"""

import sqlite3
import os
from pathlib import Path
from typing import Optional

# 项目根目录 → F:\etc\VoiceStudio
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = _PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "history.db"


def _ensure_db():
    """确保 data/ 目录和数据库文件存在"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            text TEXT,
            audio_path TEXT,
            duration_seconds REAL,
            sample_rate INTEGER,
            state TEXT DEFAULT 'completed',
            error_message TEXT,
            prompt_text TEXT,
            speed_factor REAL,
            ref_audio_path TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id, created_at DESC)
    """)
    conn.commit()
    conn.close()


def save_task(task, user_id: int):
    """保存一条完成/失败/取消的任务"""
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """INSERT OR REPLACE INTO tasks
           (task_id, user_id, text, audio_path, duration_seconds, sample_rate,
            state, error_message, prompt_text, speed_factor, ref_audio_path)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            task.task_id,
            user_id,
            getattr(task, 'text', ''),
            getattr(task, 'audio_path', None),
            getattr(task, 'duration_seconds', None),
            getattr(task, 'sample_rate', None),
            getattr(task, 'state', 'completed').value if hasattr(getattr(task, 'state', None), 'value') else str(getattr(task, 'state', 'completed')),
            getattr(task, 'error_message', None),
            getattr(task, 'prompt_text', ''),
            getattr(task, 'speed_factor', 1.0),
            getattr(task, 'ref_audio_path', ''),
        ),
    )
    conn.commit()
    conn.close()


def list_by_user(user_id: int, limit: int = 50) -> list[dict]:
    """按 user_id 查询历史，最近优先"""
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_task(task_id: str, user_id: int) -> bool:
    """删除一条记录（仅当 user_id 匹配）"""
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.execute(
        "DELETE FROM tasks WHERE task_id = ? AND user_id = ?",
        (task_id, user_id),
    )
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_task(task_id: str) -> Optional[dict]:
    """按 task_id 查询单条（不限制 user_id）"""
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

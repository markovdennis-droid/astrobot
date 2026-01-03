import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional

DB_PATH = Path("/var/data/astrobot.db")


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                chat_id TEXT PRIMARY KEY,
                lang TEXT,
                sign TEXT,
                reminder_time TEXT,
                tarot_ts INTEGER
            )
            """
        )
        conn.commit()


def get_user(chat_id: int) -> Dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT lang, sign, reminder_time, tarot_ts FROM users WHERE chat_id = ?",
            (str(chat_id),),
        ).fetchone()

    if not row:
        return {}

    return {
        "lang": row[0],
        "sign": row[1],
        "reminder_time": row[2],
        "tarot_ts": row[3],
    }


def update_user(chat_id: int, **kwargs) -> Dict[str, Any]:
    existing = get_user(chat_id)
    data = {**existing, **kwargs}

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO users (chat_id, lang, sign, reminder_time, tarot_ts)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                lang = excluded.lang,
                sign = excluded.sign,
                reminder_time = excluded.reminder_time,
                tarot_ts = excluded.tarot_ts
            """,
            (
                str(chat_id),
                data.get("lang"),
                data.get("sign"),
                data.get("reminder_time"),
                data.get("tarot_ts"),
            ),
        )
        conn.commit()

    return data


def all_users():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT chat_id, lang, sign, reminder_time, tarot_ts FROM users"
        ).fetchall()

    result = {}
    for r in rows:
        result[r[0]] = {
            "lang": r[1],
            "sign": r[2],
            "reminder_time": r[3],
            "tarot_ts": r[4],
        }
    return result

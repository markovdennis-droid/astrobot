import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.getenv("ASTROBOT_DB", os.path.join(os.path.dirname(__file__), "astrobot.db"))

@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.commit()
        conn.close()

def init_db():
    with _db() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id      INTEGER PRIMARY KEY,
            sign         TEXT,
            daily_on     INTEGER DEFAULT 0,
            daily_time   TEXT    DEFAULT '09:00',
            tz           TEXT    DEFAULT 'Europe/Madrid',
            created_at   TEXT,
            updated_at   TEXT
        )""")
        # добивка недостающих колонок (гладкие миграции)
        cols = {r["name"] for r in db.execute("PRAGMA table_info(users)")}
        if "daily_on"   not in cols: db.execute("ALTER TABLE users ADD COLUMN daily_on INTEGER DEFAULT 0")
        if "daily_time" not in cols: db.execute("ALTER TABLE users ADD COLUMN daily_time TEXT DEFAULT '09:00'")
        if "tz"         not in cols: db.execute("ALTER TABLE users ADD COLUMN tz TEXT DEFAULT 'Europe/Madrid'")
        if "created_at" not in cols: db.execute("ALTER TABLE users ADD COLUMN created_at TEXT")
        if "updated_at" not in cols: db.execute("ALTER TABLE users ADD COLUMN updated_at TEXT")

def _now_iso():
    return datetime.utcnow().isoformat(timespec="seconds")

def upsert_user(user_id: int):
    with _db() as db:
        db.execute("""
        INSERT INTO users (user_id, created_at, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET updated_at=excluded.updated_at
        """, (user_id, _now_iso(), _now_iso()))

def set_sign(user_id: int, sign: str):
    upsert_user(user_id)
    with _db() as db:
        db.execute("UPDATE users SET sign=?, updated_at=? WHERE user_id=?", (sign, _now_iso(), user_id))

def get_sign(user_id: int):
    with _db() as db:
        row = db.execute("SELECT sign FROM users WHERE user_id=?", (user_id,)).fetchone()
        return row["sign"] if row else None

def set_daily(user_id: int, enabled: bool, time_hhmm: str = None):
    upsert_user(user_id)
    with _db() as db:
        if time_hhmm is not None:
            db.execute("UPDATE users SET daily_on=?, daily_time=?, updated_at=? WHERE user_id=?",
                       (1 if enabled else 0, time_hhmm, _now_iso(), user_id))
        else:
            db.execute("UPDATE users SET daily_on=?, updated_at=? WHERE user_id=?",
                       (1 if enabled else 0, _now_iso(), user_id))

def get_daily_settings(user_id: int):
    with _db() as db:
        row = db.execute("SELECT daily_on, daily_time, tz FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            return {"daily_on": 0, "daily_time": "09:00", "tz": "Europe/Madrid"}
        return {"daily_on": int(row["daily_on"] or 0), "daily_time": row["daily_time"], "tz": row["tz"]}

def set_tz(user_id: int, tz: str):
    upsert_user(user_id)
    with _db() as db:
        db.execute("UPDATE users SET tz=?, updated_at=? WHERE user_id=?", (tz, _now_iso(), user_id))

def get_user_row(user_id: int):
    with _db() as db:
        return db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()

def list_user_ids(subscribed_only: bool = False):
    """
    Возвращает список user_id.
    Если subscribed_only=True — только с включённой ежедневной рассылкой.
    """
    with _db() as db:
        if subscribed_only:
            rows = db.execute("SELECT user_id FROM users WHERE daily_on=1").fetchall()
        else:
            rows = db.execute("SELECT user_id FROM users").fetchall()
        return [r["user_id"] for r in rows]

def list_daily_users():
    """Удобно для рассылки: только подписанные, с временем и TZ."""
    with _db() as db:
        rows = db.execute("SELECT user_id, daily_time, tz FROM users WHERE daily_on=1").fetchall()
        return [{"user_id": r["user_id"], "daily_time": r["daily_time"], "tz": r["tz"]} for r in rows]
# === Совместимость со старым bot.py ===

def get_daily(user_id: int):
    """
    Старое имя, которое ждёт bot.py.
    Возвращает словарь: {'daily_on': int, 'daily_time': 'HH:MM', 'tz': '...'}
    """
    return get_daily_settings(user_id)

def get_user(user_id: int):
    """
    Старое имя, которое ждёт bot.py.
    Возвращает dict со всеми полями строки пользователя (или None).
    """
    row = get_user_row(user_id)
    return dict(row) if row else None


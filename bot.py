# ============================================
# EVENT LOOP FIX (Python 3.11 + aiogram 2.x)
# ============================================

import asyncio
import os
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

from generator import (
    generate,
    draw_tarot_for_user,
    ZODIAC_SIGNS,
    SIGN_NAMES,
    TZ,
)

# =======================
# CONFIG
# =======================

BASE_DIR = Path(__file__).parent

DATA_DIR = Path(os.getenv("DATA_DIR", "/var/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "astrobot.db"
TAROT_IMAGES_DIR = BASE_DIR / "tarot_images"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("astrobot")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not found")

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

ADMIN_IDS = {8023489016}

# =======================
# DATABASE
# =======================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                chat_id INTEGER PRIMARY KEY,
                lang TEXT DEFAULT 'ru',
                sign TEXT,
                reminder_time TEXT,
                tarot_last_date TEXT
            )
        """)
        conn.commit()


init_db()


def get_user(chat_id: int) -> Dict[str, Any]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE chat_id = ?",
            (chat_id,)
        ).fetchone()
        return dict(row) if row else {}


def update_user(chat_id: int, **kwargs) -> Dict[str, Any]:
    user = get_user(chat_id)
    data = {**user, **kwargs}

    with get_db() as conn:
        conn.execute("""
            INSERT INTO users (chat_id, lang, sign, reminder_time, tarot_last_date)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                lang = excluded.lang,
                sign = excluded.sign,
                reminder_time = excluded.reminder_time,
                tarot_last_date = excluded.tarot_last_date
        """, (
            chat_id,
            data.get("lang", "ru"),
            data.get("sign"),
            data.get("reminder_time"),
            data.get("tarot_last_date"),
        ))
        conn.commit()

    return data


def get_user_lang(chat_id: int) -> str:
    return get_user(chat_id).get("lang", "ru")


# =======================
# STATS (ADMIN)
# =======================

def get_stats():
    with get_db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]

        with_sign = conn.execute(
            "SELECT COUNT(*) FROM users WHERE sign IS NOT NULL"
        ).fetchone()[0]

        with_reminder = conn.execute(
            "SELECT COUNT(*) FROM users WHERE reminder_time IS NOT NULL"
        ).fetchone()[0]

    return total, with_sign, with_reminder


# =======================
# UI TEXTS
# =======================

UI = {
    "ru": {
        "choose_lang": "Выберите язык:",
        "btn_lang_ru": "🇷🇺 Русский",
        "btn_lang_en": "🇬🇧 English",
        "btn_lang_es": "🇪🇸 Español",
        "start_no_sign": "✨ Привет! Я астробот.\n\nВыбери свой знак зодиака:",
        "start_with_sign": "Снова привет, {name}!\n\nТвой знак: {sign}",
        "btn_tarot": "🔮 Еженедельная карта Таро",
        "btn_reminder": "⏰ Настроить напоминание",
        "btn_change_sign": "♻️ Сменить знак",
        "btn_change_lang": "🌐 Сменить язык",
        "btn_cancel": "❌ Отменить",
        "btn_back": "⬅️ Назад",
        "reminder_prompt": "Во сколько присылать ежедневный гороскоп?",
        "reminder_set": "Буду присылать каждый день в {time}.",
        "need_sign": "Сначала выбери знак зодиака.",
        "unknown": "Я тебя не понял 🙂",
    },
    "en": {
        "choose_lang": "Choose language:",
        "btn_lang_ru": "🇷🇺 Русский",
        "btn_lang_en": "🇬🇧 English",
        "btn_lang_es": "🇪🇸 Español",
        "start_no_sign": "✨ Hi! Choose your zodiac sign:",
        "start_with_sign": "Hi again, {name}! Your sign: {sign}",
        "btn_tarot": "🔮 Weekly Tarot card",
        "btn_reminder": "⏰ Set reminder",
        "btn_change_sign": "♻️ Change sign",
        "btn_change_lang": "🌐 Change language",
        "btn_cancel": "❌ Cancel",
        "btn_back": "⬅️ Back",
        "reminder_prompt": "What time should I send your horoscope?",
        "reminder_set": "I will send it daily at {time}.",
        "need_sign": "Choose your sign first.",
        "unknown": "I didn’t understand 🙂",
    },
    "es": {
        "choose_lang": "Elige idioma:",
        "btn_lang_ru": "🇷🇺 Русский",
        "btn_lang_en": "🇬🇧 English",
        "btn_lang_es": "🇪🇸 Español",
        "start_no_sign": "✨ ¡Hola! Elige tu signo:",
        "start_with_sign": "Hola! Tu signo: {sign}",
        "btn_tarot": "🔮 Carta de Tarot semanal",
        "btn_reminder": "⏰ Recordatorio",
        "btn_change_sign": "♻️ Cambiar signo",
        "btn_change_lang": "🌐 Cambiar idioma",
        "btn_cancel": "❌ Cancelar",
        "btn_back": "⬅️ Atrás",
        "reminder_prompt": "¿A qué hora enviar el horóscopo?",
        "reminder_set": "Enviaré cada día a las {time}.",
        "need_sign": "Elige signo primero.",
        "unknown": "No entendí 🙂",
    },
}

SIGN_EMOJIS = {
    "Овен": "🐏",
    "Телец": "🐂",
    "Близнецы": "👥",
    "Рак": "🦀",
    "Лев": "🦁",
    "Дева": "👩‍🦰",
    "Весы": "⚖️",
    "Скорпион": "🦂",
    "Стрелец": "🏹",
    "Козерог": "🐐",
    "Водолей": "🌊",
    "Рыбы": "🐟",
}

# =======================
# /STATS COMMAND
# =======================

@dp.message_handler(commands=["stats"])
async def cmd_stats(message: types.Message):
    if message.chat.id not in ADMIN_IDS:
        await message.answer("⛔️ Недостаточно прав")
        return

    total, with_sign, with_reminder = get_stats()

    await message.answer(
        "📊 <b>AstroBot — статистика</b>\n\n"
        f"👥 Всего пользователей: <b>{total}</b>\n"
        f"♈️ С выбранным знаком: <b>{with_sign}</b>\n"
        f"⏰ С напоминаниями: <b>{with_reminder}</b>\n"
    )

# =======================
# (ДАЛЬШЕ КОД БЕЗ ИЗМЕНЕНИЙ)
# =======================
# ⬇⬇⬇
# весь остальной код у тебя уже есть и он рабочий
# (handlers, tarot, reminders, scheduler, startup)

import os
import json
import logging
import asyncio
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
# CONFIG & PATHS
# =======================

BASE_DIR = Path(__file__).parent

# ⬇️ ВАЖНО: SQLite на Render Disk
DATA_DIR = Path(os.getenv("DATA_DIR", "/var/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "astrobot.db"

TAROT_IMAGES_DIR = BASE_DIR / "tarot_images"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("astrobot")

# =======================
# TELEGRAM TOKEN
# =======================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not found")

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

# =======================
# ADMINS
# =======================

ADMIN_IDS = {
    8023489016,
}

# =======================
# SQLITE INIT
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

# =======================
# USER STORAGE (SQLite)
# =======================

def get_user(chat_id: int) -> Dict[str, Any]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE chat_id = ?",
            (chat_id,)
        ).fetchone()
        return dict(row) if row else {}


def update_user(chat_id: int, **kwargs) -> Dict[str, Any]:
    user = get_user(chat_id)
    fields = {**user, **kwargs}

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
            fields.get("lang", "ru"),
            fields.get("sign"),
            fields.get("reminder_time"),
            fields.get("tarot_last_date"),
        ))
        conn.commit()

    return fields


def get_user_lang(chat_id: int) -> str:
    return get_user(chat_id).get("lang", "ru")

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
        "start_with_sign": "Снова привет, {name}!\n\nТвой текущий знак: {sign}.",
        "btn_tarot": "🔮 Еженедельная карта Таро",
        "btn_reminder": "⏰ Настроить напоминание",
        "btn_change_sign": "♻️ Сменить знак",
        "btn_cancel_reminders": "❌ Отменить напоминания",
        "btn_back": "⬅️ Назад",
        "reminder_prompt": "Во сколько тебе удобно получать ежедневный гороскоп?",
        "reminder_set": "Я буду присылать гороскоп каждый день в {time}.",
        "reminder_cleared": "Напоминания отключены.",
        "need_sign": "Сначала выбери знак зодиака:",
        "unknown": "Я тебя не понял 🙂",
        "btn_change_lang": "🌐 Сменить язык",
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
        "btn_cancel_reminders": "❌ Cancel reminders",
        "btn_back": "⬅️ Back",
        "reminder_prompt": "What time should I send your horoscope?",
        "reminder_set": "I will send it daily at {time}.",
        "reminder_cleared": "Reminders disabled.",
        "need_sign": "Choose your sign first:",
        "unknown": "I didn’t understand 🙂",
        "btn_change_lang": "🌐 Change language",
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
        "btn_cancel_reminders": "❌ Cancelar",
        "btn_back": "⬅️ Atrás",
        "reminder_prompt": "¿A qué hora enviar el horóscopo?",
        "reminder_set": "Enviaré cada día a las {time}.",
        "reminder_cleared": "Recordatorios desactivados.",
        "need_sign": "Elige signo primero:",
        "unknown": "No entendí 🙂",
        "btn_change_lang": "🌐 Cambiar idioma",
    },
}
CANCEL_BUTTONS = {
    UI["ru"]["btn_cancel_reminders"],
    UI["en"]["btn_cancel_reminders"],
    UI["es"]["btn_cancel_reminders"],
}

BACK_BUTTONS = {
    UI["ru"]["btn_back"],
    UI["en"]["btn_back"],
    UI["es"]["btn_back"],
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


def build_lang_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(
        KeyboardButton(UI["ru"]["btn_lang_ru"]),
        KeyboardButton(UI["ru"]["btn_lang_en"]),
        KeyboardButton(UI["ru"]["btn_lang_es"]),
    )
    return kb


def build_sign_keyboard(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for s in ZODIAC_SIGNS:
        local = SIGN_NAMES[lang].get(s, s)
        kb.row(KeyboardButton(f"{SIGN_EMOJIS.get(s,'⭐️')} {local}"))
    return kb


def build_main_keyboard(sign: str, lang: str):
    ui = UI[lang]
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    local = SIGN_NAMES[lang].get(sign, sign)
    kb.row(KeyboardButton(f"{SIGN_EMOJIS.get(sign)} {local} — today"))
    kb.row(KeyboardButton(ui["btn_tarot"]))
    kb.row(KeyboardButton(ui["btn_reminder"]))
    kb.row(KeyboardButton(ui["btn_change_sign"]))
    kb.row(KeyboardButton(ui["btn_change_lang"]))
    return kb


def build_time_keyboard(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for t in ["07:00", "08:00", "09:00", "10:00", "19:00", "20:00", "21:00"]:
        kb.row(KeyboardButton(t))
    kb.row(KeyboardButton(UI[lang]["btn_cancel_reminders"]))
    kb.row(KeyboardButton(UI[lang]["btn_back"]))
    return kb
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    user = get_user(message.chat.id)
    lang = user.get("lang")

    if lang not in ("ru", "en", "es"):
        await message.answer("Choose language:", reply_markup=build_lang_keyboard())
        return

    sign = user.get("sign")
    ui = UI[lang]

    if sign:
        await message.answer(
            ui["start_with_sign"].format(
                name=message.from_user.first_name,
                sign=SIGN_NAMES[lang].get(sign, sign)
            ),
            reply_markup=build_main_keyboard(sign, lang)
        )
    else:
        await message.answer(ui["start_no_sign"], reply_markup=build_sign_keyboard(lang))


@dp.message_handler(lambda m: m.text in {
    UI["ru"]["btn_lang_ru"],
    UI["ru"]["btn_lang_en"],
    UI["ru"]["btn_lang_es"],
})
async def set_language(message: types.Message):
    lang = "ru" if "Рус" in message.text else "en" if "Eng" in message.text else "es"
    user = update_user(message.chat.id, lang=lang)

    await message.answer(UI[lang]["start_no_sign"], reply_markup=build_sign_keyboard(lang))
@dp.message_handler(lambda m: m.text and m.text.startswith(tuple(SIGN_EMOJIS.values())))
async def choose_sign(message: types.Message):
    lang = get_user_lang(message.chat.id)
    label = message.text.split(" ", 1)[1]

    sign = next(
        (s for s in ZODIAC_SIGNS if SIGN_NAMES[lang].get(s) == label),
        None
    )
    if not sign:
        return

    update_user(message.chat.id, sign=sign)

    await message.answer(
        UI[lang]["start_with_sign"].format(
            name=message.from_user.first_name,
            sign=label
        ),
        reply_markup=build_main_keyboard(sign, lang)
    )


@dp.message_handler(lambda m: "—" in m.text)
async def horoscope_today(message: types.Message):
    user = get_user(message.chat.id)
    sign = user.get("sign")
    lang = user.get("lang", "ru")

    if not sign:
        await message.answer(UI[lang]["need_sign"])
        return

    text = generate(sign, lang)
    await message.answer(text, reply_markup=build_main_keyboard(sign, lang))
@dp.message_handler(lambda m: m.text in {
    UI["ru"]["btn_tarot"],
    UI["en"]["btn_tarot"],
    UI["es"]["btn_tarot"],
})
async def tarot_handler(message: types.Message):
    chat_id = message.chat.id
    user = get_user(chat_id)
    lang = user.get("lang", "ru")

    result = draw_tarot_for_user(chat_id, lang)

    text = result.get("text")
    image = result.get("image_path")

    update_user(chat_id, tarot_last_date=datetime.now(TZ).isoformat())

    if image:
        await bot.send_photo(chat_id, types.InputFile(TAROT_IMAGES_DIR / image), caption=text)
    else:
        await message.answer(text)
@dp.message_handler(lambda m: m.text in {
    UI["ru"]["btn_reminder"],
    UI["en"]["btn_reminder"],
    UI["es"]["btn_reminder"],
})
async def reminder_button(message: types.Message):
    lang = get_user_lang(message.chat.id)
    await message.answer(
        UI[lang]["reminder_prompt"],
        reply_markup=build_time_keyboard(lang)
    )


@dp.message_handler(lambda m: ":" in m.text and len(m.text) == 5)
async def reminder_time(message: types.Message):
    update_user(message.chat.id, reminder_time=message.text)
    lang = get_user_lang(message.chat.id)
    await message.answer(
        UI[lang]["reminder_set"].format(time=message.text)
    )
async def send_daily_horoscopes():
    while True:
        now = datetime.now(TZ).strftime("%H:%M")
        with get_db() as conn:
            users = conn.execute(
                "SELECT chat_id, sign, lang FROM users WHERE reminder_time = ?",
                (now,)
            ).fetchall()

        for u in users:
            try:
                text = generate(u["sign"], u["lang"])
                await bot.send_message(u["chat_id"], text)
            except Exception as e:
                logger.error(e)

        await asyncio.sleep(60)


async def on_startup(dp):
    asyncio.create_task(send_daily_horoscopes())
    logger.info("AstroBot started (SQLite + Render Disk)")


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)

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
# KEYBOARDS
# =======================

def kb_lang():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(
        KeyboardButton(UI["ru"]["btn_lang_ru"]),
        KeyboardButton(UI["ru"]["btn_lang_en"]),
        KeyboardButton(UI["ru"]["btn_lang_es"]),
    )
    return kb


def kb_signs(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for s in ZODIAC_SIGNS:
        local = SIGN_NAMES[lang].get(s, s)
        kb.row(KeyboardButton(f"{SIGN_EMOJIS.get(s,'⭐️')} {local}"))
    return kb


def kb_main(sign: str, lang: str):
    ui = UI[lang]
    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    local = SIGN_NAMES[lang].get(sign, sign)
    if lang == "ru":
        tail = "гороскоп на сегодня"
    elif lang == "es":
        tail = "horóscopo para hoy"
    else:
        tail = "horoscope for today"

    kb.row(KeyboardButton(f"{SIGN_EMOJIS.get(sign)} {local} — {tail}"))
    kb.row(KeyboardButton(ui["btn_tarot"]))
    kb.row(KeyboardButton(ui["btn_reminder"]))
    kb.row(KeyboardButton(ui["btn_change_sign"]))
    kb.row(KeyboardButton(ui["btn_change_lang"]))
    return kb


def kb_time(lang: str):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for t in ["07:00", "08:00", "09:00", "10:00", "19:00", "20:00", "21:00"]:
        kb.row(KeyboardButton(t))
    kb.row(KeyboardButton(UI[lang]["btn_cancel"]))
    kb.row(KeyboardButton(UI[lang]["btn_back"]))
    return kb
# =======================
# HELPERS (TEXT PARSE)
# =======================

ALL_LANG_BUTTONS = {
    UI["ru"]["btn_lang_ru"], UI["ru"]["btn_lang_en"], UI["ru"]["btn_lang_es"],
    UI["en"]["btn_lang_ru"], UI["en"]["btn_lang_en"], UI["en"]["btn_lang_es"],
    UI["es"]["btn_lang_ru"], UI["es"]["btn_lang_en"], UI["es"]["btn_lang_es"],
}

def parse_lang_from_button(text: str) -> str:
    if "Рус" in text:
        return "ru"
    if "Eng" in text:
        return "en"
    return "es"


def parse_sign_from_button(text: str, lang: str) -> str | None:
    # expected: "🐏 Aries" or "🐏 Овен" etc
    parts = text.split(" ", 1)
    if len(parts) < 2:
        return None
    label = parts[1].strip()

    for s in ZODIAC_SIGNS:
        if SIGN_NAMES[lang].get(s, s) == label:
            return s
    return None


# =======================
# START / LANGUAGE
# =======================

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    chat_id = message.chat.id
    user = get_user(chat_id)
    lang = user.get("lang")

    if lang not in ("ru", "en", "es"):
        await message.answer(UI["ru"]["choose_lang"], reply_markup=kb_lang())
        return

    ui = UI[lang]
    sign = user.get("sign")

    if sign:
        await message.answer(
            ui["start_with_sign"].format(
                name=message.from_user.first_name,
                sign=SIGN_NAMES[lang].get(sign, sign)
            ),
            reply_markup=kb_main(sign, lang)
        )
    else:
        await message.answer(ui["start_no_sign"], reply_markup=kb_signs(lang))


@dp.message_handler(lambda m: m.text in ALL_LANG_BUTTONS)
async def set_language(message: types.Message):
    chat_id = message.chat.id
    lang = parse_lang_from_button(message.text)

    user = update_user(chat_id, lang=lang)
    ui = UI[lang]
    sign = user.get("sign")

    if sign:
        await message.answer(
            ui["start_with_sign"].format(
                name=message.from_user.first_name,
                sign=SIGN_NAMES[lang].get(sign, sign),
            ),
            reply_markup=kb_main(sign, lang),
        )
    else:
        await message.answer(ui["start_no_sign"], reply_markup=kb_signs(lang))


@dp.message_handler(lambda m: m.text in {
    UI["ru"]["btn_change_lang"],
    UI["en"]["btn_change_lang"],
    UI["es"]["btn_change_lang"],
})
async def change_language(message: types.Message):
    await message.answer(UI["ru"]["choose_lang"], reply_markup=kb_lang())


# =======================
# SIGN CHOICE
# =======================

@dp.message_handler(
    lambda m: m.text
    and m.text.startswith(tuple(SIGN_EMOJIS.values()))
    and "—" not in m.text
)
async def choose_sign(message: types.Message):
    chat_id = message.chat.id
    lang = get_user_lang(chat_id)

    sign = parse_sign_from_button(message.text, lang)
    if not sign:
        return

    update_user(chat_id, sign=sign)

    await message.answer(
        UI[lang]["start_with_sign"].format(
            name=message.from_user.first_name,
            sign=SIGN_NAMES[lang].get(sign, sign),
        ),
        reply_markup=kb_main(sign, lang),
    )


@dp.message_handler(lambda m: m.text in {
    UI["ru"]["btn_change_sign"],
    UI["en"]["btn_change_sign"],
    UI["es"]["btn_change_sign"],
})
async def change_sign(message: types.Message):
    chat_id = message.chat.id
    lang = get_user_lang(chat_id)
    await message.answer(UI[lang]["start_no_sign"], reply_markup=kb_signs(lang))


# =======================
# HOROSCOPE TODAY (button with "—")
# =======================

@dp.message_handler(
    lambda m: m.text
    and m.text.startswith(tuple(SIGN_EMOJIS.values()))
    and "—" in m.text
)
async def horoscope_today(message: types.Message):
    chat_id = message.chat.id
    user = get_user(chat_id)
    lang = user.get("lang", "ru")
    sign = user.get("sign")

    if not sign:
        await message.answer(UI[lang]["need_sign"], reply_markup=kb_signs(lang))
        return

    try:
        text = generate(sign, lang)
    except Exception as e:
        logger.exception(f"generate() failed chat_id={chat_id}, sign={sign}, lang={lang}: {e}")
        text = UI[lang]["unknown"]

    await message.answer(text, reply_markup=kb_main(sign, lang))


# =======================
# TAROT
# =======================

@dp.message_handler(lambda m: m.text in {
    UI["ru"]["btn_tarot"],
    UI["en"]["btn_tarot"],
    UI["es"]["btn_tarot"],
})
async def tarot_handler(message: types.Message):
    chat_id = message.chat.id
    user = get_user(chat_id)
    lang = user.get("lang", "ru")
    sign = user.get("sign") or ZODIAC_SIGNS[0]

    try:
        result = draw_tarot_for_user(chat_id, lang)
    except Exception as e:
        logger.exception(f"draw_tarot_for_user failed chat_id={chat_id}: {e}")
        await message.answer(UI[lang]["unknown"], reply_markup=kb_main(sign, lang))
        return

    text = ""
    image_name = None

    # allow dict or string
    if isinstance(result, dict):
        text = result.get("text", "") or ""
        image_name = (
            result.get("image_path")
            or result.get("image")
            or result.get("image_file")
            or result.get("filename")
        )
    else:
        text = str(result)

    update_user(chat_id, tarot_last_date=datetime.now(TZ).isoformat())

    if image_name:
        img_path = TAROT_IMAGES_DIR / image_name
        if img_path.exists():
            try:
                await bot.send_photo(
                    chat_id,
                    photo=types.InputFile(img_path),
                    caption=text or None,
                    reply_markup=kb_main(sign, lang),
                )
                return
            except Exception as e:
                logger.exception(f"send_photo tarot failed chat_id={chat_id}: {e}")

    await message.answer(text or UI[lang]["unknown"], reply_markup=kb_main(sign, lang))


# =======================
# REMINDERS UI
# =======================

@dp.message_handler(lambda m: m.text in {
    UI["ru"]["btn_reminder"],
    UI["en"]["btn_reminder"],
    UI["es"]["btn_reminder"],
})
async def reminder_button(message: types.Message):
    chat_id = message.chat.id
    lang = get_user_lang(chat_id)
    await message.answer(UI[lang]["reminder_prompt"], reply_markup=kb_time(lang))


@dp.message_handler(lambda m: m.text in {
    UI["ru"]["btn_cancel"],
    UI["en"]["btn_cancel"],
    UI["es"]["btn_cancel"],
})
async def reminder_cancel(message: types.Message):
    chat_id = message.chat.id
    lang = get_user_lang(chat_id)
    user = update_user(chat_id, reminder_time=None)
    sign = user.get("sign")

    if sign:
        await message.answer(UI[lang]["unknown"], reply_markup=kb_main(sign, lang))
    else:
        await message.answer(UI[lang]["start_no_sign"], reply_markup=kb_signs(lang))


@dp.message_handler(lambda m: m.text in {
    UI["ru"]["btn_back"],
    UI["en"]["btn_back"],
    UI["es"]["btn_back"],
})
async def back_to_menu(message: types.Message):
    chat_id = message.chat.id
    user = get_user(chat_id)
    lang = user.get("lang", "ru")
    sign = user.get("sign")

    if sign:
        await message.answer("OK", reply_markup=kb_main(sign, lang))
    else:
        await message.answer(UI[lang]["start_no_sign"], reply_markup=kb_signs(lang))


@dp.message_handler(
    lambda m: m.text
    and ":" in m.text
    and len(m.text.strip()) == 5
    and m.text.replace(":", "").isdigit()
)
async def reminder_time(message: types.Message):
    chat_id = message.chat.id
    lang = get_user_lang(chat_id)
    user = get_user(chat_id)
    sign = user.get("sign")

    time_str = message.text.strip()

    # validate HH:MM range
    try:
        hh, mm = time_str.split(":")
        hh_i = int(hh)
        mm_i = int(mm)
        if not (0 <= hh_i <= 23 and 0 <= mm_i <= 59):
            raise ValueError("range")
    except Exception:
        await message.answer(UI[lang]["unknown"], reply_markup=kb_time(lang))
        return

    update_user(chat_id, reminder_time=f"{hh_i:02d}:{mm_i:02d}")

    if sign:
        await message.answer(
            UI[lang]["reminder_set"].format(time=f"{hh_i:02d}:{mm_i:02d}"),
            reply_markup=kb_main(sign, lang),
        )
    else:
        await message.answer(
            UI[lang]["reminder_set"].format(time=f"{hh_i:02d}:{mm_i:02d}"),
            reply_markup=kb_signs(lang),
        )


# =======================
# FALLBACK
# =======================

@dp.message_handler()
async def fallback(message: types.Message):
    chat_id = message.chat.id
    user = get_user(chat_id)
    lang = user.get("lang", "ru")
    sign = user.get("sign")

    if sign:
        await message.answer(UI[lang]["unknown"], reply_markup=kb_main(sign, lang))
    else:
        await message.answer(UI[lang]["unknown"], reply_markup=kb_signs(lang))
# =======================
# DAILY SCHEDULER
# =======================

async def send_daily_horoscopes():
    """
    Каждую минуту проверяет пользователей с reminder_time == текущему HH:MM
    и отправляет гороскоп.
    """
    logger.info("Daily scheduler started")
    while True:
        try:
            now_hhmm = datetime.now(TZ).strftime("%H:%M")

            with get_db() as conn:
                rows = conn.execute(
                    """
                    SELECT chat_id, sign, lang
                    FROM users
                    WHERE reminder_time = ?
                      AND sign IS NOT NULL
                    """,
                    (now_hhmm,),
                ).fetchall()

            for r in rows:
                try:
                    text = generate(r["sign"], r["lang"])
                    await bot.send_message(r["chat_id"], text)
                except Exception as e:
                    logger.exception(
                        f"Failed to send daily horoscope chat_id={r['chat_id']}: {e}"
                    )

        except Exception as loop_err:
            logger.exception(f"Scheduler loop error: {loop_err}")

        await asyncio.sleep(60)


# =======================
# STARTUP / SHUTDOWN
# =======================

async def on_startup(dp: Dispatcher):
    logger.info("AstroBot starting (SQLite + Render Disk)")
    asyncio.create_task(send_daily_horoscopes())


async def on_shutdown(dp: Dispatcher):
    logger.info("AstroBot shutdown")


# =======================
# MAIN
# =======================

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup,
        loop=loop
    )


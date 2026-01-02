import os
import sys
import json
import logging
import asyncio
import signal
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import aiohttp
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

API_BASE_URL = "https://astrobot-api-jrrr.onrender.com"

BASE_DIR = Path(__file__).parent
USERS_FILE = BASE_DIR / "users_state.json"
TAROT_IMAGES_DIR = BASE_DIR / "tarot_images"

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN / TELEGRAM_BOT_TOKEN not found")

ADMIN_IDS = {8023489016}

# =======================
# LOGGING
# =======================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("astrobot")

# =======================
# BOT / DISPATCHER
# =======================

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

# =======================
# POLLING SAFETY
# =======================

POLLING_STARTED = False
SHUTTING_DOWN = False


def shutdown_handler(signum, frame):
    global SHUTTING_DOWN
    if SHUTTING_DOWN:
        return
    SHUTTING_DOWN = True
    logger.warning(f"Received signal {signum}. Shutting down gracefully...")
    try:
        loop = asyncio.get_event_loop()
        loop.stop()
    except Exception:
        pass
    sys.exit(0)


signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)

# =======================
# UI TEXT
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
        "btn_change_lang": "🌐 Сменить язык",
        "reminder_prompt": "Во сколько присылать гороскоп? (ЧЧ:ММ)",
        "reminder_set": "Готово! Каждый день в {time}.",
        "reminder_cleared": "Напоминания отключены.",
        "unknown": "Я тебя не понял 🙂",
    },
    "en": {
        "choose_lang": "Choose language:",
        "btn_lang_ru": "🇷🇺 Русский",
        "btn_lang_en": "🇬🇧 English",
        "btn_lang_es": "🇪🇸 Español",
        "start_no_sign": "✨ Hi! Choose your zodiac sign:",
        "start_with_sign": "Hi {name}! Your sign: {sign}.",
        "btn_tarot": "🔮 Weekly Tarot card",
        "btn_reminder": "⏰ Set reminder",
        "btn_change_sign": "♻️ Change sign",
        "btn_cancel_reminders": "❌ Cancel reminders",
        "btn_back": "⬅️ Back",
        "btn_change_lang": "🌐 Change language",
        "reminder_prompt": "What time? (HH:MM)",
        "reminder_set": "Done! Every day at {time}.",
        "reminder_cleared": "Reminders disabled.",
        "unknown": "I didn't understand 🙂",
    },
    "es": {
        "choose_lang": "Elige idioma:",
        "btn_lang_ru": "🇷🇺 Русский",
        "btn_lang_en": "🇬🇧 English",
        "btn_lang_es": "🇪🇸 Español",
        "start_no_sign": "✨ ¡Hola! Elige tu signo:",
        "start_with_sign": "Hola {name}, tu signo: {sign}.",
        "btn_tarot": "🔮 Carta de Tarot semanal",
        "btn_reminder": "⏰ Configurar recordatorio",
        "btn_change_sign": "♻️ Cambiar signo",
        "btn_cancel_reminders": "❌ Cancelar recordatorios",
        "btn_back": "⬅️ Atrás",
        "btn_change_lang": "🌐 Cambiar idioma",
        "reminder_prompt": "¿A qué hora? (HH:MM)",
        "reminder_set": "¡Listo! Cada día a las {time}.",
        "reminder_cleared": "Recordatorios desactivados.",
        "unknown": "No entendí 🙂",
    },
}

# =======================
# USERS STORAGE
# =======================

def load_users() -> Dict[str, Any]:
    if not USERS_FILE.exists():
        return {}
    try:
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"Load users error: {e}")
        return {}


def save_users(data: Dict[str, Any]) -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    USERS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_user(chat_id: int) -> Dict[str, Any]:
    return load_users().get(str(chat_id), {})


def update_user(chat_id: int, **kwargs) -> Dict[str, Any]:
    users = load_users()
    user = users.get(str(chat_id), {})
    user.update(kwargs)
    users[str(chat_id)] = user
    save_users(users)
    return user


def get_lang(chat_id: int) -> str:
    lang = get_user(chat_id).get("lang", "ru")
    return lang if lang in UI else "ru"
# -----------------------
# KEYBOARDS
# -----------------------

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
    for i, sign in enumerate(ZODIAC_SIGNS):
        label = SIGN_NAMES.get(lang, SIGN_NAMES["ru"]).get(sign, sign)
        if i % 2 == 0:
            kb.row(KeyboardButton(label))
        else:
            kb.insert(KeyboardButton(label))
    return kb


def build_main_keyboard(lang: str):
    ui = UI[lang]
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(ui["btn_tarot"]))
    kb.row(KeyboardButton(ui["btn_reminder"]))
    kb.row(KeyboardButton(ui["btn_change_sign"]))
    kb.row(KeyboardButton(ui["btn_change_lang"]))
    return kb


# -----------------------
# COMMANDS
# -----------------------

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    user = get_user(message.chat.id)
    lang = user.get("lang")

    if lang not in UI:
        await message.answer(
            UI["ru"]["choose_lang"],
            reply_markup=build_lang_keyboard(),
        )
        return

    ui = UI[lang]
    sign = user.get("sign")

    if sign:
        await message.answer(
            ui["start_with_sign"].format(
                name=message.from_user.first_name,
                sign=sign,
            ),
            reply_markup=build_main_keyboard(lang),
        )
    else:
        await message.answer(
            ui["start_no_sign"],
            reply_markup=build_sign_keyboard(lang),
        )


# -----------------------
# LANGUAGE SELECT
# -----------------------

@dp.message_handler(
    lambda m: m.text in {
        UI["ru"]["btn_lang_ru"],
        UI["ru"]["btn_lang_en"],
        UI["ru"]["btn_lang_es"],
    }
)
async def choose_language(message: types.Message):
    if message.text == UI["ru"]["btn_lang_ru"]:
        lang = "ru"
    elif message.text == UI["ru"]["btn_lang_en"]:
        lang = "en"
    else:
        lang = "es"

    update_user(message.chat.id, lang=lang)

    ui = UI[lang]
    await message.answer(
        ui["lang_set"] if "lang_set" in ui else "OK",
        reply_markup=build_sign_keyboard(lang),
    )


# -----------------------
# ZODIAC SIGN SELECT
# -----------------------

@dp.message_handler(lambda m: m.text in SIGN_NAMES.get("ru", {}).values())
async def choose_sign(message: types.Message):
    lang = get_lang(message.chat.id)

    sign = next(
        (k for k, v in SIGN_NAMES[lang].items() if v == message.text),
        None,
    )
    if not sign:
        return

    update_user(message.chat.id, sign=sign)

    await message.answer(
        generate(sign, lang),
        reply_markup=build_main_keyboard(lang),
    )


# -----------------------
# TAROT
# -----------------------

@dp.message_handler(lambda m: m.text in {
    UI["ru"]["btn_tarot"],
    UI["en"]["btn_tarot"],
    UI["es"]["btn_tarot"],
})
async def tarot(message: types.Message):
    user = get_user(message.chat.id)
    sign = user.get("sign")
    lang = get_lang(message.chat.id)

    if not sign:
        await message.answer(UI[lang]["unknown"])
        return

    text, image_path = draw_tarot_for_user(message.chat.id, sign, lang)

    if image_path and Path(image_path).exists():
        with open(image_path, "rb") as img:
            await message.answer_photo(img, caption=text)
    else:
        await message.answer(text)


# -----------------------
# DAILY REMINDERS
# -----------------------

async def daily_reminders_loop():
    while True:
        now = datetime.now(TZ).strftime("%H:%M")
        users = load_users()

        for chat_id, data in users.items():
            if data.get("reminder_time") == now and data.get("sign"):
                try:
                    text = generate(data["sign"], data.get("lang", "ru"))
                    await bot.send_message(int(chat_id), text)
                except Exception as e:
                    logger.error(f"Reminder error {chat_id}: {e}")

        await asyncio.sleep(60)


@dp.message_handler(lambda m: m.text in {
    UI["ru"]["btn_reminder"],
    UI["en"]["btn_reminder"],
    UI["es"]["btn_reminder"],
})
async def ask_reminder_time(message: types.Message):
    lang = get_lang(message.chat.id)
    await message.answer(UI[lang]["reminder_prompt"])


@dp.message_handler(lambda m: ":" in m.text and len(m.text) == 5)
async def set_reminder(message: types.Message):
    lang = get_lang(message.chat.id)
    update_user(message.chat.id, reminder_time=message.text)

    await message.answer(
        UI[lang]["reminder_set"].format(time=message.text),
        reply_markup=build_main_keyboard(lang),
    )


# -----------------------
# API HEALTH CHECK
# -----------------------

@dp.message_handler(commands=["api"])
async def api_health(message: types.Message):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/health", timeout=5) as resp:
                await message.answer(f"API OK: {await resp.text()}")
    except Exception as e:
        await message.answer(f"API ERROR: {e}")


# -----------------------
# STARTUP
# -----------------------

async def on_startup(dp: Dispatcher):
    asyncio.create_task(daily_reminders_loop())
    logger.info("AstroBot started successfully")


# -----------------------
# MAIN ENTRY
# -----------------------

if __name__ == "__main__":

    if POLLING_STARTED:
        logger.error("Polling already running. Exit.")
        sys.exit(0)

    POLLING_STARTED = True
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup,
    )

import os
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import aiohttp  # === SAFE API ADDITION ===

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

# === SAFE API CONFIG ===
API_BASE_URL = "https://astrobot-api-jrrr.onrender.com"
# =======================

BASE_DIR = Path(__file__).parent
USERS_FILE = BASE_DIR / "users_state.json"
TAROT_IMAGES_DIR = BASE_DIR / "tarot_images"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен: TELEGRAM_BOT_TOKEN или BOT_TOKEN
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError(
        "Не найден TELEGRAM_BOT_TOKEN или BOT_TOKEN в переменных окружения"
    )

ADMIN_IDS = {
    8023489016,
}

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

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
        "reminder_prompt": (
            "Во сколько тебе удобно получать ежедневный гороскоп?\n"
            "Например: 09:00\n\n"
            "Или выбери время из предложенных вариантов:"
        ),
        "reminder_set": "Отлично! Я буду отправлять гороскоп каждый день в {time}.",
        "reminder_cleared": "Ежедневные напоминания отключены.",
        "back_to_menu": "Возвращаю в главное меню.",
        "need_sign": "Сначала выбери свой знак зодиака:",
        "unknown": "Я тебя не понял. Используй кнопки ниже 🙂",
        "tarot_already": "Ты уже вытянул карту на этой неделе 🙂\nСледующую можно будет получить через 7 дней.",
        "stats_header_users": "👥 Всего пользователей: {total}",
        "stats_header_notify": "⏰ С включёнными напоминаниями: {with_notify}",
        "stats_by_sign": "⭐️ По знакам:",
        "reminder_time_format": "Пожалуйста, введи время в формате ЧЧ:ММ, например 09:00.",
        "lang_set": "Язык сохранён: Русский.",
        "btn_change_lang": "🌐 Сменить язык",
    },
    "en": {
        "choose_lang": "Choose your language:",
        "btn_lang_ru": "🇷🇺 Русский",
        "btn_lang_en": "🇬🇧 English",
        "btn_lang_es": "🇪🇸 Español",
        "start_no_sign": "✨ Hi! I am AstroBot.\n\nChoose your zodiac sign:",
        "start_with_sign": "Hi again, {name}!\n\nYour current sign: {sign}.",
        "btn_tarot": "🔮 Weekly Tarot card",
        "btn_reminder": "⏰ Set reminder",
        "btn_change_sign": "♻️ Change sign",
        "btn_cancel_reminders": "❌ Cancel reminders",
        "btn_back": "⬅️ Back",
        "reminder_prompt": (
            "What time should I send your daily horoscope?\n"
            "For example: 09:00\n\n"
            "Or choose from the options below:"
        ),
        "reminder_set": "Great! I will send your horoscope every day at {time}.",
        "reminder_cleared": "Daily reminders are turned off.",
        "back_to_menu": "Back to main menu.",
        "need_sign": "First choose your zodiac sign:",
        "unknown": "I didn’t understand. Please use the buttons below 🙂",
        "tarot_already": "You already drew a card for this week 🙂\nYou can draw a new one in 7 days.",
        "stats_header_users": "👥 Total users: {total}",
        "stats_header_notify": "⏰ With reminders: {with_notify}",
        "stats_by_sign": "⭐️ By signs:",
        "reminder_time_format": "Please enter time in HH:MM format, e.g. 09:00.",
        "lang_set": "Language set to English.",
        "btn_change_lang": "🌐 Change language",
    },
    "es": {
        "choose_lang": "Elige un idioma:",
        "btn_lang_ru": "🇷🇺 Русский",
        "btn_lang_en": "🇬🇧 English",
        "btn_lang_es": "🇪🇸 Español",
        "start_no_sign": "✨ ¡Hola! Soy AstroBot.\n\nElige tu signo del zodiaco:",
        "start_with_sign": "Hola de nuevo, {name}!\n\nTu signo actual: {sign}.",
        "btn_tarot": "🔮 Carta de Tarot semanal",
        "btn_reminder": "⏰ Configurar recordatorio",
        "btn_change_sign": "♻️ Cambiar signo",
        "btn_cancel_reminders": "❌ Desactivar recordatorios",
        "btn_back": "⬅️ Atrás",
        "reminder_prompt": (
            "¿A qué hora quieres recibir tu horóscopo diario?\n"
            "Por ejemplo: 09:00\n\n"
            "O elige una hora de la lista:"
        ),
        "reminder_set": "¡Perfecto! Enviaré tu horóscopo cada día a las {time}.",
        "reminder_cleared": "Los recordatorios diarios están desactivados.",
        "back_to_menu": "Volviendo al menú principal.",
        "need_sign": "Primero elige tu signo del zodiaco:",
        "unknown": "No te he entendido. Usa los botones de abajo 🙂",
        "tarot_already": "Ya has sacado tu carta de esta semana 🙂\nPodrás sacar otra dentro de 7 días.",
        "stats_header_users": "👥 Usuarios totales: {total}",
        "stats_header_notify": "⏰ Con recordatorios: {with_notify}",
        "stats_by_sign": "⭐️ Por signos:",
        "reminder_time_format": "Introduce la hora en formato HH:MM, por ejemplo 09:00.",
        "lang_set": "Idioma configurado: Español.",
        "btn_change_lang": "🌐 Cambiar idioma",
    },
}
# ----------------------- Работа с пользователями --------------------

def load_users() -> Dict[str, Any]:
    if not USERS_FILE.exists():
        return {}
    try:
        with USERS_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка чтения {USERS_FILE}: {e}")
        return {}


def save_users(data: Dict[str, Any]) -> None:
    try:
        USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with USERS_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка записи {USERS_FILE}: {e}")


def get_user(chat_id: int) -> Dict[str, Any]:
    users = load_users()
    return users.get(str(chat_id), {})


def update_user(chat_id: int, **kwargs) -> Dict[str, Any]:
    users = load_users()
    u = users.get(str(chat_id), {})
    u.update(kwargs)
    users[str(chat_id)] = u
    save_users(users)
    return u


def get_user_lang(chat_id: int) -> str:
    u = get_user(chat_id)
    lang = u.get("lang", "ru")
    if lang not in ("ru", "en", "es"):
        lang = "ru"
    return lang


# ----------------------------- Клавиатуры ---------------------------

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


def build_lang_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(
        KeyboardButton(UI["ru"]["btn_lang_ru"]),
        KeyboardButton(UI["ru"]["btn_lang_en"]),
        KeyboardButton(UI["ru"]["btn_lang_es"]),
    )
    return kb


def build_sign_keyboard(lang: str) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for i, sign in enumerate(ZODIAC_SIGNS):
        local = SIGN_NAMES.get(lang, SIGN_NAMES["ru"]).get(sign, sign)
        btn_text = local
        if i % 2 == 0:
            kb.row(KeyboardButton(btn_text))
        else:
            kb.insert(KeyboardButton(btn_text))
    return kb


def build_main_keyboard(sign: str, lang: str) -> ReplyKeyboardMarkup:
    ui = UI[lang]
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(ui["btn_tarot"]))
    kb.row(KeyboardButton(ui["btn_reminder"]))
    kb.row(KeyboardButton(ui["btn_change_sign"]))
    kb.row(KeyboardButton(ui["btn_change_lang"]))
    return kb


def build_time_keyboard(lang: str) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    times = ["07:00", "08:00", "09:00", "10:00", "19:00", "20:00", "21:00"]
    for t in times:
        kb.row(KeyboardButton(t))
    kb.row(KeyboardButton(UI[lang]["btn_cancel_reminders"]))
    kb.row(KeyboardButton(UI[lang]["btn_back"]))
    return kb


# ----------------------------- API CHECK ----------------------------

@dp.message_handler(commands=["api"])
async def handle_api_health(message: types.Message):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/health", timeout=5) as resp:
                data = await resp.json()
                await message.answer(f"✅ API health: {data}")
    except Exception as e:
        await message.answer(f"❌ API error: {e}")


# ----------------------------- Хэндлеры -----------------------------

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    user = get_user(message.chat.id)
    lang = user.get("lang")
    if lang not in ("ru", "en", "es"):
        await message.answer("Выберите язык:", reply_markup=build_lang_keyboard())
        return

    ui = UI[lang]
    sign = user.get("sign")
    if sign:
        await message.answer(
            ui["start_with_sign"].format(
                name=message.from_user.first_name, sign=sign
            ),
            reply_markup=build_main_keyboard(sign, lang),
        )
    else:
        await message.answer(ui["start_no_sign"], reply_markup=build_sign_keyboard(lang))


@dp.message_handler(
    lambda m: m.text
    and m.text
    in {
        UI["ru"]["btn_lang_ru"],
        UI["ru"]["btn_lang_en"],
        UI["ru"]["btn_lang_es"],
    }
)
async def handle_lang_choice(message: types.Message):
    text = message.text
    if text == UI["ru"]["btn_lang_ru"]:
        lang = "ru"
    elif text == UI["ru"]["btn_lang_en"]:
        lang = "en"
    else:
        lang = "es"

    user = update_user(message.chat.id, lang=lang)
    ui = UI[lang]
    sign = user.get("sign")

    await message.answer(ui["lang_set"])
    if sign:
        await message.answer(
            ui["start_with_sign"].format(
                name=message.from_user.first_name, sign=sign
            ),
            reply_markup=build_main_keyboard(sign, lang),
        )
    else:
        await message.answer(ui["start_no_sign"], reply_markup=build_sign_keyboard(lang))


# --------------------- Ежедневные напоминания ----------------------

async def send_daily_horoscopes():
    while True:
        now = datetime.now(TZ)
        current_time = now.strftime("%H:%M")
        users = load_users()

        for chat_id_str, data in users.items():
            if data.get("reminder_time") == current_time and data.get("sign"):
                try:
                    text = generate(data["sign"], data.get("lang", "ru"))
                    await bot.send_message(int(chat_id_str), text)
                except Exception as e:
                    logger.error(f"Ошибка отправки сообщения {chat_id_str}: {e}")

        await asyncio.sleep(60)


async def on_startup(dp: Dispatcher):
    asyncio.create_task(send_daily_horoscopes())
    logger.info("Бот запущен и отправка напоминаний активирована.")


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)

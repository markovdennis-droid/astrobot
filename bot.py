import os
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import aiohttp  # === API INTEGRATION (SAFE) ===

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

# === API INTEGRATION (SAFE) ===
API_BASE_URL = "https://astrobot-api-jrrr.onrender.com"
# ==============================

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

# IDs админов, которые могут вызывать /stats
ADMIN_IDS = {
    8023489016,  # 🔁 ЗАМЕНИ на свой Telegram user_id
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

# ----------------------- API TEST HANDLER (SAFE) --------------------

@dp.message_handler(commands=["api"])
async def handle_api_health(message: types.Message):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/health", timeout=5) as resp:
                data = await resp.json()
                await message.answer(f"✅ API health: {data}")
    except Exception as e:
        await message.answer(f"❌ API error: {e}")

# -------------------------------------------------------------------

# ⬇️⬇️⬇️ ВСЁ ОСТАЛЬНОЕ — БЕЗ ИЗМЕНЕНИЙ ⬇️⬇️⬇️

# --------------------- Ежедневные напоминания ----------------------

async def send_daily_horoscopes():
    while True:
        now = datetime.now(TZ)
        current_time = now.strftime("%H:%M")
        users = load_users()

        for chat_id_str, data in users.items():
            reminder_time = data.get("reminder_time")
            sign = data.get("sign")
            lang = data.get("lang", "ru")
            if reminder_time == current_time and sign:
                try:
                    text = generate(sign, lang)
                    await bot.send_message(int(chat_id_str), text)
                except Exception as e:
                    logger.error(f"Ошибка отправки сообщения {chat_id_str}: {e}")

        await asyncio.sleep(60)


async def on_startup(dp: Dispatcher):
    asyncio.create_task(send_daily_horoscopes())
    logger.info("Бот запущен и отправка напоминаний активирована.")


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)

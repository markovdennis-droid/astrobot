import os
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from generator import generate, draw_tarot_for_user, ZODIAC_SIGNS, TZ

BASE_DIR = Path(__file__).parent
USERS_FILE = BASE_DIR / "users_state.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Эмодзи для знаков
SIGN_EMOJIS = {
    "Овен": "♈",
    "Телец": "♉",
    "Близнецы": "♊",
    "Рак": "♋",
    "Лев": "♌",
    "Дева": "♍",
    "Весы": "♎",
    "Скорпион": "♏",
    "Стрелец": "♐",
    "Козерог": "♑",
    "Водолей": "♒",
    "Рыбы": "♓",
}


# ---------- Работа с состоянием пользователей ----------

def load_users_state() -> Dict[str, Any]:
    if not USERS_FILE.exists():
        return {}
    try:
        with USERS_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_users_state(state: Dict[str, Any]) -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with USERS_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_user(chat_id: int) -> Dict[str, Any]:
    state = load_users_state()
    key = str(chat_id)
    user = state.get(key) or {}
    # значения по умолчанию
    user.setdefault("sign", None)
    user.setdefault("notify", False)
    user.setdefault("time", "09:00")
    state[key] = user
    save_users_state(state)
    return user


def update_user(chat_id: int, **fields) -> Dict[str, Any]:
    state = load_users_state()
    key = str(chat_id)
    user = state.get(key) or {}
    user.setdefault("sign", None)
    user.setdefault("notify", False)
    user.setdefault("time", "09:00")
    user.update(fields)
    state[key] = user
    save_users_state(state)
    return user


# ---------- Клавиатуры ----------

def build_sign_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    row = []
    for idx, sign in enumerate(ZODIAC_SIGNS, start=1):
        emoji = SIGN_EMOJIS.get(sign, "⭐️")
        row.append(KeyboardButton(f"{emoji} {sign}"))
        if idx % 3 == 0:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    return kb


def build_main_keyboard(sign: str) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    emoji = SIGN_EMOJIS.get(sign, "⭐️")
    kb.row(KeyboardButton(f"{emoji} {sign} — гороскоп на сегодня"))
    kb.row(KeyboardButton("♻️ Сменить знак"), KeyboardButton("🔮 Таро дня"))
    kb.row(KeyboardButton("🔔 Включить ежедневные"), KeyboardButton("🚫 Выключить ежедневные"))
    kb.row(KeyboardButton("⏰ Задать время"))
    return kb


# ---------- Инициализация бота ----------

API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not API_TOKEN:
    raise RuntimeError("Не найден TELEGRAM_BOT_TOKEN в переменных окружения.")

bot = Bot(API_TOKEN)
dp = Dispatcher(bot)

# простая память: кто сейчас вводит время
WAITING_FOR_TIME = set()


# ---------- Команды и хендлеры ----------

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    user = get_user(message.chat.id)
    if user["sign"]:
        sign = user["sign"]
        text = (
            "✨ Привет! Я астробот.\n\n"
            f"Твой текущий знак: {sign}.\n"
            "Могу показать гороскоп на сегодня, карту Таро дня и отправлять ежедневные прогнозы.\n\n"
            "Нажми кнопку ниже, чтобы получить гороскоп 👇"
        )
        await message.answer(text, reply_markup=build_main_keyboard(sign))
    else:
        await message.answer(
            "✨ Привет! Я астробот.\n\nВыбери, пожалуйста, свой знак зодиака:",
            reply_markup=build_sign_keyboard(),
        )


# выбор знака: кнопки вида "♌ Лев"
@dp.message_handler(lambda m: m.text and m.text.startswith(tuple(SIGN_EMOJIS.values())))
async def handle_sign_choice(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        return
    sign = parts[1]
    if sign not in ZODIAC_SIGNS:
        return

    update_user(message.chat.id, sign=sign)
    text = generate(sign)
    await message.answer(
        f"Знак сохранён: {sign}.\n\n{text}",
        reply_markup=build_main_keyboard(sign),
    )


@dp.message_handler(lambda m: m.text == "♻️ Сменить знак")
async def handle_change_sign(message: types.Message):
    await message.answer(
        "Выбери новый знак зодиака:",
        reply_markup=build_sign_keyboard(),
    )


@dp.message_handler(lambda m: m.text and "гороскоп на сегодня" in m.text)
async def handle_today_horoscope(message: types.Message):
    user = get_user(message.chat.id)
    sign = user.get("sign")
    if not sign:
        await message.answer(
            "Сначала выбери свой знак зодиака:",
            reply_markup=build_sign_keyboard(),
        )
        return
    text = generate(sign)
    await message.answer(text, reply_markup=build_main_keyboard(sign))


@dp.message_handler(lambda m: m.text == "🔮 Таро дня")
async def handle_tarot(message: types.Message):
    """
    Здесь как раз жёсткое правило:
    - 1-я попытка в день: выдаём карту + текст
    - 2-я и далее: ту же карту + подпись, что уже тянул
    НИКАКИХ отдельных кнопок выбора карт тут нет.
    """
    result = draw_tarot_for_user(message.chat.id)
    text = result["text"]
    if result["already_drawn"]:
        text += (
            "\n\nТы уже тянул карту сегодня 🙂"
            "\nКарту Таро можно получать только один раз в сутки."
        )
    else:
        text += "\n\nКарту Таро можно получать только один раз в сутки."

    user = get_user(message.chat.id)
    sign = user.get("sign") or "Знак"
    await message.answer(text, reply_markup=build_main_keyboard(sign))


@dp.message_handler(lambda m: m.text == "🔔 Включить ежедневные")
async def handle_enable_daily(message: types.Message):
    user = get_user(message.chat.id)
    if not user.get("sign"):
        await message.answer(
            "Сначала выбери свой знак, а потом включи ежедневные гороскопы 🙂",
            reply_markup=build_sign_keyboard(),
        )
        return
    user = update_user(message.chat.id, notify=True)
    await message.answer(
        f"Ежедневные гороскопы включены.\n"
        f"Время отправки: {user['time']} (по времени Europe/Madrid).",
        reply_markup=build_main_keyboard(user["sign"] or "Знак"),
    )


@dp.message_handler(lambda m: m.text == "🚫 Выключить ежедневные")
async def handle_disable_daily(message: types.Message):
    user = update_user(message.chat.id, notify=False)
    sign = user.get("sign") or "Знак"
    await message.answer(
        "Ежедневные гороскопы отключены.",
        reply_markup=build_main_keyboard(sign),
    )


@dp.message_handler(lambda m: m.text == "⏰ Задать время")
async def handle_set_time(message: types.Message):
    user = get_user(message.chat.id)
    if not user.get("sign"):
        await message.answer(
            "Сначала выбери свой знак, а потом задай время для ежедневных гороскопов 🙂",
            reply_markup=build_sign_keyboard(),
        )
        return

    WAITING_FOR_TIME.add(message.chat.id)
    await message.answer(
        "Напиши время в формате ЧЧ:ММ (например, 09:00 или 21:30).",
        reply_markup=types.ReplyKeyboardRemove(),
    )


@dp.message_handler(lambda m: m.chat.id in WAITING_FOR_TIME)
async def handle_time_input(message: types.Message):
    text = (message.text or "").strip()
    try:
        datetime.strptime(text, "%H:%M")
    except ValueError:
        await message.answer(
            "Неверный формат времени. Попробуй ещё раз, например: 09:00"
        )
        return

    WAITING_FOR_TIME.discard(message.chat.id)
    user = update_user(message.chat.id, time=text)
    await message.answer(
        f"Время сохранено: {text}.\n"
        "Теперь ежедневные гороскопы (если включены) будут приходить в это время.",
        reply_markup=build_main_keyboard(user["sign"] or "Знак"),
    )


# ---------- Планировщик ежедневных гороскопов ----------

async def scheduler(dp: Dispatcher):
    """
    Простейший планировщик: раз в минуту проверяет, кому отправить гороскоп.
    Работает в таймзоне TZ (Europe/Madrid из generator.py).
    """
    while True:
        now = datetime.now(TZ).strftime("%H:%M")
        state = load_users_state()
        for chat_id, data in state.items():
            try:
                if not data.get("notify"):
                    continue
                sign = data.get("sign")
                send_time = data.get("time")
                if not sign or not send_time:
                    continue
                if send_time == now:
                    text = generate(sign)
                    await dp.bot.send_message(
                        int(chat_id),
                        text,
                        reply_markup=build_main_keyboard(sign),
                    )
            except Exception as e:
                logger.exception("Ошибка при отправке ежедневного гороскопа: %s", e)
        await asyncio.sleep(60)


async def on_startup(dp: Dispatcher):
    asyncio.create_task(scheduler(dp))
    logger.info("Бот запущен и планировщик стартовал.")


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)

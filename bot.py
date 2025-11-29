import os
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from generator import generate as raw_generate, draw_tarot_for_user, ZODIAC_SIGNS, TZ

BASE_DIR = Path(__file__).parent
USERS_FILE = BASE_DIR / "users_state.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Эмодзи для знаков
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


def format_horoscope_message(sign: str) -> str:
    """
    Форматирует текст гороскопа под красивую раскладку в Telegram.

    Мы аккуратно оборачиваем то, что возвращает generator.generate, чтобы:
    - не ломать старое поведение, если там уже готовый текст;
    - уметь собирать новый формат, если generate() вернёт dict с полями.
    """
    raw = raw_generate(sign)

    # 1) Самый частый случай — generate() уже отдаёт готовую строку.
    if isinstance(raw, str):
        text = raw.strip()
        emoji = SIGN_EMOJIS.get(sign, "⭐️")
        header = f"{emoji} {sign} — гороскоп на сегодня"

        # Если первая строка уже похожа на заголовок — не дублируем.
        first_line = text.splitlines()[0] if text.splitlines() else ""
        if sign in first_line and "гороскоп" in first_line.lower():
            return text

        return f"{header}\n\n{text}"

    # 2) Продвинутый вариант: generate() возвращает dict с частями гороскопа.
    if isinstance(raw, dict):
        emoji = SIGN_EMOJIS.get(sign, "⭐️")

        now = datetime.now(TZ)
        weekday = raw.get("weekday") or now.strftime("%A")
        date_str = raw.get("date") or now.strftime("%d.%m.%Y")

        day_type = raw.get("day_type_text", "")
        day_type_emoji = raw.get("day_type_emoji", "⚡")

        season = raw.get("season") or raw.get("season_mood") or ""
        love = raw.get("love") or ""
        work = raw.get("work") or ""
        money = raw.get("money") or ""
        health = raw.get("health") or ""
        advice = raw.get("advice") or ""
        number = raw.get("number") or raw.get("day_number") or ""
        color = raw.get("color") or raw.get("day_color") or ""

        lines = [
            f"{emoji} {sign} — гороскоп на сегодня",
            "",
            f"{now.day} {weekday}, {date_str}",
            "",
            (f"Тип дня {day_type_emoji} {day_type}".strip()),
            "",
            (f"🍁 Сезонный настрой: {season}".strip()),
            (f"💕 Любовь: {love}".strip()),
            (f"👩‍💻 Работа: {work}".strip()),
            (f"💰 Деньги: {money}".strip()),
            (f"🩺 Здоровье: {health}".strip()),
            (f"🧘 Совет: {advice}".strip()),
            "",
            (f"✨ Число дня: {number}".strip()),
            (f"✨ Цвет дня: {color}".strip()),
        ]

        # Чистим пустые строки
        cleaned = [line for line in lines if line and not line.isspace()]
        return "\n".join(cleaned)

    # 3) На всякий случай — приводим к строке.
    return str(raw)


# ---------- Работа с состоянием пользователей ----------

def load_users_state() -> Dict[str, Any]:
    if not USERS_FILE.exists():
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.exception("Не удалось прочитать users_state.json: %s", e)
        return {}


def save_users_state(state: Dict[str, Any]) -> None:
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.exception("Не удалось сохранить users_state.json: %s", e)


def get_user(chat_id: int) -> Dict[str, Any]:
    state = load_users_state()
    return state.get(str(chat_id), {})


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
    kb.row(KeyboardButton("🔮 Таро дня"))
    kb.row(KeyboardButton("⏰ Настроить напоминание"))
    kb.row(KeyboardButton("♻️ Сменить знак"))
    return kb


def build_time_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(
        KeyboardButton("07:00"),
        KeyboardButton("08:00"),
        KeyboardButton("09:00"),
    )
    kb.row(
        KeyboardButton("10:00"),
        KeyboardButton("11:00"),
        KeyboardButton("12:00"),
    )
    kb.row(
        KeyboardButton("18:00"),
        KeyboardButton("20:00"),
        KeyboardButton("22:00"),
    )
    kb.row(KeyboardButton("❌ Отменить напоминания"))
    kb.row(KeyboardButton("⬅️ Назад"))
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
    sign = user.get("sign")
    if sign:
        text = (
            f"Снова привет, {message.from_user.first_name}!\n\n"
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


# выбор знака: кнопки вида "🐏 Овен"
@dp.message_handler(lambda m: m.text and m.text.startswith(tuple(SIGN_EMOJIS.values())))
async def handle_sign_choice(message: types.Message):
    parts = message.text.split(" ", 1)
    if len(parts) < 2:
        return
    sign = parts[1]
    if sign not in ZODIAC_SIGNS:
        return

    update_user(message.chat.id, sign=sign)
    text = format_horoscope_message(sign)
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
    text = format_horoscope_message(sign)
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
    await message.answer(text, reply_markup=build_main_keyboard(get_user(message.chat.id).get("sign") or "Овен"))


@dp.message_handler(lambda m: m.text == "⏰ Настроить напоминание")
async def handle_set_reminder(message: types.Message):
    WAITING_FOR_TIME.add(message.chat.id)
    await message.answer(
        "Во сколько тебе удобно получать ежедневный гороскоп?\n"
        "Например: 09:00\n\n"
        "Или выбери время из предложенных вариантов:",
        reply_markup=build_time_keyboard(),
    )


@dp.message_handler(lambda m: m.text in {"❌ Отменить напоминания", "⬅️ Назад"})
async def handle_cancel_or_back(message: types.Message):
    chat_id = message.chat.id
    if message.text == "❌ Отменить напоминания":
        update_user(chat_id, notify=False)
        if chat_id in WAITING_FOR_TIME:
            WAITING_FOR_TIME.discard(chat_id)
        await message.answer(
            "Ежедневные напоминания отключены.",
            reply_markup=build_main_keyboard(get_user(chat_id).get("sign") or "Овен"),
        )
    else:
        # Назад
        if chat_id in WAITING_FOR_TIME:
            WAITING_FOR_TIME.discard(chat_id)
        await message.answer(
            "Возвращаю в главное меню.",
            reply_markup=build_main_keyboard(get_user(chat_id).get("sign") or "Овен"),
        )


@dp.message_handler()
async def handle_any_message(message: types.Message):
    chat_id = message.chat.id
    text = message.text.strip()

    if chat_id in WAITING_FOR_TIME:
        # Ожидаем время
        if len(text) == 5 and text[2] == ":" and text[:2].isdigit() and text[3:].isdigit():
            update_user(chat_id, notify=True, time=text)
            WAITING_FOR_TIME.discard(chat_id)
            await message.answer(
                f"Отлично! Я буду отправлять гороскоп каждый день в {text}.",
                reply_markup=build_main_keyboard(get_user(chat_id).get("sign") or "Овен"),
            )
        else:
            await message.answer(
                "Пожалуйста, введи время в формате ЧЧ:ММ, например 09:00.",
                reply_markup=build_time_keyboard(),
            )
    else:
        # Если сообщение не про время, просто подсказка
        user = get_user(chat_id)
        sign = user.get("sign")
        if not sign:
            await message.answer(
                "Сначала выбери свой знак зодиака:",
                reply_markup=build_sign_keyboard(),
            )
        else:
            await message.answer(
                "Я тебя не понял. Используй кнопки ниже 🙂",
                reply_markup=build_main_keyboard(sign),
            )


# ---------- Планировщик ----------

async def scheduler(dp: Dispatcher):
    """
    Каждую минуту проверяем: есть ли пользователи, у которых сейчас время отправки.
    """
    while True:
        try:
            now_dt = datetime.now(TZ)
            now = now_dt.strftime("%H:%M")
            state = load_users_state()
            for chat_id, info in state.items():
                sign = info.get("sign")
                notify = info.get("notify", False)
                send_time = info.get("time", "09:00")

                if not notify or not sign or not send_time:
                    continue
                if send_time == now:
                    text = format_horoscope_message(sign)
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

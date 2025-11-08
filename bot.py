# bot.py
# -*- coding: utf-8 -*-
"""
ASTROBOT — single-file edition (aiogram v2)
Функции:
- /start — выбор знака (inline)
- 📝 Гороскоп на сегодня — развёрнутый текст с эмодзи
- 🔮 Таро дня — однократный выбор (после клика остальные карты исчезают)
- Ежедневные уведомления — выбор времени из слотов 06:00–10:00 (inline)
- /daily_off, /time, ♻️ Сменить знак
- SQLite-хранилище (без внешних БД)

Зависимости:
    pip install "aiogram==2.*" python-dotenv

ENV:
    BOT_TOKEN=ВАШ_ТОКЕН
    TZ=Europe/Madrid
"""

import asyncio
import contextlib
import datetime as dt
import os
import random
import secrets
import sqlite3
import textwrap
from typing import Dict, Tuple, Optional

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)

# === ENV & TZ ================================================================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
TZ = os.getenv("TZ", "Europe/Madrid")
os.environ["TZ"] = TZ

if not BOT_TOKEN or len(BOT_TOKEN) < 20:
    raise SystemExit("❌ BOT_TOKEN пуст или некорректен. Укажи его в .env")

# === BOT/DP ==================================================================
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

# === DB (SQLite) =============================================================
DB_PATH = os.path.join(os.path.dirname(__file__), "astrobot.db")

def db_connect():
    return sqlite3.connect(DB_PATH)

def db_init():
    with db_connect() as cn:
        cn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            sign TEXT,
            daily_enabled INTEGER DEFAULT 0,
            daily_hour INTEGER DEFAULT 9,
            daily_minute INTEGER DEFAULT 0,
            last_sent DATE
        )
        """)
        cn.commit()

def upsert_user(user_id: int):
    with db_connect() as cn:
        cn.execute("""
        INSERT INTO users (user_id) VALUES (?)
        ON CONFLICT(user_id) DO NOTHING
        """, (user_id,))
        cn.commit()

def set_sign(user_id: int, sign: str):
    with db_connect() as cn:
        cn.execute("""
        INSERT INTO users (user_id, sign) VALUES (?,?)
        ON CONFLICT(user_id) DO UPDATE SET sign=excluded.sign
        """, (user_id, sign))
        cn.commit()

def get_user(user_id: int) -> Optional[tuple]:
    with db_connect() as cn:
        cur = cn.execute("SELECT user_id, sign, daily_enabled, daily_hour, daily_minute, last_sent FROM users WHERE user_id=?", (user_id,))
        return cur.fetchone()

def set_daily(user_id: int, enabled: bool):
    with db_connect() as cn:
        cn.execute("UPDATE users SET daily_enabled=? WHERE user_id=?", (1 if enabled else 0, user_id))
        cn.commit()

def set_time(user_id: int, hour: int, minute: int):
    with db_connect() as cn:
        cn.execute("UPDATE users SET daily_hour=?, daily_minute=? WHERE user_id=?", (hour, minute, user_id))
        cn.commit()

def set_last_sent_today(user_id: int, today: str):
    with db_connect() as cn:
        cn.execute("UPDATE users SET last_sent=? WHERE user_id=?", (today, user_id))
        cn.commit()

def get_due_users(now_local: dt.datetime):
    today = now_local.date().isoformat()
    hh, mm = now_local.hour, now_local.minute
    with db_connect() as cn:
        cur = cn.execute("""
            SELECT user_id, sign FROM users
            WHERE daily_enabled=1
              AND daily_hour=? AND daily_minute=?
              AND (last_sent IS NULL OR last_sent <> ?)
              AND sign IS NOT NULL
        """, (hh, mm, today))
        return cur.fetchall()

# === SIGNS & UI ==============================================================
SIGNS = [
    ("♈ Овен", "aries"),
    ("♉ Телец", "taurus"),
    ("♊ Близнецы", "gemini"),
    ("♋ Рак", "cancer"),
    ("♌ Лев", "leo"),
    ("♍ Дева", "virgo"),
    ("♎ Весы", "libra"),
    ("♏ Скорпион", "scorpio"),
    ("♐ Стрелец", "sagittarius"),
    ("♑ Козерог", "capricorn"),
    ("♒ Водолей", "aquarius"),
    ("♓ Рыбы", "pisces"),
]

SIGN_NAME_RU = {code: title for title, code in SIGNS}

def kb_signs() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=3)
    buttons = [InlineKeyboardButton(text=title, callback_data=f"sign|{code}") for title, code in SIGNS]
    kb.add(*buttons)
    return kb

def kb_main():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📝 Гороскоп на сегодня"), KeyboardButton("🔮 Таро дня"))
    kb.add(KeyboardButton("♻️ Сменить знак"))
    kb.add(KeyboardButton("🔔 Включить ежедневные"), KeyboardButton("🚫 Выключить ежедневные"))
    kb.add(KeyboardButton("⏰ Задать время"))
    return kb

# === DAILY TIME PICKER (06:00–10:00) ========================================
def kb_daily_time_picker() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=3)
    times = ["06:00", "07:00", "08:00", "09:00", "10:00"]
    buttons = [InlineKeyboardButton(t, callback_data=f"daily|{t}") for t in times]
    kb.add(*buttons)
    return kb

@dp.callback_query_handler(lambda c: c.data.startswith("daily|"))
async def daily_time_pick(callback: types.CallbackQuery):
    _, hhmm = callback.data.split("|", 1)
    try:
        h, m = map(int, hhmm.split(":"))
        set_time(callback.from_user.id, h, m)
        set_daily(callback.from_user.id, True)
        with contextlib.suppress(Exception):
            await bot.edit_message_reply_markup(
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                reply_markup=None
            )
        await callback.answer("Ежедневные включены!")
        await bot.send_message(callback.message.chat.id, f"🔔 Ежедневные включены на {h:02d}:{m:02d}.", reply_markup=kb_main())
    except Exception:
        await callback.answer("Не удалось установить время.", show_alert=True)

# === TAROT (single-pick) =====================================================
TAROT_SESSIONS: Dict[Tuple[int, str], bool] = {}

TAROT_MEANINGS = {
    "1": "🌞 <b>Солнце</b> — успех, радость и гармония! День благоприятен для инициатив.",
    "2": "💖 <b>Влюблённые</b> — любовь, выбор сердцем, взаимопонимание.",
    "3": "🌈 <b>Мир</b> — завершение цикла, внутренняя целостность и покой.",
}

def tarot_keyboard(session_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton("🃏 Карта 1", callback_data=f"tarot|{session_id}|1"),
        InlineKeyboardButton("🃏 Карта 2", callback_data=f"tarot|{session_id}|2"),
        InlineKeyboardButton("🃏 Карта 3", callback_data=f"tarot|{session_id}|3"),
    )
    return kb

async def start_tarot(message: types.Message):
    session_id = secrets.token_hex(4)
    TAROT_SESSIONS[(message.chat.id, session_id)] = True
    text = "🔮 <b>Таро дня</b>\nВыбери <b>одну</b> карту — остальные закроются."
    await message.answer(text, reply_markup=tarot_keyboard(session_id))

@dp.callback_query_handler(lambda c: c.data.startswith("tarot|"))
async def tarot_pick(callback: types.CallbackQuery):
    try:
        _, session_id, card_id = callback.data.split("|", 2)
    except ValueError:
        return await callback.answer("Некорректные данные.", show_alert=True)

    key = (callback.message.chat.id, session_id)
    if not TAROT_SESSIONS.get(key, False):
        return await callback.answer("Эта раскладка уже закрыта.", show_alert=True)

    TAROT_SESSIONS[key] = False
    meaning = TAROT_MEANINGS.get(card_id, "✨ Неизвестная карта.")
    result_text = f"🔮 <b>Таро дня</b>\n\nТы выбрал <b>Карту {card_id}</b>.\n\n{meaning}"

    await callback.answer("Карта выбрана!")
    with contextlib.suppress(Exception):
        await bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text=result_text,
        )

# === HOROSCOPE GENERATOR =====================================================
QUOTES = [
    "«Удача любит смелых.»",
    "«Терпение сегодня — твой главный козырь.»",
    "«Сконцентрируйся на главном — остальное приложится.»",
    "«Слова обладают силой — говори о хорошем.»",
]

COLORS = ["красный", "синий", "зелёный", "золотой", "фиолетовый", "бирюзовый", "янтарный", "алый", "небесный", "изумрудный"]

def seed_from(sign: str, date: dt.date) -> int:
    return hash((sign, date.toordinal())) & 0xFFFFFFFF

def generate_horoscope(sign: str, date: Optional[dt.date] = None) -> str:
    if date is None:
        date = dt.datetime.now().date()
    rnd = random.Random(seed_from(sign, date))

    love = ["приятный сюрприз", "поддержка партнёра", "новое знакомство", "тёплый разговор", "гармония"]
    work = ["чёткий план", "неспешный темп", "вдохновение", "возможность проявить себя", "переговоры в твою пользу"]
    money = ["приятный бонус", "умеренные траты", "полезная инвестиция", "выгодная скидка", "успешная сделка"]
    health = ["бережёное отношение к себе", "прогулка на свежем воздухе", "умеренная активность", "баланс сна", "витаминный перекус"]
    advice = ["будь спокоен", "доверься интуиции", "оформи мысль письменно", "сделай паузу и выдохни", "расставь приоритеты"]

    num = rnd.randint(1, 99)
    color = rnd.choice(COLORS)
    q = rnd.choice(QUOTES)

    title = SIGN_NAME_RU.get(sign, sign)
    title_short = title.split()[-1] if " " in title else title

    text = textwrap.dedent(f"""
    <b>{title_short}</b> — гороскоп на сегодня

    💖 <b>Любовь:</b> {rnd.choice(love)}
    💼 <b>Работа:</b> {rnd.choice(work)}
    💰 <b>Деньги:</b> {rnd.choice(money)}
    🌿 <b>Здоровье:</b> {rnd.choice(health)}
    🎯 <b>Совет:</b> {rnd.choice(advice)}
    #️⃣ <b>Число дня:</b> {num}
    🎨 <b>Цвет:</b> {color}

    {q}
    """).strip()
    return text

# === COMMANDS & HANDLERS =====================================================
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    upsert_user(message.from_user.id)
    greet = (
        "✨ Привет! Я <b>AstroBot</b>.\n"
        "Сначала выбери свой знак зодиака:"
    )
    await message.answer(greet, reply_markup=kb_signs())

@dp.callback_query_handler(lambda c: c.data.startswith("sign|"))
async def pick_sign(callback: types.CallbackQuery):
    _, code = callback.data.split("|", 1)
    set_sign(callback.from_user.id, code)
    await callback.answer("Знак сохранён!")
    text = (
        f"Отлично! Знак <b>{SIGN_NAME_RU[code]}</b> сохранён.\n\n"
        f"Нажми «📝 Гороскоп на сегодня» или включи ежедневную рассылку."
    )
    with contextlib.suppress(Exception):
        await bot.edit_message_reply_markup(callback.message.chat.id, callback.message.message_id, reply_markup=None)
    await bot.send_message(callback.message.chat.id, text, reply_markup=kb_main())

@dp.message_handler(lambda m: m.text and m.text.startswith("📝"))
@dp.message_handler(commands=["today"])
async def send_today(message: types.Message):
    row = get_user(message.from_user.id)
    if not row or not row[1]:
        return await message.answer("Сначала выбери знак:", reply_markup=kb_signs())
    sign = row[1]
    await message.answer(generate_horoscope(sign), reply_markup=kb_main())

@dp.message_handler(lambda m: m.text and m.text.startswith("♻️"))
@dp.message_handler(commands=["sign"])
async def change_sign(message: types.Message):
    await message.answer("Выбери новый знак:", reply_markup=kb_signs())

@dp.message_handler(lambda m: m.text and m.text.startswith("🔮"))
@dp.message_handler(commands=["tarot"])
async def tarot_entry(message: types.Message):
    return await start_tarot(message)

# Ежедневные — кнопка «Включить ежедневные» показывает слоты 06–10
@dp.message_handler(lambda m: m.text and m.text.startswith("🔔"))
@dp.message_handler(commands=["daily_on"])
async def daily_on(message: types.Message):
    # Поддержка /daily_on HH:MM (опционально)
    args = (message.get_args() or "").strip()
    if args:
        try:
            h, m = map(int, args.split(":"))
            if 0 <= h < 24 and 0 <= m < 60:
                set_time(message.from_user.id, h, m)
                set_daily(message.from_user.id, True)
                return await message.answer(f"🔔 Ежедневные включены на {h:02d}:{m:02d}.", reply_markup=kb_main())
        except Exception:
            pass
    await message.answer("Выбери время ежедневной рассылки:", reply_markup=kb_daily_time_picker())

@dp.message_handler(lambda m: m.text and m.text.startswith("🚫"))
@dp.message_handler(commands=["daily_off"])
async def daily_off(message: types.Message):
    set_daily(message.from_user.id, False)
    await message.answer("🚫 Ежедневные отключены.", reply_markup=kb_main())

@dp.message_handler(lambda m: m.text and m.text.startswith("⏰"))
@dp.message_handler(commands=["time"])
async def daily_time(message: types.Message):
    row = get_user(message.from_user.id)
    if not row:
        upsert_user(message.from_user.id)
        row = get_user(message.from_user.id)
    _, sign, enabled, hh, mm, last = row
    status = "вкл" if enabled else "выкл"
    await message.answer(
        f"⏰ Текущее время рассылки: {hh:02d}:{mm:02d} ({status}).\n"
        f"Задать новое время: /daily_on HH:MM\n"
        f"Или через кнопки: «🔔 Включить ежедневные».",
        reply_markup=kb_main()
    )

# Фолбэк-подсказка
@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def fallback(message: types.Message):
    text = (
        "Доступно:\n"
        "• /start — выбор знака\n"
        "• 📝 Гороскоп на сегодня\n"
        "• 🔮 Таро дня\n"
        "• 🔔 Включить ежедневные (выбор 06:00–10:00)\n"
        "• /daily_on [HH:MM] — задать своё время\n"
        "• /daily_off — выключить рассылку\n"
        "• /time — показать настройки\n"
        "• ♻️ Сменить знак"
    )
    await message.answer(text, reply_markup=kb_main())

# === SCHEDULER LOOP ==========================================================
async def scheduler_loop():
    await asyncio.sleep(2)
    while True:
        try:
            now = dt.datetime.now()
            due = get_due_users(now)
            if due:
                for user_id, sign in due:
                    try:
                        await bot.send_message(user_id, generate_horoscope(sign))
                        set_last_sent_today(user_id, now.date().isoformat())
                    except Exception:
                        pass  # пользователь мог заблокировать бота и т.п.
        except Exception:
            pass
        await asyncio.sleep(60)

# === MAIN ====================================================================
async def on_startup(_):
    db_init()
    asyncio.create_task(scheduler_loop())

if __name__ == "__main__":
    db_init()
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)


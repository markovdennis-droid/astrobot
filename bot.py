import logging
import os
import random
import sqlite3
from datetime import date, timedelta

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ============================================================
#                      НАСТРОЙКИ
# ============================================================

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or "ВСТАВЬ_СВОЙ_ТОКЕН_СЮДА"
DB_NAME = "astrobot.db"

scheduler = AsyncIOScheduler(timezone="Europe/Madrid")
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

waiting_for_time = set()


# ============================================================
#                      БАЗА ДАННЫХ
# ============================================================

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # Таблица пользователей
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            sign_code TEXT,
            daily_enabled INTEGER DEFAULT 0,
            notify_hour INTEGER DEFAULT 9,
            notify_minute INTEGER DEFAULT 0,
            last_month INTEGER DEFAULT 0
        )
        """
    )

    # История шаблонов
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            template_id TEXT,
            used_at TEXT
        )
        """
    )

    # Новая таблица: сохранённые гороскопы на день
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_horoscopes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            day TEXT,
            text TEXT
        )
        """
    )

    conn.commit()
    conn.close()


def get_user(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, sign_code, daily_enabled, notify_hour, notify_minute, last_month "
        "FROM users WHERE user_id = ?",
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()
    return row


def ensure_user(user_id: int):
    if get_user(user_id) is None:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (user_id, sign_code, daily_enabled, notify_hour, notify_minute, last_month) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, None, 0, 9, 0, 0),
        )
        conn.commit()
        conn.close()


def set_user_sign(user_id: int, sign_code: str):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("UPDATE users SET sign_code = ? WHERE user_id = ?", (sign_code, user_id))
    conn.commit()
    conn.close()


def update_last_month(user_id: int, month: int):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET last_month = ? WHERE user_id = ?",
        (month, user_id),
    )
    conn.commit()
    conn.close()


def clear_history_for_user(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM history WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def set_daily_enabled(user_id: int, enabled: bool):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET daily_enabled = ? WHERE user_id = ?",
        (1 if enabled else 0, user_id),
    )
    conn.commit()
    conn.close()


def set_notify_time(user_id: int, hour: int, minute: int):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET notify_hour = ?, notify_minute = ? WHERE user_id = ?",
        (hour, minute, user_id),
    )
    conn.commit()
    conn.close()


def add_history(user_id: int, template_id: str):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    today = date.today().isoformat()
    cur.execute(
        "INSERT INTO history (user_id, template_id, used_at) VALUES (?, ?, ?)",
        (user_id, template_id, today),
    )
    conn.commit()
    conn.close()


def get_recent_template_ids(user_id: int, days: int = 14):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    cur.execute(
        "SELECT DISTINCT template_id FROM history WHERE user_id = ? AND used_at >= ?",
        (user_id, cutoff),
    )
    rows = cur.fetchall()
    conn.close()
    return {r[0] for r in rows}


def get_last_n_templates(user_id: int, n: int = 6):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT template_id FROM history WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, n),
    )
    rows = cur.fetchall()
    conn.close()
    return {r[0] for r in rows}


def get_all_daily_users():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, notify_hour, notify_minute FROM users WHERE daily_enabled = 1"
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# -------- сохранённые гороскопы на день --------

def get_stored_daily_horoscope(user_id: int, day: str):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT text FROM daily_horoscopes WHERE user_id = ? AND day = ? LIMIT 1",
        (user_id, day),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def store_daily_horoscope(user_id: int, day: str, text: str):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO daily_horoscopes (user_id, day, text) VALUES (?, ?, ?)",
        (user_id, day, text),
    )
    conn.commit()
    conn.close()


# ============================================================
#                      ДАННЫЕ ЗОДИАКА
# ============================================================

SIGNS = [
    ("aries", "♈", "Овен"),
    ("taurus", "♉", "Телец"),
    ("gemini", "♊", "Близнецы"),
    ("cancer", "♋", "Рак"),
    ("leo", "♌", "Лев"),
    ("virgo", "♍", "Дева"),
    ("libra", "♎", "Весы"),
    ("scorpio", "♏", "Скорпион"),
    ("sagittarius", "♐", "Стрелец"),
    ("capricorn", "♑", "Козерог"),
    ("aquarius", "♒", "Водолей"),
    ("pisces", "♓", "Рыбы"),
]

SIGN_BY_CODE = {code: (symbol, name) for code, symbol, name in SIGNS}


def get_sign_display(sign_code: str):
    if not sign_code or sign_code not in SIGN_BY_CODE:
        return None
    symbol, name = SIGN_BY_CODE[sign_code]
    return f"{symbol} {name}"


# ============================================================
#                   СЕЗОННЫЕ ШАБЛОНЫ
# ============================================================

def get_season(month: int):
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "autumn"


TEMPLATES = {
    "winter": [
        {"id": "w1", "text": "Сегодня важно беречь энергию и не распыляться."},
        {"id": "w2", "text": "Зима даёт время подумать и перестроиться."},
        {"id": "w3", "text": "Сохраняй спокойный темп и береги ресурс."},
    ],
    "spring": [
        {"id": "sp1", "text": "Весна зовёт к обновлению — начни что-то новое."},
        {"id": "sp2", "text": "Сегодня тебе особенно подходит лёгкость и движение."},
        {"id": "sp3", "text": "Весна усиливает желание расти — используй это."},
    ],
    "summer": [
        {"id": "su1", "text": "Добавь себе лёгкости, не перегружай день."},
        {"id": "su2", "text": "Лето даёт энергию проявиться ярче."},
        {"id": "su3", "text": "Хороший момент быть заметнее и активнее."},
    ],
    "autumn": [
        {"id": "a1", "text": "Сосредоточься на чётких шагах без спешки."},
        {"id": "a2", "text": "Осень помогает подвести маленькие итоги."},
        {"id": "a3", "text": "Поддержи себя чем-то тёплым — это важно."},
    ],
}


# ============================================================
#                 КОРОТКИЕ БЛОКИ ГОРСКОПА
# ============================================================

LOVE_LINES = [
    "внимание к деталям",
    "мягкий разговор решит многое",
    "немного терпения — и всё ок",
    "не спеши с выводами",
    "поддержка важнее идеальности",
]

WORK_LINES = [
    "неспешность будет плюсом",
    "не перегружай список дел",
    "аккуратные маленькие шаги",
    "не дави на себя",
    "важно не спешить",
]

MONEY_LINES = [
    "план без лишнего",
    "не делать импульсивных покупок",
    "пересмотри старые подписки",
    "не бери на себя лишнего",
    "экономия в деталях",
]

HEALTH_LINES = [
    "тишина перед сном",
    "немного больше воды",
    "чуть больше движения",
    "не перегружай нервную систему",
    "не перенапрягай голову",
]

ADVICE_EXTRA = [
    "не откладывай на завтра мелкие шаги.",
    "заметь хотя бы одну вещь, которая сегодня получилась.",
    "сделай что-то приятное без повода.",
    "не сравнивай себя с другими.",
    "будь мягче к себе.",
]

DAY_COLORS = [
    "янтарный",
    "небесно-голубой",
    "лавандовый",
    "мятный",
    "терракотовый",
    "оливковый",
    "графитовый",
]


# ============================================================
#               ПРИВЫЧКИ (мини-советы)
# ============================================================

HABIT_TIPS = {
    "сон": [
        "постарайся лечь спать на 30 минут раньше.",
        "убери экран за час до сна.",
    ],
    "вода": [
        "выпей стакан воды прямо сейчас.",
        "добавь лимон или мяту — так легче пить.",
    ],
    "прогулка": [
        "пройди 10–15 минут без телефона.",
        "пройди пару кварталов пешком.",
    ],
    "цифровой детокс": [
        "20 минут без соцсетей помогут разгрузить голову.",
        "выключи лишние уведомления хотя бы на сегодня.",
    ],
}


def get_random_habit_tip():
    category = random.choice(list(HABIT_TIPS.keys()))
    return random.choice(HABIT_TIPS[category])


# ============================================================
#               ТАЛИСМАН МЕСЯЦА (С ЭМОДЗИ)
# ============================================================

TALISMANS = {
    1: ("Гранат ❤️‍🔥", "даёт энергию и настрой на цели"),
    2: ("Аметист 🔮", "успокаивает и даёт ясность"),
    3: ("Аквамарин 💠", "помогает мягко общаться"),
    4: ("Розовый кварц 💗", "поддерживает тему любви"),
    5: ("Изумруд 💚", "про честность сердца"),
    6: ("Лунный камень 🌙", "усиливает интуицию"),
    7: ("Цитрин 🌞", "даёт уверенность"),
    8: ("Карнеол 🧡", "даёт действие и решимость"),
    9: ("Сапфир 🔷", "помогает концентрироваться"),
    10: ("Тигровый глаз 🐯", "усиливает внутренний стержень"),
    11: ("Обсидиан ⚫️", "помогает отпускать лишнее"),
    12: ("Горный хрусталь ✨", "усиливает намерения"),
}


def get_talisman_for_month(month: int):
    return TALISMANS[month]


# ============================================================
#                   ГЕНЕРАЦИЯ ГОРСКОПА
# ============================================================

def build_horoscope_text(user_id: int, sign_code: str):
    today = date.today()
    day_key = today.isoformat()

    # 1. Проверяем, есть ли уже гороскоп на сегодня
    stored = get_stored_daily_horoscope(user_id, day_key)
    if stored:
        return stored

    # 2. Если нет — генерируем новый и сразу сохраняем
    sign_symbol, sign_name = SIGN_BY_CODE[sign_code]
    month = today.month
    season = get_season(month)

    # Смена месяца -> очистка истории
    user = get_user(user_id)
    last_month = user[5]
    if last_month != month:
        clear_history_for_user(user_id)
        update_last_month(user_id, month)

    seasonal_templates = TEMPLATES[season]
    last6 = get_last_n_templates(user_id, n=6)
    last14 = get_recent_template_ids(user_id)
    blocked = last6.union(last14)

    available = [t for t in seasonal_templates if t["id"] not in blocked]
    if not available:
        available = seasonal_templates.copy()

    template = random.choice(available)
    add_history(user_id, template["id"])

    seasonal_advice = template["text"]

    love = random.choice(LOVE_LINES)
    work = random.choice(WORK_LINES)
    money = random.choice(MONEY_LINES)
    health = random.choice(HEALTH_LINES)
    extra = random.choice(ADVICE_EXTRA)
    day_number = random.randint(1, 9)
    color = random.choice(DAY_COLORS)
    habit = get_random_habit_tip()
    gem, aura = get_talisman_for_month(month)

    text = (
        f"{sign_symbol} {sign_name} — гороскоп на сегодня\n\n"
        f"💖 Любовь: {love}\n"
        f"💼 Работа: {work}\n"
        f"💰 Деньги: {money}\n"
        f"🌿 Здоровье: {health}\n"
        f"🎯 Совет: {seasonal_advice} {extra}\n"
        f"#️⃣ Число дня: {day_number}\n"
        f"🎨 Цвет: {color}\n"
        f"💡 Привычка дня: {habit}\n"
        f"💎 Талисман месяца: {gem} — {aura}."
    )

    # сохраняем этот текст как "гороскоп дня" для пользователя
    store_daily_horoscope(user_id, day_key, text)
    return text


# ============================================================
#                     ТАРО: 3 КАРТЫ
# ============================================================

TAROT_CARDS = [
    ("Шут", "Время позволить себе лёгкость. Позволь новому войти в жизнь мягко и спокойно."),
    ("Маг", "У тебя есть всё нужное, чтобы сделать шаг вперёд. Действуй уверенно."),
    ("Жрица", "Интуиция сегодня подсказывает верные решения. Прислушайся к себе."),
    ("Императрица", "День заботы о себе. Комфорт, красота и спокойствие принесут энергию."),
    ("Император", "Хороший момент навести порядок и почувствовать уверенную опору."),
    ("Иерофант", "Рядом есть поддержка. Правильные люди помогут, если попросишь."),
    ("Влюблённые", "День гармонии и мягкого соединения с близкими или с собой."),
    ("Колесница", "Время двигаться вперёд. Даже маленький шаг имеет значение."),
    ("Сила", "Твоя сила — в спокойствии. Мягкость сегодня сильнее давления."),
    ("Умеренность", "Баланс — ключ дня. Ничего не нужно форсировать."),
    ("Звезда", "Очень светлая карта: вдохновение, мечты и спокойная вера в лучшее."),
    ("Луна", "Творчество и чувствительность усиливаются. Прислушайся к настроению."),
    ("Солнце", "Очень сильная карта: ясность, радость и удачные решения."),
    ("Мир", "Завершение цикла и внутреннее спокойствие. Всё идёт как нужно."),
]


# ============================================================
#                     КЛАВИАТУРЫ
# ============================================================

main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.row(
    KeyboardButton("✨ Гороскоп на сегодня"),
    KeyboardButton("🎴 Таро дня"),
)
main_kb.row(KeyboardButton("♻️ Сменить знак"))
main_kb.row(
    KeyboardButton("✅ Включить ежедневные"),
    KeyboardButton("⛔️ Выключить ежедневные"),
)
main_kb.row(KeyboardButton("⏰ Задать время"))

sign_kb = InlineKeyboardMarkup(row_width=3)
for code, symbol, name in SIGNS:
    sign_kb.insert(
        InlineKeyboardButton(f"{symbol} {name}", callback_data=f"sign_{code}")
    )


# ============================================================
#                    ХЕНДЛЕРЫ КОМАНД
# ============================================================

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    ensure_user(user_id)

    user = get_user(user_id)
    _, sign_code, _, h, m, _ = user

    sign_display = get_sign_display(sign_code) or "не выбран"

    await message.answer(
        "✨ Привет! Я AstroBot.\n\n"
        "Я делаю мягкие ежедневные гороскопы с блоками по сферам жизни, "
        "мини-привычками, сезонными советами и талисманом месяца.\n\n"
        f"Твой текущий знак: {sign_display}\n"
        "Можешь сразу запросить гороскоп или выбрать знак:",
        reply_markup=main_kb,
    )

    if not sign_code:
        await message.answer("Выбери свой знак зодиака:", reply_markup=sign_kb)


@dp.message_handler(lambda m: m.text == "♻️ Сменить знак")
async def change_sign(message: types.Message):
    await message.answer("Выбери свой знак:", reply_markup=sign_kb)


@dp.callback_query_handler(lambda c: c.data.startswith("sign_"))
async def pick_sign(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    sign_code = callback_query.data.replace("sign_", "")

    if sign_code not in SIGN_BY_CODE:
        await callback_query.answer("Ошибка", show_alert=True)
        return

    set_user_sign(user_id, sign_code)
    await callback_query.answer("Знак обновлён!", show_alert=False)

    await bot.send_message(
        user_id,
        f"Знак сохранён: {get_sign_display(sign_code)}.\n"
        "Теперь можешь запросить гороскоп ✨",
        reply_markup=main_kb,
    )


@dp.message_handler(lambda m: m.text == "✨ Гороскоп на сегодня")
async def horoscope_today(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)

    if not user or not user[1]:
        await message.answer("Сначала выбери знак:", reply_markup=sign_kb)
        return

    _, sign_code, _, _, _, _ = user

    text = build_horoscope_text(user_id, sign_code)
    await message.answer(text, reply_markup=main_kb)


# ------------------------ ТАРО ------------------------

@dp.message_handler(lambda m: m.text == "🎴 Таро дня")
async def tarot(message: types.Message):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("🃏 Карта 1", callback_data="tarot_1"),
        InlineKeyboardButton("🃏 Карта 2", callback_data="tarot_2"),
        InlineKeyboardButton("🃏 Карта 3", callback_data="tarot_3"),
    )
    await message.answer("Выбери карту:", reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data.startswith("tarot_"))
async def tarot_pick(callback_query: types.CallbackQuery):
    card_name, meaning = random.choice(TAROT_CARDS)

    await callback_query.answer("Карта открыта 🌟", show_alert=False)

    await bot.send_message(
        callback_query.from_user.id,
        f"🎴 Карта дня: {card_name}\n\n{meaning}",
        reply_markup=main_kb,
    )


# ------------------------ ЕЖЕДНЕВНЫЕ ------------------------

def schedule_daily_job(user_id: int, hour: int, minute: int):
    job_id = f"daily_{user_id}"
    scheduler.add_job(
        send_daily_horoscope,
        "cron",
        hour=hour,
        minute=minute,
        args=[user_id],
        id=job_id,
        replace_existing=True,
    )


def remove_daily_job(user_id: int):
    job_id = f"daily_{user_id}"
    try:
        scheduler.remove_job(job_id)
    except:
        pass


async def send_daily_horoscope(user_id: int):
    user = get_user(user_id)
    if not user:
        return

    _, sign_code, daily_enabled, _, _, _ = user

    if not daily_enabled or not sign_code:
        return

    text = build_horoscope_text(user_id, sign_code)
    try:
        await bot.send_message(user_id, text, reply_markup=main_kb)
    except Exception as e:
        logging.warning(f"Ошибка отправки пользователю {user_id}: {e}")


@dp.message_handler(lambda m: m.text == "✅ Включить ежедневные")
async def enable_daily(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)

    if not user[1]:
        await message.answer("Сначала выбери знак:", reply_markup=sign_kb)
        return

    _, _, _, h, m, _ = user

    set_daily_enabled(user_id, True)
    schedule_daily_job(user_id, h, m)

    await message.answer(
        f"Ежедневные включены! Отправка будет в {h:02d}:{m:02d}.",
        reply_markup=main_kb,
    )


@dp.message_handler(lambda m: m.text == "⛔️ Выключить ежедневные")
async def disable_daily(message: types.Message):
    user_id = message.from_user.id
    set_daily_enabled(user_id, False)
    remove_daily_job(user_id)

    await message.answer("Ежедневные выключены.", reply_markup=main_kb)


# ------------------------ ВЫБОР ВРЕМЕНИ ------------------------

@dp.message_handler(lambda m: m.text == "⏰ Задать время")
async def set_time(message: types.Message):
    user_id = message.from_user.id
    waiting_for_time.add(user_id)

    await message.answer(
        "Напиши время в формате ЧЧ:ММ, например 09:30 или 21:05."
    )


@dp.message_handler(lambda m: m.from_user.id in waiting_for_time)
async def save_time(message: types.Message):
    user_id = message.from_user.id
    txt = message.text.strip()

    try:
        hour, minute = map(int, txt.split(":"))
        assert 0 <= hour <= 23
        assert 0 <= minute <= 59
    except:
        await message.answer("Формат неправильный. Пример: 08:40")
        return

    waiting_for_time.discard(user_id)
    set_notify_time(user_id, hour, minute)

    user = get_user(user_id)
    _, _, enabled, _, _, _ = user

    if enabled:
        schedule_daily_job(user_id, hour, minute)

    await message.answer(
        f"Время сохранено: {hour:02d}:{minute:02d}",
        reply_markup=main_kb,
    )


# ЭХО на все неизвестные сообщения
@dp.message_handler()
async def echo(message: types.Message):
    await message.answer(f"Ты написал(а): {message.text}")


# ============================================================
#                      СТАРТ БОТА
# ============================================================

async def on_startup(dp):
    init_db()
    scheduler.start()

if __name__ == "__main__":
    init_db()
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)

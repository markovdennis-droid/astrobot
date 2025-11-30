import os
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from generator import generate as raw_generate, draw_tarot_for_user, ZODIAC_SIGNS, TZ

BASE_DIR = Path(__file__).parent
USERS_FILE = BASE_DIR / "users_state.json"
TAROT_IMAGES_DIR = BASE_DIR / "tarot_images"  # сюда класть картинки карт

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- НАСТРОЙКИ АДМИНА ДЛЯ /stats ----------

# Если ADMIN_ID = 0, команду /stats может вызывать любой
# Если ADMIN_ID != 0 — только этот chat_id
ADMIN_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

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


def _extract_value(line: str, key: str) -> str:
    """
    Вспомогательная функция: достаём часть после ключа.
    Пример:
    "🌀 Тип дня: гармоничный день" + key="Тип дня" -> "гармоничный день"
    """
    if not line:
        return ""
    try:
        line = line.strip()
        idx = line.find(key)
        if idx == -1:
            # если ключ не нашли — просто убираем эмодзи и возвращаем текст
            return line.lstrip("✨📅🌀🕊💖💼💰🌿🎯#️⃣🎨 ").strip()
        sub = line[idx + len(key):].strip()
        if sub.startswith(":"):
            sub = sub[1:].strip()
        return sub
    except Exception:
        return line.strip()


def _get_season_emoji(now: datetime) -> str:
    """
    Возвращает эмодзи сезона в зависимости от месяца:
    зима ❄️, весна 🌸, лето ☀️, осень 🍁
    """
    month = now.month
    if month in (12, 1, 2):
        return "❄️"
    elif month in (3, 4, 5):
        return "🌸"
    elif month in (6, 7, 8):
        return "☀️"
    else:
        return "🍁"


def format_horoscope_message(sign: str) -> str:
    """
    Форматируем текст гороскопа в раскладку.
    """
    raw = raw_generate(sign)
    emoji = SIGN_EMOJIS.get(sign, "⭐️")
    now = datetime.now(TZ)
    season_emoji = _get_season_emoji(now)

    # ----- Вариант 1: generate() отдаёт dict -----
    if isinstance(raw, dict):
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
            f"{weekday}, {date_str}",
            "",
            (f"Тип дня {day_type_emoji} {day_type}".strip()) if day_type else "",
            "",
            (f"{season_emoji} Сезонный настрой: {season}".strip()) if season else "",
            (f"💕 Любовь: {love}".strip()) if love else "",
            (f"👩‍💻 Работа: {work}".strip()) if work else "",
            (f"💰 Деньги: {money}".strip()) if money else "",
            (f"🩺 Здоровье: {health}".strip()) if health else "",
            (f"🧘 Совет: {advice}".strip()) if advice else "",
            "",
            (f"✨ Число дня: {number}".strip()) if number else "",
            (f"✨ Цвет дня: {color}".strip()) if color else "",
        ]
        cleaned = [l for l in lines if l and not l.isspace()]
        return "\n".join(cleaned)

    # ----- Вариант 2: generate() отдаёт строку (текущий случай) -----
    if isinstance(raw, str):
        lines_in = [l.strip() for l in raw.splitlines() if l.strip()]

        # Дата (строка с 📅 или чем-то типа "Суббота, 29.11.2025")
        date_src = ""
        for l in lines_in:
            if "📅" in l or ("," in l and "." in l):
                date_src = l
                break
        date_clean = date_src.lstrip("📅").strip()
        if not date_clean:
            # запасной вариант, если не нашли
            weekday = now.strftime("%A")
            date_clean = f"{weekday}, {now.strftime('%d.%m.%Y')}"

        # Остальные блоки
        day_type_src = next((l for l in lines_in if "Тип дня" in l), "")
        season_src = next((l for l in lines_in if "Сезонный настрой" in l), "")
        love_src = next((l for l in lines_in if "Любовь" in l), "")
        work_src = next((l for l in lines_in if "Работа" in л), "") if (л := "Работа") else next((l for l in lines_in if "Работа" in l), "")
        money_src = next((l for l in lines_in if "Деньги" in l), "")
        health_src = next((l for l in lines_in if "Здоровье" in l), "")
        advice_src = next((l for l in lines_in if "Совет" in l), "")
        number_src = next((l for l in lines_in if "Число дня" in l), "")
        color_src = next((l for l in lines_in if "Цвет дня" in l), "")

        day_type = _extract_value(day_type_src, "Тип дня")
        season = _extract_value(season_src, "Сезонный настрой")
        love = _extract_value(love_src, "Любовь")
        work = _extract_value(work_src, "Работа")
        money = _extract_value(money_src, "Деньги")
        health = _extract_value(health_src, "Здоровье")
        advice = _extract_value(advice_src, "Совет")
        number = _extract_value(number_src, "Число дня").rstrip(".")
        color = _extract_value(color_src, "Цвет дня")

        out_lines = [
            f"{emoji} {sign} — гороскоп на сегодня",
            "",
            date_clean,
            "",
            (f"Тип дня ⚡ {day_type}".strip()) if day_type else "",
            "",
            (f"{season_emoji} Сезонный настрой: {season}".strip()) if season else "",
            (f"💕 Любовь: {love}".strip()) if love else "",
            (f"👩‍💻 Работа: {work}".strip()) if work else "",
            (f"💰 Деньги: {money}".strip()) if money else "",
            (f"🩺 Здоровье: {health}".strip()) if health else "",
            (f"🧘 Совет: {advice}".strip()) if advice else "",
            "",
            (f"✨ Число дня: {number}".strip()) if number else "",
            (f"✨ Цвет дня: {color}".strip()) if color else "",
        ]
        cleaned = [l for l in out_lines if l and not l.isspace()]
        return "\n".join(cleaned)

    # Фолбэк — просто строка
    return str(raw)


# ---------- Таро: поиск картинки ----------

def get_tarot_image_path(card_name: str) -> Optional[Path]:
    """
    Ищем файл картинки для карты Таро по имени.
    Ожидаем файлы в папке tarot_images:
    - tarot_images/Шут.png
    - tarot_images/Колесница.jpg
    и т.п.

    Сначала пробуем точное совпадение, потом более мягкий вариант (без регистра).
    """
    if not card_name:
        return None

    if not TAROT_IMAGES_DIR.exists():
        return None

    # точное совпадение по имени
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        candidate = TAROT_IMAGES_DIR / f"{card_name}{ext}"
        if candidate.exists():
            return candidate

    # мягкий поиск: без регистра и лишних пробелов
    norm = card_name.strip().lower()
    for path in TAROT_IMAGES_DIR.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        if path.stem.strip().lower() == norm:
            return path

    return None


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
    kb.row(KeyboardButton("🔮 Еженедельная карта Таро"))
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
            "Могу показать гороскоп на сегодня, еженедельную карту Таро и "
            "отправлять ежедневные прогнозы.\n\n"
            "Нажми кнопку ниже, чтобы получить гороскоп 👇"
        )
        await message.answer(text, reply_markup=build_main_keyboard(sign))
    else:
        await message.answer(
            "✨ Привет! Я астробот.\n\nВыбери, пожалуйста, свой знак зодиака:",
            reply_markup=build_sign_keyboard(),
        )


# /stats — показывает количество пользователей и разбивку по знакам
@dp.message_handler(commands=["stats"])
async def cmd_stats(message: types.Message):
    # если ADMIN_ID = 0 — можно всем, иначе только указанному id
    if ADMIN_ID != 0 and message.chat.id != ADMIN_ID:
        return

    state = load_users_state()
    total_users = len(state)
    with_notify = sum(1 for u in state.values() if u.get("notify"))

    by_sign: Dict[str, int] = {}
    for u in state.values():
        sign = u.get("sign") or "—"
        by_sign[sign] = by_sign.get(sign, 0) + 1

    lines = [
        f"👥 Всего пользователей: {total_users}",
        f"⏰ С включёнными напоминаниями: {with_notify}",
        "",
        "⭐️ По знакам:",
    ]
    for sign, count in sorted(by_sign.items()):
        lines.append(f"• {sign}: {count}")

    await message.answer("\n".join(lines))


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


# ---------- Еженедельная карта Таро: КАРТИНКА + ОТДЕЛЬНО ТЕКСТ ----------

@dp.message_handler(lambda m: m.text in {"🔮 Еженедельная карта Таро", "🔮 Таро дня"})
async def handle_tarot(message: types.Message):
    """
    Еженедельная карта Таро:
    - draw_tarot_for_user() сам следит за интервалом в 7 дней
    - сначала отправляем КАРТИНКУ
    - затем отдельным сообщением ТЕКСТ
    """
    result = draw_tarot_for_user(message.chat.id)
    text = result["text"]

    # дописываем предупреждение, если уже тянул в эту неделю
    if result.get("already_drawn"):
        text += (
            "\n\nТы уже вытянул карту на этой неделе 🙂"
            "\nСледующую можно будет получить через 7 дней."
        )

    # пытаемся понять имя карты
    card_name = (
        result.get("card_name")
        or result.get("card")
        or result.get("name")
    )

    # 1) отправляем картинку, если есть
    if card_name:
        img_path = get_tarot_image_path(card_name)
        if img_path and img_path.exists():
            try:
                await message.answer_photo(
                    types.InputFile(str(img_path))
                )
            except Exception as e:
                logger.exception("Не удалось отправить картинку Таро: %s", e)

    # 2) отправляем текст
    sign = get_user(message.chat.id).get("sign") or "Овен"
    await message.answer(
        text,
        reply_markup=build_main_keyboard(sign),
    )


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

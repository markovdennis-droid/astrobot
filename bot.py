import os
import json
import logging
import asyncio
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

# --- НОВОЕ: для генерации открытки ---
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).parent
USERS_FILE = BASE_DIR / "users_state.json"
TAROT_IMAGES_DIR = BASE_DIR / "tarot_images"

BACKGROUND_DIR = BASE_DIR / "horoscope_background"
BACKGROUND_DIR.mkdir(parents=True, exist_ok=True)
BACKGROUND_FILE = BACKGROUND_DIR / "background.jpg"

# сюда будем сохранять сгенерированную открытку
HOROSCOPE_CARD_FILE = BASE_DIR / "horoscope_card.jpg"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ТОЛЬКО ЭТА ПЕРЕМЕННАЯ ДЛЯ ТОКЕНА
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("Не найден TELEGRAM_BOT_TOKEN или BOT_TOKEN в переменных окружения")

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

# -------------------------------------------------------------------
#   ФУНКЦИИ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ
# -------------------------------------------------------------------

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

# -------------------------------------------------------------------
#   КЛАВИАТУРЫ
# -------------------------------------------------------------------

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
        emoji = SIGN_EMOJIS.get(sign, "⭐️")
        btn_text = f"{emoji} {local}"
        if i % 2 == 0:
            kb.row(KeyboardButton(btn_text))
        else:
            kb.insert(KeyboardButton(btn_text))
    return kb


def build_main_keyboard(sign: str, lang: str) -> ReplyKeyboardMarkup:
    ui = UI[lang]
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    emoji = SIGN_EMOJIS.get(sign, "⭐️")
    local_name = SIGN_NAMES.get(lang, SIGN_NAMES["ru"]).get(sign, sign)
    if lang == "ru":
        title = f"{emoji} {local_name} — гороскоп на сегодня"
    elif lang == "en":
        title = f"{emoji} {local_name} — horoscope for today"
    else:
        title = f"{emoji} {local_name} — horóscopo para hoy"
    kb.row(KeyboardButton(title))
    kb.row(KeyboardButton(ui["btn_tarot"]))
    kb.row(KeyboardButton(ui["btn_reminder"]))
    kb.row(KeyboardButton(ui["btn_change_sign"]))
    kb.row(KeyboardButton(ui["btn_change_lang"]))
    return kb


def build_time_keyboard(lang: str) -> ReplyKeyboardMarkup:
    ui = UI[lang]
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "ru":
        times = ["07:00", "08:00", "09:00", "10:00", "19:00", "20:00", "21:00"]
    elif lang == "en":
        times = ["07:00", "08:00", "09:00", "10:00", "7:00", "8:00", "9:00"]
    else:
        times = ["07:00", "08:00", "09:00", "10:00", "19:00", "20:00", "21:00"]

    for t in times:
        kb.row(KeyboardButton(t))
    kb.row(KeyboardButton(UI[lang]["btn_cancel_reminders"]))
    kb.row(KeyboardButton(UI[lang]["btn_back"]))
    return kb

# -------------------------------------------------------------------
#   ГЕНЕРАЦИЯ ОТКРЫТКИ С ГОРОСКОПОМ
# -------------------------------------------------------------------

def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """
    Пытаемся взять нормальный системный шрифт.
    Если не получится — используем дефолтный.
    """
    try:
        # стандартный путь для Linux контейнеров
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size=size)
    except Exception:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size=size)
        except Exception:
            return ImageFont.load_default()


def render_horoscope_card(text: str) -> Path:
    """
    Рисуем весь текст гороскопа на фоне BACKGROUND_FILE
    и сохраняем как HOROSCOPE_CARD_FILE.
    Стиль — один шрифт, мягкий коричневый цвет.
    Убираем цветные эмодзи, чтобы не было квадратиков,
    и подбираем размер шрифта так, чтобы весь текст поместился.
    """
    if not BACKGROUND_FILE.exists():
        raise FileNotFoundError("Фон не найден, BACKGROUND_FILE отсутствует")

    # Удаляем "тяжёлые" эмодзи (большие кодпоинты), чтобы не было квадратиков
    def strip_emoji(s: str) -> str:
        return "".join(ch for ch in s if ord(ch) <= 0xFFFF)

    text = strip_emoji(text)

    img = Image.open(BACKGROUND_FILE).convert("RGB")
    width, height = img.size

    # Цвет текста - мягкий коричневый, не черный
    text_color = (90, 70, 50)

    margin_x = int(width * 0.08)
    margin_y = int(height * 0.08)
    max_width = width - 2 * margin_x
    max_height = height - 2 * margin_y

    def layout_with_font(font: ImageFont.FreeTypeFont):
        draw = ImageDraw.Draw(img)
        paragraphs = text.split("\n")

        def wrap_paragraph(paragraph: str) -> list[str]:
            if not paragraph.strip():
                return [""]
            words = paragraph.split(" ")
            lines: list[str] = []
            current = ""
            for w in words:
                candidate = (current + " " + w).strip()
                bbox = draw.textbbox((0, 0), candidate, font=font)
                line_width = bbox[2] - bbox[0]
                if line_width <= max_width:
                    current = candidate
                else:
                    if current:
                        lines.append(current)
                    current = w
            if current:
                lines.append(current)
            return lines

        all_lines: list[str] = []
        for p in paragraphs:
            all_lines.extend(wrap_paragraph(p))
            all_lines.append("")  # пустая строка как интервал абзаца

        bbox = draw.textbbox((0, 0), "Ay", font=font)
        line_height = (bbox[3] - bbox[1]) + int(height * 0.008)

        total_height = 0
        for line in all_lines:
            if not line:
                total_height += line_height // 2
            else:
                total_height += line_height

        return all_lines, line_height, total_height

    # Пытаемся подобрать размер шрифта так, чтобы весь текст влез
    base_size = max(22, int(height * 0.026))
    best_font = None
    best_lines = None
    best_line_height = None

    for _ in range(6):  # до 6 итераций уменьшения
        font = _load_font(base_size)
        lines, line_height, total_height = layout_with_font(font)
        if total_height <= max_height or base_size <= 16:
            best_font = font
            best_lines = lines
            best_line_height = line_height
            break
        base_size = int(base_size * 0.9)  # уменьшаем шрифт и пробуем снова

    if best_font is None:
        best_font = _load_font(18)
        best_lines, best_line_height, _ = layout_with_font(best_font)

    img = Image.open(BACKGROUND_FILE).convert("RGB")
    draw = ImageDraw.Draw(img)

    y = margin_y
    for line in best_lines:
        if not line:
            y += best_line_height // 2
            continue
        draw.text((margin_x, y), line, fill=text_color, font=best_font)
        y += best_line_height

    img.save(HOROSCOPE_CARD_FILE, quality=95)
    return HOROSCOPE_CARD_FILE


# -------------------------------------------------------------------
#   ХЭНДЛЕРЫ
# -------------------------------------------------------------------

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
        local_name = SIGN_NAMES[lang].get(sign, sign)
        await message.answer(
            ui["start_with_sign"].format(
                name=message.from_user.first_name, sign=local_name
            ),
            reply_markup=build_main_keyboard(sign, lang),
        )
    else:
        await message.answer(ui["start_no_sign"], reply_markup=build_sign_keyboard(lang))


@dp.message_handler(commands=["lang", "language"])
async def cmd_language(message: types.Message):
    lang = get_user_lang(message.chat.id)
    ui = UI[lang]
    await message.answer(ui["choose_lang"], reply_markup=build_lang_keyboard())


@dp.message_handler(
    lambda m: m.text
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
        local_name = SIGN_NAMES[lang].get(sign, sign)
        await message.answer(
            ui["start_with_sign"].format(
                name=message.from_user.first_name, sign=local_name
            ),
            reply_markup=build_main_keyboard(sign, lang),
        )
    else:
        await message.answer(ui["start_no_sign"], reply_markup=build_sign_keyboard(lang))


@dp.message_handler(
    lambda m: m.text
    and (
        m.text == UI["ru"]["btn_change_lang"]
        or m.text == UI["en"]["btn_change_lang"]
        or m.text == UI["es"]["btn_change_lang"]
    )
)
async def handle_change_language(message: types.Message):
    lang = get_user_lang(message.chat.id)
    ui = UI[lang]
    await message.answer(ui["choose_lang"], reply_markup=build_lang_keyboard())


# выбор знака – только кнопки вида "🐏 Aries", без "—"
@dp.message_handler(
    lambda m: m.text
    and m.text.startswith(tuple(SIGN_EMOJIS.values()))
    and "—" not in m.text
)
async def handle_sign_choice(message: types.Message):
    chat_id = message.chat.id
    lang = get_user_lang(chat_id)

    parts = message.text.split(" ", 1)
    if len(parts) < 2:
        return
    label = parts[1].strip()

    base_sign = None
    for s in ZODIAC_SIGNS:
        if SIGN_NAMES.get(lang, SIGN_NAMES["ru"]).get(s, s) == label:
            base_sign = s
            break

    if not base_sign:
        return

    update_user(chat_id, sign=base_sign)
    await message.answer(
        UI[lang]["start_with_sign"].format(
            name=message.from_user.first_name, sign=label
        ),
        reply_markup=build_main_keyboard(base_sign, lang),
    )


@dp.message_handler(
    lambda m: m.text
    and any(
        m.text.startswith(prefix)
        for prefix in [
            "🐏",
            "🐂",
            "👥",
            "🦀",
            "🦁",
            "👩‍🦰",
            "⚖️",
            "🦂",
            "🏹",
            "🐐",
            "🌊",
            "🐟",
        ]
    )
    and "—" in m.text
)
async def handle_horoscope_request(message: types.Message):
    chat_id = message.chat.id
    lang = get_user_lang(chat_id)
    user = get_user(chat_id)
    sign = user.get("sign")

    if not sign:
        await message.answer(
            UI[lang]["need_sign"], reply_markup=build_sign_keyboard(lang)
        )
        return

    try:
        text = generate(sign, lang)
    except Exception as e:
        logger.error(f"Ошибка generate() для {chat_id}: {e}")
        await message.answer(UI[lang]["unknown"], reply_markup=build_main_keyboard(sign, lang))
        return

    # Если есть фон — рисуем открытку
    if BACKGROUND_FILE.exists():
        try:
            card_path = render_horoscope_card(text)
            await bot.send_photo(
                chat_id,
                photo=types.InputFile(card_path),
                reply_markup=build_main_keyboard(sign, lang),
            )
            return
        except Exception as e:
            logger.error(f"Ошибка генерации/отправки открытки для {chat_id}: {e}")

    # Fallback: отправляем просто текст
    await message.answer(text, reply_markup=build_main_keyboard(sign, lang))


@dp.message_handler(
    lambda m: m.text
    and m.text
    in {UI["ru"]["btn_change_sign"], UI["en"]["btn_change_sign"], UI["es"]["btn_change_sign"]}
)
async def handle_change_sign(message: types.Message):
    lang = get_user_lang(message.chat.id)
    ui = UI[lang]
    await message.answer(ui["start_no_sign"], reply_markup=build_sign_keyboard(lang))


@dp.message_handler(
    lambda m: m.text
    and m.text
    in {UI["ru"]["btn_tarot"], UI["en"]["btn_tarot"], UI["es"]["btn_tarot"]}
)
async def handle_tarot(message: types.Message):
    chat_id = message.chat.id
    lang = get_user_lang(chat_id)
    result = draw_tarot_for_user(chat_id, lang)

    user = get_user(chat_id)
    sign = user.get("sign", ZODIAC_SIGNS[0])

    # Пытаемся отправить картинку, если она есть
    image_path = None
    if isinstance(result, dict):
        image_name = (
            result.get("image")
            or result.get("image_file")
            or result.get("filename")
            or result.get("image_path")
        )
        if image_name:
            candidate = TAROT_IMAGES_DIR / image_name
            if candidate.exists():
                image_path = candidate

    text = result.get("text", "") if isinstance(result, dict) else str(result)

    if image_path:
        try:
            await bot.send_photo(
                chat_id,
                photo=types.InputFile(image_path),
                caption=text,
                reply_markup=build_main_keyboard(sign, lang),
            )
            return
        except Exception as e:
            logger.error(f"Ошибка отправки изображения Таро для {chat_id}: {e}")

    await message.answer(
        text,
        reply_markup=build_main_keyboard(sign, lang),
    )


@dp.message_handler(
    lambda m: m.text
    and m.text
    in {
        UI["ru"]["btn_reminder"],
        UI["en"]["btn_reminder"],
        UI["es"]["btn_reminder"],
    }
)
async def handle_reminder_button(message: types.Message):
    chat_id = message.chat.id
    lang = get_user_lang(chat_id)
    ui = UI[lang]
    await message.answer(ui["reminder_prompt"], reply_markup=build_time_keyboard(lang))


@dp.message_handler(lambda m: m.text in CANCEL_BUTTONS)
async def handle_cancel_reminders(message: types.Message):
    chat_id = message.chat.id
    lang = get_user_lang(chat_id)
    ui = UI[lang]
    user = update_user(chat_id, reminder_time=None)
    sign = user.get("sign", ZODIAC_SIGNS[0])
    await message.answer(
        ui["reminder_cleared"],
        reply_markup=build_main_keyboard(sign, lang),
    )


@dp.message_handler(lambda m: m.text in BACK_BUTTONS)
async def handle_back(message: types.Message):
    chat_id = message.chat.id
    lang = get_user_lang(chat_id)
    ui = UI[lang]
    user = get_user(chat_id)
    sign = user.get("sign")
    if not sign:
        await message.answer(ui["need_sign"], reply_markup=build_sign_keyboard(lang))
        return
    await message.answer(
        ui["back_to_menu"],
        reply_markup=build_main_keyboard(sign, lang),
    )


@dp.message_handler(
    lambda m: m.text
    and ":" in m.text
    and len(m.text) in (4, 5)
    and m.text.replace(":", "").isdigit()
)
async def handle_time_input(message: types.Message):
    chat_id = message.chat.id
    lang = get_user_lang(chat_id)
    ui = UI[lang]
    time_text = message.text.strip()

    parts = time_text.split(":")
    if len(parts) != 2:
        await message.answer(ui["reminder_time_format"])
        return

    hour_str, minute_str = parts
    if not hour_str.isdigit() or not minute_str.isdigit():
        await message.answer(ui["reminder_time_format"])
        return

    hour = int(hour_str)
    minute = int(minute_str)
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        await message.answer(ui["reminder_time_format"])
        return

    user = update_user(chat_id, reminder_time=f"{hour:02d}:{minute:02d}")
    sign = user.get("sign", ZODIAC_SIGNS[0])

    await message.answer(
        ui["reminder_set"].format(time=f"{hour:02d}:{minute:02d}"),
        reply_markup=build_main_keyboard(sign, lang),
    )


@dp.message_handler()
async def fallback_handler(message: types.Message):
    chat_id = message.chat.id
    lang = get_user_lang(chat_id)
    ui = UI[lang]
    user = get_user(chat_id)
    sign = user.get("sign")
    if sign:
        kb = build_main_keyboard(sign, lang)
    else:
        kb = build_sign_keyboard(lang)
    await message.answer(ui["unknown"], reply_markup=kb)

# -------------------------------------------------------------------
#   ЕЖЕДНЕВНЫЕ НАПОМИНАНИЯ
# -------------------------------------------------------------------

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

                    if BACKGROUND_FILE.exists():
                        try:
                            card_path = render_horoscope_card(text)
                            await bot.send_photo(
                                int(chat_id_str),
                                photo=types.InputFile(card_path),
                                reply_markup=build_main_keyboard(sign, lang),
                            )
                            continue
                        except Exception as e:
                            logger.error(
                                f"Ошибка отправки открытки в напоминании для {chat_id_str}: {e}"
                            )

                    await bot.send_message(int(chat_id_str), text)
                except Exception as e:
                    logger.error(f"Ошибка отправки сообщения {chat_id_str}: {e}")

        await asyncio.sleep(60)


async def on_startup(dp: Dispatcher):
    asyncio.create_task(send_daily_horoscopes())
    logger.info("Бот запущен и отправка напоминаний активирована.")


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)

import os
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

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

BASE_DIR = Path(__file__).parent
USERS_FILE = BASE_DIR / "users_state.json"
TAROT_IMAGES_DIR = BASE_DIR / "tarot_images"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

SUPPORTED_LANGS = ["ru", "en", "es"]

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
        "horoscope_button_pattern": "гороскоп",
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
        "horoscope_button_pattern": "horoscope",
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
        "horoscope_button_pattern": "horóscopo",
    },
}


def load_users_state() -> Dict[str, Any]:
    if not USERS_FILE.exists():
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_users_state(state: Dict[str, Any]) -> None:
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


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
    user.setdefault("lang", "ru")
    user.update(fields)
    state[key] = user
    save_users_state(state)
    return user


def get_user_lang(chat_id: int) -> str:
    user = get_user(chat_id)
    lang = user.get("lang") or "ru"
    if lang not in SUPPORTED_LANGS:
        lang = "ru"
    return lang


def get_tarot_image_path(image_name: str) -> Optional[Path]:
    if not image_name:
        return None
    path = TAROT_IMAGES_DIR / image_name
    if path.exists():
        return path
    return None


def build_sign_keyboard(lang: str) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    row = []
    for idx, base_sign in enumerate(ZODIAC_SIGNS, start=1):
        emoji = SIGN_EMOJIS.get(base_sign, "⭐️")
        local_name = SIGN_NAMES.get(lang, SIGN_NAMES["ru"]).get(base_sign, base_sign)
        row.append(KeyboardButton(f"{emoji} {local_name}"))
        if idx % 3 == 0:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    return kb


def build_lang_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row(KeyboardButton(UI["ru"]["btn_lang_ru"]))
    kb.row(KeyboardButton(UI["ru"]["btn_lang_en"]))
    kb.row(KeyboardButton(UI["ru"]["btn_lang_es"]))
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
    return kb


def build_time_keyboard(lang: str) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("07:00"), KeyboardButton("08:00"), KeyboardButton("09:00"))
    kb.row(KeyboardButton("10:00"), KeyboardButton("11:00"), KeyboardButton("12:00"))
    kb.row(KeyboardButton("18:00"), KeyboardButton("20:00"), KeyboardButton("22:00"))
    # Кнопки управления пока общие
    kb.row(KeyboardButton("❌ Отменить напоминания"))
    kb.row(KeyboardButton("⬅️ Назад"))
    return kb


API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not API_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

bot = Bot(API_TOKEN)
dp = Dispatcher(bot)

WAITING_FOR_TIME = set()


@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    user = get_user(message.chat.id)
    lang = user.get("lang")

    # Первый старт — выбираем язык
    if not lang:
        await message.answer(UI["ru"]["choose_lang"], reply_markup=build_lang_keyboard())
        return

    if lang not in SUPPORTED_LANGS:
        lang = "ru"
        update_user(message.chat.id, lang=lang)

    ui = UI[lang]
    sign = user.get("sign")

    if sign:
        local_name = SIGN_NAMES[lang].get(sign, sign)
        extra = {
            "ru": "Нажми кнопку ниже, чтобы получить гороскоп 👇",
            "en": "Tap the button below to get your horoscope 👇",
            "es": "Pulsa el botón de abajo para ver tu horóscopo 👇",
        }[lang]
        text = ui["start_with_sign"].format(name=message.from_user.first_name, sign=local_name) + "\n\n" + extra
        await message.answer(text, reply_markup=build_main_keyboard(sign, lang))
    else:
        await message.answer(ui["start_no_sign"], reply_markup=build_sign_keyboard(lang))


@dp.message_handler(commands=["stats"])
async def cmd_stats(message: types.Message):
    if ADMIN_ID != 0 and message.chat.id != ADMIN_ID:
        return

    lang = get_user_lang(message.chat.id)
    ui = UI[lang]

    state = load_users_state()
    total_users = len(state)
    with_notify = sum(1 for u in state.values() if u.get("notify"))

    by_sign: Dict[str, int] = {}
    for u in state.values():
        sign = u.get("sign") or "—"
        by_sign[sign] = by_sign.get(sign, 0) + 1

    lines = [
        ui["stats_header_users"].format(total=total_users),
        ui["stats_header_notify"].format(with_notify=with_notify),
        "",
        ui["stats_by_sign"],
    ]

    for base_sign, count in sorted(by_sign.items()):
        if base_sign in SIGN_NAMES["ru"]:
            label = SIGN_NAMES[lang].get(base_sign, base_sign)
        else:
            label = base_sign
        lines.append(f"• {label}: {count}")

    await message.answer("\n".join(lines))


@dp.message_handler(lambda m: m.text in {
    UI["ru"]["btn_lang_ru"],
    UI["ru"]["btn_lang_en"],
    UI["ru"]["btn_lang_es"],
})
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
            ui["start_with_sign"].format(name=message.from_user.first_name, sign=local_name),
            reply_markup=build_main_keyboard(sign, lang),
        )
    else:
        await message.answer(ui["start_no_sign"], reply_markup=build_sign_keyboard(lang))


@dp.message_handler(lambda m: m.text and m.text.startswith(tuple(SIGN_EMOJIS.values())))
async def handle_sign_choice(message: types.Message):
    chat_id = message.chat.id
    lang = get_user_lang(chat_id)

    parts = message.text.split(" ", 1)
    if len(parts) < 2:
        return
    label = parts[1].strip()

    # Находим внутренний знак по локализованному имени
    base_sign = None
    for s in ZODIAC_SIGNS:
        if SIGN_NAMES.get(lang, SIGN_NAMES["ru"]).get(s, s) == label:
            base_sign = s
            break

    if not base_sign:
        return

    update_user(chat_id, sign=base_sign)
    text = generate(base_sign, lang)
    local_name = SIGN_NAMES[lang].get(base_sign, base_sign)
    ui = UI[lang]

    await message.answer(
        ui["start_with_sign"].format(name=message.from_user.first_name, sign=local_name) + "\n\n" + text,
        reply_markup=build_main_keyboard(base_sign, lang),
    )


@dp.message_handler(lambda m: m.text and any(
    word in m.text.lower() for word in ("гороскоп", "horoscope", "horóscopo")
))
async def handle_today_horoscope(message: types.Message):
    chat_id = message.chat.id
    lang = get_user_lang(chat_id)
    ui = UI[lang]

    user = get_user(chat_id)
    sign = user.get("sign")
    if not sign:
        await message.answer(ui["need_sign"], reply_markup=build_sign_keyboard(lang))
        return

    text = generate(sign, lang)
    await message.answer(text, reply_markup=build_main_keyboard(sign, lang))


@dp.message_handler(lambda m: m.text and (
    m.text == UI["ru"]["btn_change_sign"] or
    m.text == UI["en"]["btn_change_sign"] or
    m.text == UI["es"]["btn_change_sign"]
))
async def handle_change_sign(message: types.Message):
    lang = get_user_lang(message.chat.id)
    ui = UI[lang]
    await message.answer(ui["need_sign"], reply_markup=build_sign_keyboard(lang))


@dp.message_handler(lambda m: m.text and (
    "таро" in m.text.lower() or "tarot" in m.text.lower()
))
async def handle_tarot(message: types.Message):
    chat_id = message.chat.id
    lang = get_user_lang(chat_id)
    ui = UI[lang]

    result = draw_tarot_for_user(chat_id, lang=lang)
    text = result["text"]
    if result.get("already_drawn"):
        text += "\n\n" + ui["tarot_already"]

    img_name = result.get("image")
    img_path = get_tarot_image_path(img_name)
    if img_path:
        try:
            await message.answer_photo(types.InputFile(str(img_path)))
        except Exception as e:
            logger.exception("Не удалось отправить картинку Таро: %s", e)

    user = get_user(chat_id)
    sign = user.get("sign") or ZODIAC_SIGNS[0]
    await message.answer(text, reply_markup=build_main_keyboard(sign, lang))


@dp.message_handler(lambda m: m.text and any(
    key in m.text.lower() for key in ("напомин", "reminder", "recordatorio")
))
async def handle_set_reminder(message: types.Message):
    chat_id = message.chat.id
    lang = get_user_lang(chat_id)
    ui = UI[lang]
    WAITING_FOR_TIME.add(chat_id)
    await message.answer(ui["reminder_prompt"], reply_markup=build_time_keyboard(lang))


@dp.message_handler(lambda m: m.text in {"❌ Отменить напоминания", "⬅️ Назад"})
async def handle_cancel_or_back(message: types.Message):
    chat_id = message.chat.id
    lang = get_user_lang(chat_id)
    ui = UI[lang]

    if message.text == "❌ Отменить напоминания":
        update_user(chat_id, notify=False)
        WAITING_FOR_TIME.discard(chat_id)
        sign = get_user(chat_id).get("sign") or ZODIAC_SIGNS[0]
        await message.answer(ui["reminder_cleared"], reply_markup=build_main_keyboard(sign, lang))
    else:
        WAITING_FOR_TIME.discard(chat_id)
        sign = get_user(chat_id).get("sign") or ZODIAC_SIGNS[0]
        await message.answer(ui["back_to_menu"], reply_markup=build_main_keyboard(sign, lang))


@dp.message_handler()
async def handle_any_message(message: types.Message):
    chat_id = message.chat.id
    lang = get_user_lang(chat_id)
    ui = UI[lang]
    text = (message.text or "").strip()

    if chat_id in WAITING_FOR_TIME:
        if len(text) == 5 and text[2] == ":" and text[:2].isdigit() and text[3:].isdigit():
            update_user(chat_id, notify=True, time=text)
            WAITING_FOR_TIME.discard(chat_id)
            sign = get_user(chat_id).get("sign") or ZODIAC_SIGNS[0]
            await message.answer(
                ui["reminder_set"].format(time=text),
                reply_markup=build_main_keyboard(sign, lang),
            )
        else:
            await message.answer(ui["reminder_time_format"], reply_markup=build_time_keyboard(lang))
    else:
        user = get_user(chat_id)
        sign = user.get("sign")
        if not sign:
            await message.answer(ui["need_sign"], reply_markup=build_sign_keyboard(lang))
        else:
            await message.answer(ui["unknown"], reply_markup=build_main_keyboard(sign, lang))


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
                lang = info.get("lang") or "ru"
                if lang not in SUPPORTED_LANGS:
                    lang = "ru"

                if not notify or not sign or not send_time:
                    continue
                if send_time == now:
                    text = generate(sign, lang)
                    await dp.bot.send_message(
                        int(chat_id),
                        text,
                        reply_markup=build_main_keyboard(sign, lang),
                    )
        except Exception as e:
            logger.exception("Ошибка при отправке ежедневного гороскопа: %s", e)
        await asyncio.sleep(60)


async def on_startup(dp: Dispatcher):
    asyncio.create_task(scheduler(dp))
    logger.info("Бот запущен и планировщик стартовал.")


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)

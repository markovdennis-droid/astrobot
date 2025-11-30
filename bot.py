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

# Явное соответствие имён карт -> файлов
TAROT_IMAGE_MAP: Dict[str, Path] = {
    "Шут": TAROT_IMAGES_DIR / "Шут.png",
    "Маг": TAROT_IMAGES_DIR / "маг.png",
    "Верховная жрица": TAROT_IMAGES_DIR / "Верховная жрица.png",
    "Императрица": TAROT_IMAGES_DIR / "Императрица.png",
    "Иерофант": TAROT_IMAGES_DIR / "Иерофант.png",
    "Влюблённые": TAROT_IMAGES_DIR / "Влюбленные.png",
    "Колесница": TAROT_IMAGES_DIR / "Колесница.png",
    "Сила": TAROT_IMAGES_DIR / "Сила.png",
    "Звезда": TAROT_IMAGES_DIR / "Звезда.png",
    "Солнце": TAROT_IMAGES_DIR / "Солнце.png",
    "Мир": TAROT_IMAGES_DIR / "Мир.png",
    "Отшельник": TAROT_IMAGES_DIR / "Отшельник.png",
    # если появятся другие карты, можно дописать сюда
}

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
    Переформатируем текст гороскопа из generator.generate()
    в красивый блок с эмодзи.
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
        work_src = next((l for l in lines_in if "Работа" in l), "")
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

        out_lines_

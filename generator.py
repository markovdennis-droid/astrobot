# generator.py
# Модуль генерации гороскопов для AstroBot
# Поддерживает RU / EN / ES, защиту от повторов и единый стиль оформления

import random
import sqlite3
from datetime import date
from typing import Optional, Tuple

# -----------------------------
# Настройки и словари
# -----------------------------

SUPPORTED_LANGS = ["en", "ru", "es"]

ZODIAC_META = {
    "aries":   {"emoji": "🐏", "en": "Aries",       "ru": "Овен",        "es": "Aries"},
    "taurus":  {"emoji": "🐂", "en": "Taurus",      "ru": "Телец",       "es": "Tauro"},
    "gemini":  {"emoji": "👥", "en": "Gemini",      "ru": "Близнецы",    "es": "Géminis"},
    "cancer":  {"emoji": "🐚", "en": "Cancer",      "ru": "Рак",         "es": "Cáncer"},
    "leo":     {"emoji": "🦁", "en": "Leo",         "ru": "Лев",         "es": "Leo"},
    "virgo":   {"emoji": "🌾", "en": "Virgo",       "ru": "Дева",        "es": "Virgo"},
    "libra":   {"emoji": "⚖️", "en": "Libra",       "ru": "Весы",        "es": "Libra"},
    "scorpio": {"emoji": "🦂", "en": "Scorpio",     "ru": "Скорпион",    "es": "Escorpio"},
    "sagittarius": {"emoji": "🏹", "en": "Sagittarius", "ru": "Стрелец", "es": "Sagitario"},
    "capricorn":   {"emoji": "🐐", "en": "Capricorn",   "ru": "Козерог", "es": "Capricornio"},
    "aquarius":    {"emoji": "🌊", "en": "Aquarius",    "ru": "Водолей", "es": "Acuario"},
    "pisces":      {"emoji": "🐟", "en": "Pisces",      "ru": "Рыбы",    "es": "Piscis"},
}

WEEKDAYS = {
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "ru": ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"],
    "es": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
}

TEXT_BLOCKS = {
    "en": {
        "tone": [
            "harmonious day",
            "dynamic and lively day",
            "calm and balanced day",
            "day of clarity and easy decisions",
            "soft and intuitive day",
            "day when many things align by themselves",
            "day with a good inner rhythm",
            "day suitable for small victories",
            "day that supports a fresh start",
        ],
        "seasonal_mood": [
            "A cozy day to sum up small results.",
            "A good moment to gently organize your life.",
            "A day to slow down a little and feel your inner comfort.",
            "The atmosphere supports calm, warm interactions.",
            "It's a good time to tidy up space and thoughts.",
            "A day to finish what has been hanging for a while.",
            "Good for quiet rituals and personal pauses.",
        ],
        "love": [
            "A good day to show care and attention.",
            "Soft conversations work better than sharp statements today.",
            "Harmony in relationships grows through small, sincere gestures.",
            "If there is tension, today it can be eased gently.",
            "For singles, this is a day to notice subtle signs from the world.",
            "Being a little warmer than usual will already change the atmosphere.",
        ],
        "work": [
            "Today accuracy is more important than speed.",
            "Great for finishing small tasks and loose ends.",
            "Suitable for putting things in order and revising plans.",
            "It's better to think twice than to rush into action.",
            "Clarifying details today will save you energy later.",
            "Quiet, focused work will be more productive than multitasking.",
        ],
        "money": [
            "It's a suitable day to slightly cut impulsive purchases.",
            "Good time to review your recent expenses.",
            "Avoid big financial decisions — let ideas ripen a bit more.",
            "Small, thoughtful spending is better than big experiments.",
            "You may notice a small but pleasant opportunity or discount.",
        ],
        "health": [
            "It’s useful to pause for breathing and a light stretch.",
            "A short walk will help you reset your state.",
            "Gentle care for the body will respond with more energy.",
            "Don't overload yourself — balance is more important today.",
            "Listening to your body will give you clear hints.",
        ],
        "advice": [
            "Don’t try to do everything at once — choose the main things.",
            "Keep a calm pace — it will be optimal today.",
            "Pay attention to small details: they lead to important results.",
            "Trust your rhythm — it is more precise than it seems.",
            "Choose the simplest solution where possible.",
        ],
        "colors": [
            "olive", "soft blue", "warm beige", "emerald", "lavender",
            "deep green", "light grey", "pearl white", "terracotta",
        ],
        "labels": {
            "title": "horoscope for today",
            "type_of_day": "Type of day",
            "seasonal_mood": "Seasonal mood",
            "love": "Love",
            "work": "Work",
            "money": "Money",
            "health": "Health",
            "advice": "Advice",
            "number_of_day": "Number of the day",
            "color_of_day": "Color of the day",
        },
    },
    "ru": {
        "tone": [
            "гармоничный день",
            "динамичный и живой день",
            "спокойный и ровный день",
            "день ясности и лёгких решений",
            "мягкий и интуитивный день",
            "день, когда многое само складывается",
            "день с хорошим внутренним ритмом",
            "день для маленьких, но важных побед",
            "день, который поддерживает новое начало",
        ],
        "seasonal_mood": [
            "Уютный день, чтобы подвести небольшие итоги.",
            "Хороший момент, чтобы мягко навести порядок в делах.",
            "День, когда хочется немного замедлиться и почувствовать комфорт.",
            "Атмосфера располагает к спокойному, тёплому общению.",
            "Подходит, чтобы разобрать пространство и мысли.",
            "День для завершения того, что давно тянется.",
            "Хорошее время для тихих личных ритуалов и пауз.",
        ],
        "love": [
            "Подходящий день, чтобы проявить заботу и внимание.",
            "Мягкие слова сегодня работают лучше, чем резкие выводы.",
            "Гармония в отношениях растёт через простые, искренние жесты.",
            "Если была напряжённость, сегодня её можно сгладить.",
            "Для одиноких это день, когда стоит присмотреться к знакомым людям.",
            "Чуть больше тепла с вашей стороны уже меняет атмосферу.",
        ],
        "work": [
            "Сегодня аккуратность важнее скорости.",
            "Подходит для завершения небольших задач.",
            "Хорошее время, чтобы разложить всё по полочкам.",
            "Лучше дважды обдумать шаг, чем спешить.",
            "Уточнение деталей сейчас сэкономит силы позже.",
            "Тихая, сосредоточенная работа будет особенно продуктивной.",
        ],
        "money": [
            "Сегодня стоит чуть сократить импульсивные покупки.",
            "Хороший день, чтобы взглянуть на недавние расходы.",
            "С крупными тратами лучше не спешить — пусть идея дозреет.",
            "Небольшие, осознанные траты предпочтительнее экспериментов.",
            "Можно заметить небольшой, но выгодный вариант или скидку.",
        ],
        "health": [
            "Полезно сделать паузу для дыхания и лёгкой разминки.",
            "Короткая прогулка поможет перезагрузиться.",
            "Мягкий режим и внимание к себе пойдут на пользу.",
            "Не перегружайте себя делами — важен баланс.",
            "Прислушиваясь к телу, вы поймёте, чего сейчас не хватает.",
        ],
        "advice": [
            "Не пытайтесь успеть всё — выберите главное.",
            "Сохраняйте спокойный темп — он сейчас оптимален.",
            "Обращайте внимание на мелочи: они приведут к важному.",
            "Доверьтесь своему внутреннему ритму.",
            "Выбирайте простое решение там, где это возможно.",
        ],
        "colors": [
            "оливковый", "нежно-голубой", "тёплый бежевый", "изумрудный",
            "лавандовый", "глубокий зелёный", "светло-серый",
            "жемчужно-белый", "терракотовый",
        ],
        "labels": {
            "title": "гороскоп на сегодня",
            "type_of_day": "Тип дня",
            "seasonal_mood": "Сезонное настроение",
            "love": "Любовь",
            "work": "Работа",
            "money": "Деньги",
            "health": "Здоровье",
            "advice": "Совет",
            "number_of_day": "Число дня",
            "color_of_day": "Цвет дня",
        },
    },
    "es": {
        "tone": [
            "día armonioso",
            "día dinámico y vivo",
            "día tranquilo y equilibrado",
            "día de claridad y decisiones sencillas",
            "día suave e intuitivo",
            "día en el que muchas cosas encajan solas",
            "día con buen ritmo interior",
            "día adecuado para pequeñas victorias",
            "día que apoya un nuevo comienzo",
        ],
        "seasonal_mood": [
            "Un día acogedor para cerrar pequeños asuntos.",
            "Buen momento para ordenar con calma lo pendiente.",
            "Un día para bajar un poco el ritmo y sentirte cómodo.",
            "La atmósfera invita a interacciones cálidas y tranquilas.",
            "Es buen momento para ordenar espacio y pensamientos.",
            "Día para terminar lo que lleva tiempo esperando.",
            "Ideal para pequeños rituales personales y pausas.",
        ],
        "love": [
            "Buen día para mostrar cariño y atención.",
            "Las palabras suaves funcionan mejor que las frases duras.",
            "La armonía en la pareja crece a través de gestos sinceros.",
            "Si había tensión, hoy se puede suavizar sin presión.",
            "Para quienes están solos, es un día para notar señales sutiles.",
            "Un poco más de calidez de tu parte ya cambia el ambiente.",
        ],
        "work": [
            "Hoy la precisión es más importante que la velocidad.",
            "Buen día para cerrar tareas pequeñas.",
            "Ideal para poner orden y revisar planes.",
            "Mejor pensar dos veces que actuar con prisa.",
            "Aclarar detalles ahora ahorrará energía más adelante.",
            "El trabajo tranquilo y concentrado será más productivo.",
        ],
        "money": [
            "Es un buen día para reducir compras impulsivas.",
            "Momento adecuado para revisar tus gastos recientes.",
            "Evita decisiones financieras grandes — deja que la idea madure.",
            "Es mejor gastar poco pero con conciencia.",
            "Puedes encontrar una pequeña oportunidad o descuento agradable.",
        ],
        "health": [
            "Es útil hacer una pausa para respirar y estirarte un poco.",
            "Un paseo corto ayudará a reiniciar tu estado.",
            "El cuerpo responde bien al cuidado suave.",
            "No te sobrecargues — hoy es importante el equilibrio.",
            "Escuchar al cuerpo te dará pistas claras.",
        ],
        "advice": [
            "No intentes hacerlo todo a la vez — elige lo principal.",
            "Mantén un ritmo tranquilo — hoy es el mejor modo.",
            "Presta atención a los detalles pequeños: llevan a grandes resultados.",
            "Confía en tu propio ritmo interior.",
            "Elige la solución más sencilla cuando sea posible.",
        ],
        "colors": [
            "oliva", "azul suave", "beige cálido", "esmeralda",
            "lavanda", "verde profundo", "gris claro",
            "blanco perla", "terracota",
        ],
        "labels": {
            "title": "horóscopo para hoy",
            "type_of_day": "Tipo de día",
            "seasonal_mood": "Ánimo de la estación",
            "love": "Amor",
            "work": "Trabajo",
            "money": "Dinero",
            "health": "Salud",
            "advice": "Consejo",
            "number_of_day": "Número del día",
            "color_of_day": "Color del día",
        },
    },
}


# -----------------------------
# Работа с БД для защиты от повторов
# -----------------------------

def _ensure_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS last_horoscopes (
                user_id TEXT NOT NULL,
                lang TEXT NOT NULL,
                sign_code TEXT NOT NULL,
                horoscope_type TEXT NOT NULL,
                date TEXT NOT NULL,
                text TEXT NOT NULL,
                PRIMARY KEY (user_id, lang, sign_code, horoscope_type, date)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _get_last_text(
    db_path: str,
    user_id: str,
    lang: str,
    sign_code: str,
    horoscope_type: str,
    current_date: date,
) -> Optional[str]:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT text
            FROM last_horoscopes
            WHERE user_id = ?
              AND lang = ?
              AND sign_code = ?
              AND horoscope_type = ?
              AND date < ?
            ORDER BY date DESC
            LIMIT 1
            """,
            (user_id, lang, sign_code, horoscope_type, current_date.isoformat()),
        )
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def _save_text(
    db_path: str,
    user_id: str,
    lang: str,
    sign_code: str,
    horoscope_type: str,
    current_date: date,
    text: str,
) -> None:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO last_horoscopes
            (user_id, lang, sign_code, horoscope_type, date, text)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, lang, sign_code, horoscope_type, current_date.isoformat(), text),
        )
        conn.commit()
    finally:
        conn.close()


# -----------------------------
# Вспомогательные функции
# -----------------------------

def _get_sign_meta(sign_code: str, lang: str) -> Tuple[str, str]:
    """
    sign_code: 'leo', 'aries' и т.п.
    lang: 'en', 'ru', 'es'
    """
    meta = ZODIAC_META.get(sign_code.lower())
    if not meta:
        emoji = "⭐"
        name = sign_code.capitalize()
    else:
        emoji = meta["emoji"]
        name = meta.get(lang, meta["en"])
    return emoji, name


def _format_date(d: date, lang: str) -> str:
    weekday_index = d.weekday()  # Monday=0
    weekday = WEEKDAYS[lang][weekday_index]
    return f"{weekday}, {d.strftime('%d.%m.%Y')}"


def _build_text(
    sign_code: str,
    lang: str,
    current_date: date,
) -> str:
    blocks = TEXT_BLOCKS[lang]
    labels = blocks["labels"]

    tone = random.choice(blocks["tone"])
    seasonal_mood = random.choice(blocks["seasonal_mood"])
    love = random.choice(blocks["love"])
    work = random.choice(blocks["work"])
    money = random.choice(blocks["money"])
    health = random.choice(blocks["health"])
    advice = random.choice(blocks["advice"])
    number_of_day = random.randint(1, 9)
    color_of_day = random.choice(blocks["colors"])

    emoji, sign_name = _get_sign_meta(sign_code, lang)
    date_str = _format_date(current_date, lang)

    # Заголовок и тело в стиле твоего примера
    if lang == "en":
        header = f"{emoji}{sign_name} — {labels['title']}\n\n{date_str}\n\n"
    elif lang == "ru":
        header = f"{emoji}{sign_name} — {labels['title']}\n\n{date_str}\n\n"
    else:  # es
        header = f"{emoji}{sign_name} — {labels['title']}\n\n{date_str}\n\n"

    body = (
        f"{labels['type_of_day']} ⚡ {tone}\n\n"
        f"❄️{labels['seasonal_mood']}: {seasonal_mood}\n"
        f"💕{labels['love']}: {love}\n"
        f"👩‍💻{labels['work']}: {work}\n"
        f"💰{labels['money']}: {money}\n"
        f"🩺{labels['health']}: {health}\n"
        f"🧘{labels['advice']}: {advice}\n\n"
        f"✨{labels['number_of_day']}: {number_of_day}\n"
        f"✨{labels['color_of_day']}: {color_of_day}"
    )

    return header + body


# -----------------------------
# Основная функция генерации
# -----------------------------

def generate_daily_horoscope(
    sign_code: str,
    lang: str = "en",
    user_id: Optional[str] = None,
    db_path: Optional[str] = None,
    today: Optional[date] = None,
    horoscope_type: str = "daily",
) -> str:
    """
    Генерация гороскопа на день.

    sign_code: 'leo', 'aries', ... (см. ZODIAC_META)
    lang: 'en' / 'ru' / 'es'
    user_id: строковый id пользователя из БД/Telegram (для защиты от повторов)
    db_path: путь к SQLite (например 'astrobot.db')
    today: дата (если None — берётся date.today())
    horoscope_type: тип гороскопа (на будущее можно добавить 'love', 'week' и т.п.)
    """
    if lang not in SUPPORTED_LANGS:
        lang = "en"

    if today is None:
        today = date.today()

    # Без БД / user_id — просто генерим текст
    if not user_id or not db_path:
        return _build_text(sign_code, lang, today)

    # С защитой от повторов
    _ensure_db(db_path)
    last_text = _get_last_text(db_path, user_id, lang, sign_code, horoscope_type, today)

    # Пытаемся несколько раз сгенерировать текст, отличный от вчерашнего
    attempts = 0
    max_attempts = 5
    text = _build_text(sign_code, lang, today)

    while last_text is not None and text == last_text and attempts < max_attempts:
        text = _build_text(sign_code, lang, today)
        attempts += 1

    _save_text(db_path, user_id, lang, sign_code, horoscope_type, today, text)
    return text


# -----------------------------
# Пример локального теста
# -----------------------------
if __name__ == "__main__":
    # Пример: локальный запуск
    print(generate_daily_horoscope("leo", lang="en"))
    print()
    print(generate_daily_horoscope("leo", lang="ru"))
    print()
    print(generate_daily_horoscope("leo", lang="es"))

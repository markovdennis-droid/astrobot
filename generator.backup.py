#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Astrobot — генератор гороскопов (CLI + OpenAI, если доступен ключ)

Использование:
  python generator.py --sign aries --style classic --lang ru --date 2025-10-13
  python generator.py --sign leo --style mystic --lang en
  python generator.py --all --style humor --lang ru

Параметры:
  --sign    знак (en): aries, taurus, gemini, cancer, leo, virgo, libra,
           scorpio, sagittarius, capricorn, aquarius, pisces
  --style   classic | humor | mystic | motivation (по умолчанию classic)
  --lang    ru | en | es (по умолчанию ru)
  --date    YYYY-MM-DD (необязательно, только для контекста текста)
  --all     сгенерировать для всех знаков (игнорирует --sign)

Логика:
  1) Если переменная окружения OPENAI_API_KEY установлена — пробуем запросить
     ответ у OpenAI Chat Completions (model=gpt-4o-mini). При ошибке — фолбэк.
  2) Фолбэк — локальная генерация текста по шаблонам, без интернета.
"""
from __future__ import annotations
import os
import sys
import argparse
import random
from datetime import date as date_cls

try:
    from openai import OpenAI  # новая библиотека OpenAI
except Exception:  # библиотека может быть не установлена — не критично
    OpenAI = None  # type: ignore

SIGNS = [
    "aries","taurus","gemini","cancer","leo","virgo",
    "libra","scorpio","sagittarius","capricorn","aquarius","pisces"
]

STYLES = {
    "classic": "Классический",
    "humor": "Юморной",
    "mystic": "Мистический",
    "motivation": "Мотивирующий",
}

# Локализация названий знаков (en -> отображение)
LOCALIZED_SIGNS = {
    "ru": {
        "aries": "Овен", "taurus": "Телец", "gemini": "Близнецы", "cancer": "Рак",
        "leo": "Лев", "virgo": "Дева", "libra": "Весы", "scorpio": "Скорпион",
        "sagittarius": "Стрелец", "capricorn": "Козерог", "aquarius": "Водолей", "pisces": "Рыбы"
    },
    "en": {
        "aries": "Aries", "taurus": "Taurus", "gemini": "Gemini", "cancer": "Cancer",
        "leo": "Leo", "virgo": "Virgo", "libra": "Libra", "scorpio": "Scorpio",
        "sagittarius": "Sagittarius", "capricorn": "Capricorn", "aquarius": "Aquarius", "pisces": "Pisces"
    },
    "es": {
        "aries": "Aries", "taurus": "Tauro", "gemini": "Géminis", "cancer": "Cáncer",
        "leo": "Leo", "virgo": "Virgo", "libra": "Libra", "scorpio": "Escorpio",
        "sagittarius": "Sagitario", "capricorn": "Capricornio", "aquarius": "Acuario", "pisces": "Piscis"
    },
}

# Фразы для фолбэка
FALLBACK_BITS = {
    "classic": {
        "openers": [
            "День складывается благоприятно.",
            "Звёзды на вашей стороне.",
            "Сохраняйте спокойствие — и всё получится.",
            "Есть шанс на удачное совпадение обстоятельств.",
        ],
        "advice": [
            "Не откладывайте важные звонки.",
            "Сконцентрируйтесь на одном деле, а не на десяти сразу.",
            "Слушайте интуицию — она подскажет верный ход.",
            "Договор лучше закрепить письменно.",
        ],
    },
    "humor": {
        "openers": [
            "Вселенная подмигнула вам — делайте ход!",
            "Сегодня вы — магнит для забавных случайностей.",
            "Если жизнь — кино, то у вас камер-план отличный.",
            "Гороскоп советует: улыбнитесь и притворитесь, что так и задумано.",
        ],
        "advice": [
            "Не спорьте с холодильником после полуночи.",
            "Добавьте в план дня пункт ‘кайфануть’.",
            "Шутка сегодня лишней не будет — главное, доброй.",
            "Примите комплимент: вы сегодня особенно харизматичны.",
        ],
    },
    "mystic": {
        "openers": [
            "Тонкие энергии ведут вас к нужной двери.",
            "Сны и знаки сегодня особенно выразительны.",
            "Время для тихого внутреннего выбора.",
            "Откроется то, что было скрыто в полутоне.",
        ],
        "advice": [
            "Запишите мысли — среди них промелькнёт ответ.",
            "Медленная прогулка даст быстрый инсайт.",
            "Сохраните баланс — и мир отзовётся гармонией.",
            "Обряд прост: глубокий вдох, выдох и маленький шаг вперёд.",
        ],
    },
    "motivation": {
        "openers": [
            "Сегодня — день действия.",
            "Фокус, дисциплина и маленькие победы.",
            "Вы ближе к цели, чем кажется.",
            "Сила в последовательности.",
        ],
        "advice": [
            "Разбейте задачу на три шага и сделайте первый.",
            "Скажите ‘нет’ лишнему — освободите время для важного.",
            "Отмечайте прогресс: чек-лист — лучший друг.",
            "Наградите себя за выполненное: так строится привычка.",
        ],
    },
}

LUCKY_BITS = {
    "ru": {
        "luck": ["Удача", "Поддержка", "Фортуна", "Везение"],
        "colors": ["синий", "золотой", "фиолетовый", "изумрудный", "графитовый"],
        "things": ["кружка кофе", "плейлист из 00-х", "чистый стол", "новая заметка", "короткая прогулка"],
        "labels": {"lucky": "Счастливое число", "color": "Цвет дня", "tip": "Фокус дня"}
    },
    "en": {
        "luck": ["Luck", "Support", "Fortune", "Momentum"],
        "colors": ["blue", "gold", "violet", "emerald", "graphite"],
        "things": ["a cup of coffee", "a 00s playlist", "a clean desk", "a fresh note", "a short walk"],
        "labels": {"lucky": "Lucky number", "color": "Color", "tip": "Focus"}
    },
    "es": {
        "luck": ["Suerte", "Apoyo", "Fortuna", "Impulso"],
        "colors": ["azul", "dorado", "violeta", "esmeralda", "grafito"],
        "things": ["una taza de café", "lista 2000s", "mesa ordenada", "nota nueva", "paseo corto"],
        "labels": {"lucky": "Número de la suerte", "color": "Color", "tip": "Foco"}
    },
}

STYLE_INSTRUCTIONS_EN = {
    "classic": "neutral, balanced, practical",
    "humor": "light, witty, playful but kind",
    "mystic": "poetic, intuitive, spiritual undertones",
    "motivation": "energetic, concise, action-oriented"
}

def normalize_sign(s: str) -> str:
    s = (s or "").strip().lower()
    if s not in SIGNS:
        raise ValueError(f"Unknown sign: {s}. Use one of: {', '.join(SIGNS)}")
    return s

def pick(bits: list[str]) -> str:
    return random.choice(bits)

def fallback(sign: str = "aries", style: str = "classic", lang: str = "ru", dt: str | None = None) -> str:
    """Локальная генерация гороскопа на 110–160 слов, без внешних API."""
    style = style if style in FALLBACK_BITS else "classic"
    lang = lang if lang in ("ru","en","es") else "ru"

    openers = FALLBACK_BITS[style]["openers"]
    advice = FALLBACK_BITS[style]["advice"]

    seeds = random.Random()
    lucky_number = seeds.randint(1, 99)
    loc = LUCKY_BITS[lang]

    sign_name = LOCALIZED_SIGNS.get(lang, LOCALIZED_SIGNS["ru"])[sign]

    if lang == "ru":
        date_line = f"На дату {dt}. " if dt else ""
        text = (
            f"{sign_name}. {date_line}{pick(openers)} "
            f"День подойдёт для дел, где важна аккуратность и внимание к деталям. "
            f"В первой половине суток держите темп помедленнее, ближе к вечеру появится больше свободы для манёвра. "
            f"{pick(advice)} "
            f"Личные инициативы поддержат окружающие, если вы заранее обозначите рамки и сроки. "
            f"С деньгами практичнее: выделите бюджет и проверьте мелкий шрифт. "
            f"В отношениях поможет простота: меньше предположений — больше вопросов.\n\n"
            f"{loc['labels']['lucky']}: {lucky_number}.\n"
            f"{loc['labels']['color']}: {pick(loc['colors'])}.\n"
            f"{loc['labels']['tip']}: {pick(loc['things'])}."
        )
    elif lang == "en":
        date_line = f"For {dt}. " if dt else ""
        text = (
            f"{sign_name}. {date_line}{pick(openers)} "
            f"Use measured pace early on; the evening brings more room to maneuver. "
            f"Mind the details in anything contractual or technical. "
            f"{pick(advice)} "
            f"Set clear expectations and timelines to rally support. "
            f"Be practical with money: set a budget and read the fine print. "
            f"In relationships, ask instead of guessing.\n\n"
            f"{loc['labels']['lucky']}: {lucky_number}.\n"
            f"{loc['labels']['color']}: {pick(loc['colors'])}.\n"
            f"{loc['labels']['tip']}: {pick(loc['things'])}."
        )
    else:  # es
        date_line = f"Para {dt}. " if dt else ""
        text = (
            f"{sign_name}. {date_line}{pick(openers)} "
            f"Mantén un ritmo medido por la mañana; por la tarde habrá más margen. "
            f"Cuida los detalles en lo contractual o técnico. "
            f"{pick(advice)} "
            f"Alinea expectativas y plazos para sumar apoyo. "
            f"Con el dinero, sé práctico: fija un presupuesto y lee la letra pequeña. "
            f"En las relaciones, pregunta en vez de suponer.\n\n"
            f"{loc['labels']['lucky']}: {lucky_number}.\n"
            f"{loc['labels']['color']}: {pick(loc['colors'])}.\n"
            f"{loc['labels']['tip']}: {pick(loc['things'])}."
        )

    return text

def build_openai_prompt(sign: str, style: str, lang: str, dt: str | None) -> list[dict]:
    style_en = STYLE_INSTRUCTIONS_EN.get(style, STYLE_INSTRUCTIONS_EN["classic"])
    sign_disp = LOCALIZED_SIGNS.get("en")[sign]

    sys_msg = (
        "You are Astrobot, a concise horoscope writer. "
        "Write a single-paragraph daily horoscope (110–160 words) with a clear takeaway line. "
        "No bullet points. Avoid esotericism unless style calls for it. Keep it helpful and grounded."
    )
    user_msg = (
        f"Sign: {sign_disp}. Style: {style_en}. Language: {lang}. "
        f"Date: {dt or 'today'}. Include a final short takeaway sentence."
    )
    return [
        {"role": "system", "content": sys_msg},
        {"role": "user", "content": user_msg},
    ]

def generate(sign: str, style: str = "classic", lang: str = "ru", dt: str | None = None) -> str:
    """Пробует OpenAI, при ошибке — локальный фолбэк."""
    sign = normalize_sign(sign)
    style = style if style in STYLES else "classic"
    lang = lang if lang in ("ru","en","es") else "ru"

    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("ASTROBOT_MODEL", "gpt-4o-mini")

    if api_key and OpenAI is not None:
        try:
            client = OpenAI(timeout=20.0)
            messages = build_openai_prompt(sign, style, lang, dt)
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.8,
                max_tokens=300,
            )
            txt = resp.choices[0].message.content if resp and resp.choices else None
            if txt:
                return txt.strip()
        except Exception as e:  # любая ошибка — уходим в фолбэк
            print(f"[Astrobot] OpenAI error: {e}", file=sys.stderr, flush=True)

    return fallback(sign=sign, style=style, lang=lang, dt=dt)

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Astrobot — генератор гороскопов")
    p.add_argument("--sign", type=str, help="знак зодиака (en)")
    p.add_argument("--style", type=str, default="classic", choices=list(STYLES.keys()))
    p.add_argument("--lang", type=str, default="ru", choices=["ru","en","es"])
    p.add_argument("--date", dest="dt", type=str, default=None)
    p.add_argument("--all", action="store_true", help="сгенерировать для всех знаков")
    p.add_argument("--debug", action="store_true", help="подробный лог в stderr")
    return p.parse_args()

def main() -> None:
    args = parse_args()

    def dbg(msg: str):
        if getattr(args, "debug", False):
            print(f"[Astrobot] {msg}", file=sys.stderr, flush=True)

    dbg("start main")
    dbg(f"args: sign={args.sign}, style={args.style}, lang={args.lang}, all={args.all}, date={args.dt}")

    if args.all:
        dbg("mode: ALL SIGNS")
        for s in SIGNS:
            print("="*72)
            print(LOCALIZED_SIGNS.get(args.lang, LOCALIZED_SIGNS["ru"])[s])
            print("-"*72)
            out = generate(s, style=args.style, lang=args.lang, dt=args.dt)
            print(out)
            print()
        return

    if not args.sign:
        print("Укажите --sign или используйте --all", file=sys.stderr)
        sys.exit(2)

    try:
        dbg("generating single sign…")
        text = generate(args.sign, style=args.style, lang=args.lang, dt=args.dt)
        dbg("printing result…")
        print("<<<BEGIN>>>")
        print(text, flush=True)
        print("<<<END>>>")
        dbg("done")
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

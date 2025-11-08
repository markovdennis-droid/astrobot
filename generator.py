#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import random
from typing import Optional

SIGNS = [
    "aries","taurus","gemini","cancer","leo","virgo",
    "libra","scorpio","sagittarius","capricorn","aquarius","pisces"
]
STYLES = {"classic":"Классический","humor":"Юморной","mystic":"Мистический","motivation":"Мотивирующий"}

def generate(sign: str, style: str = "classic", lang: str = "ru", dt: Optional[str] = None) -> str:
    # RU-only
    moods = ["спокойный","яркий","энергичный","вдохновляющий","таинственный","решительный"]
    tips  = ["доверьтесь интуиции","делайте по одному шагу","будьте мягкими, но твёрдыми","спросите напрямую, не угадывайте"]
    openers = {
        "classic": "День складывается благоприятно.",
        "humor": "Вселенная подмигнула — действуйте!",
        "mystic": "Сны и знаки сегодня особенно выразительны.",
        "motivation": "Сегодня — день действия."
    }
    opener = openers.get(style, openers["classic"])
    when = f"на дату {dt}" if dt else "сегодня"
    header = f"{sign.upper()} — {STYLES.get(style,'Классический')} | {when}"
    body = (
        f"{opener} Сохраните {random.choice(['фокус','баланс','спокойствие'])} и внимание к деталям. "
        f"Совет: {random.choice(tips)}. "
        f"С деньгами — практично; в отношениях — больше вопросов, меньше предположений."
    )
    lucky = f"Счастливое число: {random.randint(1,99)}."
    return f"{header}\n{body}\n\n{lucky}"


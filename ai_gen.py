import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def ai_horoscope(sign_text: str, lang: str = "ru") -> str:
    prompt = (
        f"Сделай красивый, вдохновляющий гороскоп для знака {sign_text}. "
        f"Структура: 💖 Любовь, 💼 Работа, 💰 Деньги, 🌿 Здоровье, 🎯 Совет. "
        f"Пиши по-русски, с лёгким позитивом, 6–8 предложений, без негативных формулировок."
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        temperature=0.8,
    )
    return resp.choices[0].message.content.strip()

def ai_tarot() -> str:
    prompt = (
        "Выбери одну позитивную карту Таро дня (например: Солнце, Звезда, Мир, Сила). "
        "Дай название и короткую добрую трактовку (1–3 предложения), по-русски."
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip()

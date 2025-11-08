# quotes.py — генерация/подбор цитаты без повторов
import random
from typing import Optional
from settings import OPENAI_API_KEY
from storage import init_quotes, get_quote, save_quote, recently_used_quotes

# Фолбэк-пул (разнообразный)
FALLBACK_QUOTES = [
    ("Сенека", "Не потому мы мало решаемся, что вещи трудны; вещи трудны, потому что мы мало решаемся."),
    ("Конфуций", "Пока не остановишься — неважно, как медленно ты идёшь."),
    ("Эйнштейн", "Жизнь — как езда на велосипеде: чтобы сохранить равновесие, нужно двигаться."),
    ("Лао-цзы", "Путешествие в тысячу ли начинается с одного шага."),
    ("Марк Аврелий", "Мы становимся тем, о чём думаем."),
    ("Ницше", "Кто имеет зачем жить, сможет вынести почти любое как."),
    ("Камю", "В глубине зимы я наконец узнал, что во мне непобедимое лето."),
    ("Пастернак", "Во всём хочу дойти до самой сути."),
    ("Ахматова", "И мир спасёт не красота — а доброта и сострадание."),
    ("Руми", "То, что ты ищешь, тоже ищет тебя."),
    ("Торо", "Упрощай, упрощай."),
    ("Черчилль", "Успех — это движение от неудачи к неудаче без потери энтузиазма."),
    ("Будда", "Мы — то, что мы думаем."),
    ("Стив Джобс", "Оставайтесь голодными. Оставайтесь безрассудными."),
    ("Майя Энджелоу", "Мы не забываем, как люди заставили нас чувствовать."),
]

# Инициализация OpenAI (опционально)
_client = None
if OPENAI_API_KEY:
    try:
        from openai import OpenAI
        _client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        _client = None

def _format_quote(text: str, author: Optional[str]) -> str:
    text = text.strip(" «»\"'")
    if author:
        return f"📜 Цитата дня: _{text}_ — **{author}**"
    return f"📜 Цитата дня: _{text}_"

def _ai_make_quote(sign_ru: str, date_disp: str, rng_seed: str) -> Optional[tuple]:
    """Просим модель короткую новую цитату (1 предложение) без клише."""
    if not _client:
        return None
    try:
        sys = ("Ты — куратор цитат. На русском. Придумай 1 лаконичную мотивирующую цитату (не банальную, без эмодзи), "
               "подходящую для размышления на день. Не используй известные крылатые фразы.")
        prompt = (f"Знак: {sign_ru}. Дата: {date_disp}. "
                  "Стиль: умно, без пафоса, 8–18 слов, без кавычек. "
                  "Верни строго в формате: ТЕКСТ — АВТОР. АВТОР может быть вымышленным лаконичным именем.")
        _ = rng_seed
        resp = _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":sys}, {"role":"user","content":prompt}],
            max_tokens=50, temperature=0.7
        )
        line = (resp.choices[0].message.content or "").strip()
        if "—" in line:
            text, author = [part.strip() for part in line.split("—", 1)]
        elif "-" in line:
            text, author = [part.strip() for part in line.split("-", 1)]
        else:
            text, author = line, None
        if text:
            return (text, author)
    except Exception:
        return None
    return None

def get_or_create_daily_quote(date_key: str, sign_en: Optional[str], sign_ru: str, date_disp: str) -> str:
    """Возвращает цитату для дня. Сначала кеш БД, иначе генерим (ИИ или фолбэк)
       и сохраняем. Избегаем повторов за последние 60 дней."""
    init_quotes()
    # кеш (сначала знаковая, иначе общая)
    row = get_quote(date_key, sign_en)
    if row:
        return _format_quote(row["text"], row["author"])

    used = recently_used_quotes(60)

    # ИИ-попытка
    text_author = _ai_make_quote(sign_ru, date_disp, rng_seed=f"{sign_en}|{date_key}")
    if text_author:
        text, author = text_author
        if text not in used:
            save_quote(date_key, text, author, sign_en)
            return _format_quote(text, author)

    # Фолбэк из пула
    rng = random.Random(f"quotes|{date_key}|{sign_en or 'ALL'}")
    candidates = FALLBACK_QUOTES[:]
    rng.shuffle(candidates)
    for author, text in candidates:
        if text not in used:
            save_quote(date_key, text, author, sign_en)
            return _format_quote(text, author)

    # На крайний случай — первая
    author, text = candidates[0]
    save_quote(date_key, text, author, sign_en)
    return _format_quote(text, author)


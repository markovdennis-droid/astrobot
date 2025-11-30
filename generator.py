import json
import random
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List

import pytz

BASE_DIR = Path(__file__).parent
ASTRO_STATE_FILE = BASE_DIR / "astro_state.json"

# Timezone (Spain)
TZ = pytz.timezone("Europe/Madrid")

# Внутренние имена знаков – как и раньше, по-русски
ZODIAC_SIGNS = [
    "Овен",
    "Телец",
    "Близнецы",
    "Рак",
    "Лев",
    "Дева",
    "Весы",
    "Скорпион",
    "Стрелец",
    "Козерог",
    "Водолей",
    "Рыбы",
]

SUPPORTED_LANGS = ["ru", "en", "es"]

# ------------- Phrase dictionaries -------------

PHRASES = {
    "ru": {
        "weekday": {
            "Monday": "Понедельник",
            "Tuesday": "Вторник",
            "Wednesday": "Среда",
            "Thursday": "Четверг",
            "Friday": "Пятница",
            "Saturday": "Суббота",
            "Sunday": "Воскресенье",
        },
        "labels": {
            "title": "{sign} — гороскоп на сегодня",
            "day_type": "Тип дня",
            "season_mood": "Сезонный настрой",
            "love": "Любовь",
            "work": "Работа",
            "money": "Деньги",
            "health": "Здоровье",
            "advice": "Совет",
            "number": "Число дня",
            "color": "Цвет дня",
        },
        "season": {
            "winter": [
                "Уютный день, чтобы подвести маленькие итоги.",
                "Хорошее время замедлиться и согреться чем-то приятным.",
                "День больше подходит для спокойных дел, чем для рывков.",
            ],
            "spring": [
                "День поддерживает мягкие обновления и новые идеи.",
                "Подходит, чтобы попробовать что-то небольшое, но свежее.",
                "Время увидеть, где можно аккуратно сдвинуться с места.",
            ],
            "summer": [
                "Энергичный день, но лучше не перегружать себя делами.",
                "Хороший момент добавить в расписание больше радости и света.",
                "День поддерживает живое общение и простые удовольствия.",
            ],
            "autumn": [
                "Спокойный день, чтобы навести порядок в делах и мыслях.",
                "Время мягких обновлений и тихого роста.",
                "Подходит для того, чтобы дописать, доделать и немного выдохнуть.",
            ],
        },
        "day_types": [
            "гармоничный день",
            "день небольших, но важных шагов",
            "спокойный день с мягкими возможностями",
            "день, когда лучше не спешить",
            "день, когда многое зависит от настроя",
        ],
        "love": [
            "В отношениях поможет спокойный, честный разговор.",
            "Полезно чуть мягче отнестись к недостаткам — своим и чужим.",
            "Хороший день, чтобы проявить заботу и внимательность.",
            "Небольшой знак внимания сделает чьи-то глаза теплее.",
        ],
        "work": [
            "На работе лучше двигаться шаг за шагом, без рывков.",
            "Сосредоточься на одном деле — так быстрее увидишь результат.",
            "Полезно уточнить детали и не стесняться задавать вопросы.",
            "Сделай сегодня упор на аккуратность, а не на скорость.",
        ],
        "money": [
            "Хороший момент пересмотреть подписки и регулярные траты.",
            "Подойдёт день, чтобы чуть сократить импульсивные покупки.",
            "Полезно навести порядок в расходах и планах на ближайший месяц.",
            "Лучше избегать резких финансовых решений и кредитных авантюр.",
        ],
        "health": [
            "Полезно сделать паузу для дыхания и лёгкой разминки.",
            "Подойдёт мягкая активность: прогулка, растяжка, спокойное движение.",
            "Стоит чуть бережнее отнестись к режиму сна и отдыха.",
            "Небольшой перерыв от гаджетов пойдёт на пользу голове и глазам.",
        ],
        "advice": [
            "Сделай сегодня хотя бы один небольшой шаг к тому, что давно откладываешь.",
            "Не пытайся успеть всё сразу — выбери главное.",
            "Если что-то тревожит, лучше спокойно обсудить, а не держать в себе.",
            "Найди 10–15 минут только для себя — без чувства вины.",
        ],
        "colors": [
            "янтарный",
            "изумрудный",
            "небесно-голубой",
            "терракотовый",
            "оливковый",
            "лавандовый",
            "серебристый",
            "золотистый",
        ],
    },
    "en": {
        "weekday": {
            "Monday": "Monday",
            "Tuesday": "Tuesday",
            "Wednesday": "Wednesday",
            "Thursday": "Thursday",
            "Friday": "Friday",
            "Saturday": "Saturday",
            "Sunday": "Sunday",
        },
        "labels": {
            "title": "{sign} — horoscope for today",
            "day_type": "Type of day",
            "season_mood": "Seasonal mood",
            "love": "Love",
            "work": "Work",
            "money": "Money",
            "health": "Health",
            "advice": "Advice",
            "number": "Number of the day",
            "color": "Color of the day",
        },
        "season": {
            "winter": [
                "A cozy day to sum up small results.",
                "A good time to slow down and warm yourself with something pleasant.",
                "A day better suited to calm tasks than sharp moves.",
            ],
            "spring": [
                "The day supports gentle updates and new ideas.",
                "Good moment to try something small but fresh.",
                "Time to see where you can carefully shift from the dead point.",
            ],
            "summer": [
                "Energetic day, but better not to overload yourself.",
                "A good moment to add more joy and light into the schedule.",
                "The day supports lively communication and simple pleasures.",
            ],
            "autumn": [
                "A calm day to put things and thoughts in order.",
                "Time of soft updates and quiet growth.",
                "Good to finish, polish and then exhale a little.",
            ],
        },
        "day_types": [
            "harmonious day",
            "day of small but important steps",
            "calm day with gentle opportunities",
            "day when it’s better not to rush",
            "day when a lot depends on your attitude",
        ],
        "love": [
            "A calm, honest talk will help in relationships.",
            "It’s useful to be a bit softer toward flaws — yours and others’.",
            "A good day to show care and attention.",
            "A small sign of attention can make someone’s eyes warmer.",
        ],
        "work": [
            "At work, it’s better to move step by step, without jerks.",
            "Focus on one task — you’ll see the result faster.",
            "It’s useful to clarify details and not be shy to ask questions.",
            "Today accuracy is more important than speed.",
        ],
        "money": [
            "Good moment to review subscriptions and regular expenses.",
            "Suitable day to slightly cut impulsive purchases.",
            "It’s useful to tidy up spending and plans for the next month.",
            "Better to avoid sharp financial decisions and risky credits.",
        ],
        "health": [
            "It’s useful to pause for breathing and a light stretch.",
            "Gentle activity is good: walking, stretching, calm movement.",
            "Be a bit more careful with your sleep and rest routine.",
            "A short break from gadgets will help your head and eyes.",
        ],
        "advice": [
            "Make at least one small step toward something you’ve long postponed.",
            "Don’t try to do everything at once — choose the main things.",
            "If something worries you, it’s better to calmly discuss it than keep it inside.",
            "Find 10–15 minutes just for yourself — without guilt.",
        ],
        "colors": [
            "amber",
            "emerald",
            "sky blue",
            "terracotta",
            "olive",
            "lavender",
            "silver",
            "golden",
        ],
    },
    "es": {
        "weekday": {
            "Monday": "Lunes",
            "Tuesday": "Martes",
            "Wednesday": "Miércoles",
            "Thursday": "Jueves",
            "Friday": "Viernes",
            "Saturday": "Sábado",
            "Sunday": "Domingo",
        },
        "labels": {
            "title": "{sign} — horóscopo para hoy",
            "day_type": "Tipo de día",
            "season_mood": "Ánimo de la estación",
            "love": "Amor",
            "work": "Trabajo",
            "money": "Dinero",
            "health": "Salud",
            "advice": "Consejo",
            "number": "Número del día",
            "color": "Color del día",
        },
        "season": {
            "winter": [
                "Un día acogedor para cerrar pequeños temas.",
                "Buen momento para ir más despacio y darte algo agradable.",
                "Un día más adecuado para tareas tranquilas que para grandes impulsos.",
            ],
            "spring": [
                "El día favorece renovaciones suaves e ideas nuevas.",
                "Buen momento para probar algo pequeño pero fresco.",
                "Es hora de ver dónde puedes moverte con cuidado del punto muerto.",
            ],
            "summer": [
                "Día con energía, pero mejor no sobrecargarse.",
                "Buen momento para añadir más alegría y luz a la agenda.",
                "El día favorece la comunicación viva y los placeres sencillos.",
            ],
            "autumn": [
                "Día tranquilo para poner en orden cosas y pensamientos.",
                "Tiempo de cambios suaves y crecimiento silencioso.",
                "Ideal para terminar, ajustar detalles y luego respirar hondo.",
            ],
        },
        "day_types": [
            "día armonioso",
            "día de pasos pequeños pero importantes",
            "día tranquilo con oportunidades suaves",
            "día en el que es mejor no correr",
            "día en el que mucho depende de tu actitud",
        ],
        "love": [
            "En las relaciones ayudará una conversación tranquila y sincera.",
            "Es útil ser un poco más suave con los defectos, propios y ajenos.",
            "Buen día para mostrar cuidado y atención.",
            "Un pequeño gesto de atención puede hacer los ojos de alguien más cálidos.",
        ],
        "work": [
            "En el trabajo es mejor avanzar paso a paso, sin tirones.",
            "Concéntrate en una tarea: así verás el resultado antes.",
            "Es útil aclarar detalles y no tener miedo de preguntar.",
            "Hoy es más importante la precisión que la velocidad.",
        ],
        "money": [
            "Buen momento para revisar suscripciones y gastos regulares.",
            "Día adecuado para reducir un poco las compras impulsivas.",
            "Es útil ordenar los gastos y planes del próximo mes.",
            "Mejor evitar decisiones financieras bruscas y créditos arriesgados.",
        ],
        "health": [
            "Es útil hacer una pausa para respirar y estirar un poco.",
            "Viene bien una actividad suave: paseo, estiramientos, movimiento tranquilo.",
            "Conviene cuidar un poco más el sueño y el descanso.",
            "Un pequeño descanso de las pantallas le hará bien a tu cabeza y a tus ojos.",
        ],
        "advice": [
            "Da hoy al menos un pequeño paso hacia algo que llevas posponiendo.",
            "No intentes hacerlo todo a la vez: elige lo principal.",
            "Si algo te preocupa, es mejor hablarlo con calma que guardártelo.",
            "Busca 10–15 minutos solo para ti, sin sentir culpa.",
        ],
        "colors": [
            "ámbar",
            "esmeralda",
            "azul cielo",
            "terracota",
            "oliva",
            "lavanda",
            "plateado",
            "dorado",
        ],
    },
}

NUMBERS = [1, 2, 3, 4, 5, 6, 7, 8, 9]


# -------- TAROT CARDS (language–independent ids) --------

TAROT_CARDS = [
    {
        "id": "fool",
        "image": "Шут.png",
        "title": {
            "ru": "Шут",
            "en": "The Fool",
            "es": "El Loco",
        },
        "short": {
            "ru": "новый шаг",
            "en": "a new step",
            "es": "un nuevo paso",
        },
        "meaning": {
            "ru": "Новый шаг, лёгкость, игривость. День для спонтанных, но мягких решений.",
            "en": "A new step, lightness and playfulness. A day for spontaneous but gentle decisions.",
            "es": "Nuevo paso, ligereza y juego. Día para decisiones espontáneas pero suaves.",
        },
    },
    {
        "id": "magician",
        "image": "маг.png",
        "title": {
            "ru": "Маг",
            "en": "The Magician",
            "es": "El Mago",
        },
        "short": {
            "ru": "фокус и воля",
            "en": "focus and will",
            "es": "foco y voluntad",
        },
        "meaning": {
            "ru": "Сила намерения, контроль и фокус. Хороший момент начать что-то важное.",
            "en": "Power of intention, control and focus. A good moment to start something important.",
            "es": "Fuerza de intención, control y foco. Buen momento para empezar algo importante.",
        },
    },
    {
        "id": "priestess",
        "image": "Верховная жрица.png",
        "title": {
            "ru": "Верховная жрица",
            "en": "The High Priestess",
            "es": "La Sacerdotisa",
        },
        "short": {
            "ru": "интуиция и тишина",
            "en": "intuition and silence",
            "es": "intuición y silencio",
        },
        "meaning": {
            "ru": "Интуиция, внутренний голос, мудрость. Хороший день прислушаться к себе и не спешить.",
            "en": "Intuition, inner voice and wisdom. A good day to listen to yourself and not rush.",
            "es": "Intuición, voz interior y sabiduría. Buen día para escucharte y no apresurarte.",
        },
    },
    {
        "id": "empress",
        "image": "Императрица.png",
        "title": {
            "ru": "Императрица",
            "en": "The Empress",
            "es": "La Emperatriz",
        },
        "short": {
            "ru": "забота и рост",
            "en": "care and growth",
            "es": "cuidado y crecimiento",
        },
        "meaning": {
            "ru": "Творчество, забота и рост. Отличный день для создания уюта и поддержки близких.",
            "en": "Creativity, care and growth. A great day to create comfort and support loved ones.",
            "es": "Creatividad, cuidado y crecimiento. Día ideal para crear calor y apoyar a los cercanos.",
        },
    },
    {
        "id": "emperor",
        "image": "Император.png",
        "title": {
            "ru": "Император",
            "en": "The Emperor",
            "es": "El Emperador",
        },
        "short": {
            "ru": "структура и опора",
            "en": "structure and support",
            "es": "estructura y apoyo",
        },
        "meaning": {
            "ru": "Структура, порядок, уверенность. Сделай шаг, который укрепляет тебя и твои планы.",
            "en": "Structure, order, confidence. Make a step that strengthens you and your plans.",
            "es": "Estructura, orden, confianza. Da un paso que refuerce tus planes y tu posición.",
        },
    },
    {
        "id": "hierophant",
        "image": "Иерофант.png",
        "title": {
            "ru": "Иерофант",
            "en": "The Hierophant",
            "es": "El Hierofante",
        },
        "short": {
            "ru": "опыт и традиции",
            "en": "experience and traditions",
            "es": "experiencia y tradiciones",
        },
        "meaning": {
            "ru": "Опора на знания, опыт и совет. День, чтобы учиться или делиться тем, что ты знаешь.",
            "en": "Support of knowledge, experience and advice. A day to learn or share what you know.",
            "es": "Apoyarse en el conocimiento, la experiencia y el consejo. Día para aprender o compartir.",
        },
    },
    {
        "id": "lovers",
        "image": "Влюбленные.png",
        "title": {
            "ru": "Влюблённые",
            "en": "The Lovers",
            "es": "Los Enamorados",
        },
        "short": {
            "ru": "выбор сердцем",
            "en": "choice by heart",
            "es": "elección con el corazón",
        },
        "meaning": {
            "ru": "Выбор сердцем, гармония и связь. Хороший момент уделить внимание отношениям и важным решениям.",
            "en": "Choice by heart, harmony and connection. Good moment to focus on relationships and key decisions.",
            "es": "Elección con el corazón, armonía y vínculo. Buen momento para las relaciones y decisiones importantes.",
        },
    },
    {
        "id": "chariot",
        "image": "Колесница.png",
        "title": {
            "ru": "Колесница",
            "en": "The Chariot",
            "es": "El Carro",
        },
        "short": {
            "ru": "движение вперёд",
            "en": "moving forward",
            "es": "avance hacia adelante",
        },
        "meaning": {
            "ru": "Движение вперёд, победа, контроль. Время взять ситуацию в свои руки и сделать шаг к цели.",
            "en": "Movement forward, victory, control. Time to take the situation in your hands and step toward your goal.",
            "es": "Movimiento hacia adelante, victoria y control. Es hora de tomar la situación en tus manos.",
        },
    },
    {
        "id": "strength",
        "image": "Сила.png",
        "title": {
            "ru": "Сила",
            "en": "Strength",
            "es": "La Fuerza",
        },
        "short": {
            "ru": "мягкая уверенность",
            "en": "gentle confidence",
            "es": "confianza suave",
        },
        "meaning": {
            "ru": "Мягкая сила, терпение и уверенность. Спокойная опора важнее, чем давление на себя и других.",
            "en": "Soft strength, patience and confidence. Calm support is more important than pressure.",
            "es": "Fuerza suave, paciencia y confianza. El apoyo tranquilo vale más que la presión.",
        },
    },
    {
        "id": "star",
        "image": "Звезда.png",
        "title": {
            "ru": "Звезда",
            "en": "The Star",
            "es": "La Estrella",
        },
        "short": {
            "ru": "тихая надежда",
            "en": "quiet hope",
            "es": "esperanza tranquila",
        },
        "meaning": {
            "ru": "Надежда, вдохновение, свет. Можно позволить себе помечтать и наметить добрые планы на будущее.",
            "en": "Hope, inspiration, light. You can allow yourself to dream and outline kind plans for the future.",
            "es": "Esperanza, inspiración y luz. Puedes permitirte soñar y trazar buenos planes de futuro.",
        },
    },
    {
        "id": "sun",
        "image": "Солнце.png",
        "title": {
            "ru": "Солнце",
            "en": "The Sun",
            "es": "El Sol",
        },
        "short": {
            "ru": "ясность и радость",
            "en": "clarity and joy",
            "es": "claridad y alegría",
        },
        "meaning": {
            "ru": "Успех, ясность, энергия. День поддерживает простые радости и честный взгляд на жизнь.",
            "en": "Success, clarity, energy. The day supports simple joys and an honest view of life.",
            "es": "Éxito, claridad y energía. El día favorece las alegrías sencillas y una mirada honesta.",
        },
    },
    {
        "id": "world",
        "image": "Мир.png",
        "title": {
            "ru": "Мир",
            "en": "The World",
            "es": "El Mundo",
        },
        "short": {
            "ru": "завершение и гармония",
            "en": "completion and harmony",
            "es": "cierre y armonía",
        },
        "meaning": {
            "ru": "Завершение цикла, гармония и внутренняя целостность. Хороший момент что-то закончить и выдохнуть.",
            "en": "End of a cycle, harmony and inner wholeness. A good moment to finish something and exhale.",
            "es": "Fin de ciclo, armonía e integridad interior. Buen momento para cerrar algo y respirar.",
        },
    },
    {
        "id": "hermit",
        "image": "Отшельник.png",
        "title": {
            "ru": "Отшельник",
            "en": "The Hermit",
            "es": "El Ermitaño",
        },
        "short": {
            "ru": "внутренний путь",
            "en": "inner path",
            "es": "camino interior",
        },
        "meaning": {
            "ru": "Мудрость, уединение, внутренний путь. Полезно побыть наедине с собой и спокойно всё обдумать.",
            "en": "Wisdom, solitude, inner path. It’s helpful to be alone for a while and calmly think things through.",
            "es": "Sabiduría, soledad y camino interior. Es útil estar a solas y reflexionar con calma.",
        },
    },
]

CARD_BY_ID = {c["id"]: c for c in TAROT_CARDS}


# ------------- State helpers -------------

def load_astro_state() -> Dict[str, Any]:
    if not ASTRO_STATE_FILE.exists():
        return {}
    try:
        with ASTRO_STATE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_astro_state(state: Dict[str, Any]) -> None:
    ASTRO_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with ASTRO_STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_season(now: datetime) -> str:
    m = now.month
    if m in (12, 1, 2):
        return "winter"
    if m in (3, 4, 5):
        return "spring"
    if m in (6, 7, 8):
        return "summer"
    return "autumn"


def _random_pattern(now: datetime) -> Dict[str, Any]:
    season_key = get_season(now)
    # используем длины русского набора как эталон (во всех языках одинаковое количество фраз)
    ru = PHRASES["ru"]
    season_idx = random.randrange(len(ru["season"][season_key]))
    day_type_idx = random.randrange(len(ru["day_types"]))
    love_idx = random.randrange(len(ru["love"]))
    work_idx = random.randrange(len(ru["work"]))
    money_idx = random.randrange(len(ru["money"]))
    health_idx = random.randrange(len(ru["health"]))
    advice_idx = random.randrange(len(ru["advice"]))
    color_idx = random.randrange(len(ru["colors"]))
    number = random.choice(NUMBERS)
    return {
        "season_key": season_key,
        "season_idx": season_idx,
        "day_type_idx": day_type_idx,
        "love_idx": love_idx,
        "work_idx": work_idx,
        "money_idx": money_idx,
        "health_idx": health_idx,
        "advice_idx": advice_idx,
        "color_idx": color_idx,
        "number": number,
    }


def _build_horoscope_text(sign: str, lang: str, now: datetime, pattern: Dict[str, Any]) -> str:
    if lang not in SUPPORTED_LANGS:
        lang = "ru"
    ph = PHRASES[lang]
    weekday_en = now.strftime("%A")
    weekday_local = ph["weekday"].get(weekday_en, weekday_en)
    date_str = now.strftime("%d.%m.%Y")

    labels = ph["labels"]

    season_key = pattern["season_key"]
    season_idx = pattern["season_idx"]
    day_type_idx = pattern["day_type_idx"]
    love_idx = pattern["love_idx"]
    work_idx = pattern["work_idx"]
    money_idx = pattern["money_idx"]
    health_idx = pattern["health_idx"]
    advice_idx = pattern["advice_idx"]
    color_idx = pattern["color_idx"]
    number = pattern["number"]

    season_phrase = ph["season"][season_key][season_idx]
    day_type = ph["day_types"][day_type_idx]
    love = ph["love"][love_idx]
    work = ph["work"][work_idx]
    money = ph["money"][money_idx]
    health = ph["health"][health_idx]
    advice = ph["advice"][advice_idx]
    color = ph["colors"][color_idx]

    title = labels["title"].format(sign=sign)

    lines = [
        f"✨ {title}",
        f"📅 {weekday_local}, {date_str}",
        f"🌀 {labels['day_type']}: {day_type}",
        f"🕊 {labels['season_mood']}: {season_phrase}",
        "",
        f"💖 {labels['love']}: {love}",
        f"💼 {labels['work']}: {work}",
        f"💰 {labels['money']}: {money}",
        f"🌿 {labels['health']}: {health}",
        f"🎯 {labels['advice']}: {advice}",
        f"#️⃣ {labels['number']}: {number}",
        f"🎨 {labels['color']}: {color}",
    ]
    return "\n".join(lines)


def generate(sign: str, lang: str = "ru") -> str:
    """
    Генерирует гороскоп для знака на сегодня в выбранном языке.

    Один паттерн (набор индексов фраз) на знак в день,
    текст рендерится в нужном языке из этого паттерна.
    Анти-повтор для ~14 дней по паттерну.
    """
    now = datetime.now(TZ)
    today_str = now.date().isoformat()

    state = load_astro_state()
    signs_state = state.setdefault("signs", {})
    sign_state = signs_state.setdefault(sign, {})

    today_entry = sign_state.get("today")
    if isinstance(today_entry, dict) and today_entry.get("date") == today_str:
        pattern = today_entry.get("pattern")
        if pattern:
            return _build_horoscope_text(sign, lang, now, pattern)

    history: List[Dict[str, Any]] = sign_state.get("history", [])
    recent_patterns = [h.get("pattern") for h in history[-14:] if "pattern" in h]

    pattern = None
    for _ in range(10):
        candidate = _random_pattern(now)
        if candidate not in recent_patterns:
            pattern = candidate
            break
    if pattern is None:
        pattern = _random_pattern(now)

    sign_state["today"] = {"date": today_str, "pattern": pattern}
    history.append({"date": today_str, "pattern": pattern})
    sign_state["history"] = history[-60:]
    signs_state[sign] = sign_state
    state["signs"] = signs_state
    save_astro_state(state)

    return _build_horoscope_text(sign, lang, now, pattern)


def _tarot_heading(lang: str) -> str:
    if lang == "en":
        return "Weekly Tarot card"
    if lang == "es":
        return "Carta de Tarot semanal"
    return "Еженедельная карта Таро"


def draw_tarot_for_user(user_id: int, lang: str = "ru") -> Dict[str, Any]:
    """
    Еженедельная карта Таро на пользователя.

    Возвращает:
    {
        "text": "...",
        "already_drawn": bool,
        "card_name": локализованное название,
        "image": имя файла картинки (из папки tarot_images/)
    }
    """
    if lang not in SUPPORTED_LANGS:
        lang = "ru"

    now = datetime.now(TZ)
    today = now.date()

    state = load_astro_state()
    tarot_state = state.setdefault("tarot", {})
    users_state = tarot_state.setdefault("users", {})

    key = str(user_id)
    user_entry = users_state.get(key)

    if isinstance(user_entry, dict) and "date" in user_entry and "card_id" in user_entry:
        last_date = date.fromisoformat(user_entry["date"])
        delta = (today - last_date).days
        card_id = user_entry["card_id"]
        card = CARD_BY_ID.get(card_id)
        if card and delta < 7:
            title = card["title"][lang]
            short = card["short"][lang]
            meaning = card["meaning"][lang]
            heading = _tarot_heading(lang)
            text = f"🔮 {heading}: {title}\nКлюч / Key: {short}\n\n{meaning}"
            return {
                "text": text,
                "already_drawn": True,
                "card_name": title,
                "image": card["image"],
            }

    card = random.choice(TAROT_CARDS)
    users_state[key] = {"date": today.isoformat(), "card_id": card["id"]}
    tarot_state["users"] = users_state
    state["tarot"] = tarot_state
    save_astro_state(state)

    title = card["title"][lang]
    short = card["short"][lang]
    meaning = card["meaning"][lang]
    heading = _tarot_heading(lang)
    text = f"🔮 {heading}: {title}\nКлюч / Key: {short}\n\n{meaning}"

    return {
        "text": text,
        "already_drawn": False,
        "card_name": title,
        "image": card["image"],
    }

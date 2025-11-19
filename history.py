import json
import os
import datetime

HISTORY_FILE = "astro_templates_history.json"


def _load_history() -> dict:
    """
    Загружаем историю шаблонов из JSON.
    Формат:
    {
        "♌ Лев": [
            {"id": "love_positive_1", "date": "2025-11-19"},
            ...
        ],
        "♊ Близнецы": [...],
        ...
    }
    """
    if not os.path.exists(HISTORY_FILE):
        return {}

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        # Если файл битый — игнорируем и начинаем с чистого листа
        pass

    return {}


def _save_history(data: dict) -> None:
    """Сохраняем историю шаблонов в JSON."""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_recent_template_ids(sign: str, days: int = 14) -> set:
    """
    Вернуть set ID шаблонов, которые уже использовались для знака `sign`
    за последние `days` дней.
    Одновременно чистим старые записи (старше days).
    """
    data = _load_history()
    sign_records = data.get(sign, [])

    cutoff = datetime.date.today() - datetime.timedelta(days=days)

    recent_ids = set()
    new_sign_records = []

    for item in sign_records:
        try:
            used_date = datetime.date.fromisoformat(item.get("date", ""))
        except Exception:
            # если дата битая — пропускаем
            continue

        if used_date >= cutoff:
            recent_ids.add(item.get("id"))
            new_sign_records.append(item)

    # если что-то подчистили — перезаписываем
    if len(new_sign_records) != len(sign_records):
        data[sign] = new_sign_records
        _save_history(data)

    return recent_ids


def remember_template_id(sign: str, template_id: str) -> None:
    """
    Запоминаем, что для знака `sign` сегодня был выдан шаблон `template_id`.
    Храним не больше 50 последних записей на знак, чтобы не раздувать файл.
    """
    data = _load_history()
    sign_records = data.get(sign, [])

    sign_records.append(
        {
            "id": str(template_id),
            "date": datetime.date.today().isoformat(),
        }
    )

    # ограничим историю по размеру
    data[sign] = sign_records[-50:]

    _save_history(data)

# store.py
import json, os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
from content import ZODIAC

PATH = "storage.json"

def _load() -> Dict[str, Any]:
    if not os.path.exists(PATH):
        return {"users": {}, "monthly": {}}
    with open(PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            if "users" not in data:  # защита от повреждения
                data["users"] = {}
            if "monthly" not in data:
                data["monthly"] = {}
            return data
        except Exception:
            return {"users": {}, "monthly": {}}

def _save(data: Dict[str, Any]) -> None:
    tmp = PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, PATH)

def get_user(user_id: int) -> Dict[str, Any]:
    data = _load()
    key = str(user_id)
    u = data["users"].get(key)
    if not u:
        u = {"used": [], "last_month": None, "messages": [], "profile": {}}
        data["users"][key] = u
        _save(data)
    else:
        # миграция старых записей без profile
        if "profile" not in u:
            u["profile"] = {}
            data["users"][key] = u
            _save(data)
    return u

def put_user(user_id: int, user: Dict[str, Any]) -> None:
    data = _load()
    data["users"][str(user_id)] = user
    _save(data)

# --- Анти-повтор ---

def filter_allowed(user_id: int, templates: List[Tuple[str, str]], N: int = 6, days: int = 14):
    u = get_user(user_id)
    recent = sorted(u["used"], key=lambda x: x["ts"], reverse=True)[:N]
    recent_ids = [x["id"] for x in recent]
    cutoff = datetime.utcnow() - timedelta(days=days)
    blocked_ids = set(recent_ids + [x["id"] for x in u["used"] if datetime.fromisoformat(x["ts"]) >= cutoff])
    return [t for t in templates if t[0] not in blocked_ids]

def remember_template(user_id: int, template_id: str):
    u = get_user(user_id)
    u["used"].append({"id": template_id, "ts": datetime.utcnow().isoformat(timespec="seconds")})
    if len(u["used"]) > 200:
        u["used"] = u["used"][-200:]
    put_user(user_id, u)

# --- Помесячная очистка и логи сообщений ---

def monthly_reset_messages(user_id: int):
    u = get_user(user_id)
    cur = datetime.utcnow().strftime("%Y-%m")
    if u.get("last_month") != cur:
        u["messages"] = []
        u["last_month"] = cur
        put_user(user_id, u)

def append_message(user_id: int, text: str):
    u = get_user(user_id)
    monthly_reset_messages(user_id)
    u["messages"].append({"ts": datetime.utcnow().isoformat(timespec="seconds"), "text": text[:500]})
    if len(u["messages"]) > 500:
        u["messages"] = u["messages"][-500:]
    put_user(user_id, u)

# --- Профиль пользователя: знак зодиака ---

def get_user_sign(user_id: int):
    """
    Возвращает (code, label) или (None, None), если знак не выбран.
    code: 'aries' | 'taurus' | ... ; label: '♈ Овен' и т.п.
    """
    u = get_user(user_id)
    code = u["profile"].get("sign")
    if code and code in ZODIAC:
        return code, ZODIAC[code]
    return None, None

def set_user_sign(user_id: int, code: str):
    """
    Сохраняет код знака пользователя, если он валиден.
    """
    if code not in ZODIAC:
        return False
    u = get_user(user_id)
    u["profile"]["sign"] = code
    put_user(user_id, u)
    return True

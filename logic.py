def generate_message(user_id: int, zodiac: str) -> str:
    from datetime import datetime
    import random
    from content import get_season, SEASON_TEMPLATES, HABIT_TIPS, talisman_for_month
    from store import filter_allowed, remember_template, monthly_reset_messages, append_message

    now = datetime.utcnow()
    monthly_reset_messages(user_id)

    season = get_season(now)
    # перевод сезона на русский
    season_names = {
        "spring": "весна",
        "summer": "лето",
        "autumn": "осень",
        "winter": "зима",
    }
    season_ru = season_names.get(season, season)

    seasonal_pool = SEASON_TEMPLATES.get(season, [])
    allowed = filter_allowed(user_id, seasonal_pool, N=6, days=14)
    pool = allowed if allowed else seasonal_pool
    tid, line = random.choice(pool)

    remember_template(user_id, tid)
    tip = random.choice(random.choice(list(HABIT_TIPS.values())))
    tal_name, tal_emoji, tal_mean = talisman_for_month(now)

    msg = (
        f"{zodiac}\n"
        f"Сезон: {season_ru}\n\n"
        f"{line}\n\n"
        f"🪄 Талисман месяца: {tal_emoji} {tal_name} — {tal_mean}.\n"
        f"🧩 Привычка дня: {tip}"
    )

    append_message(user_id, msg)
    return msg


from fastapi import FastAPI, Query, HTTPException
from datetime import datetime
from typing import Optional

from generator import generate, ZODIAC_SIGNS
from pytz import timezone

app = FastAPI(title="AstroBot API", version="1.0")

TZ = timezone("Europe/Madrid")  # используй тот же TZ, что и в боте


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "astrobot-api",
        "time": datetime.now(TZ).isoformat()
    }


@app.get("/horoscope")
def horoscope(
    sign: str = Query(..., description="zodiac sign key, e.g. leo"),
    lang: str = Query("ru", description="ru | en | es")
):
    sign = sign.lower()

    # проверка знака
    if sign not in ZODIAC_SIGNS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sign. Allowed: {', '.join(ZODIAC_SIGNS)}"
        )

    if lang not in ("ru", "en", "es"):
        raise HTTPException(
            status_code=400,
            detail="Invalid lang. Use ru, en or es."
        )

    try:
        text = generate(sign, lang)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Generation error: {e}"
        )

    return {
        "sign": sign,
        "lang": lang,
        "date": datetime.now(TZ).strftime("%Y-%m-%d"),
        "text": text
    }

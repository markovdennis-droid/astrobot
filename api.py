from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime

from generator import (
    generate,
    ZODIAC_SIGNS,
    SIGN_NAMES,
)

app = FastAPI(
    title="AstroBot API",
    version="1.0.0"
)

# ======================
# MODELS
# ======================

class HoroscopeResponse(BaseModel):
    sign: str
    lang: str
    date: str
    text: str


# ======================
# HEALTH
# ======================

@app.get("/health")
def health():
    return {"status": "ok"}


# ======================
# META
# ======================

@app.get("/zodiac/list")
def zodiac_list():
    return {
        "signs": ZODIAC_SIGNS,
        "names": SIGN_NAMES,
    }


# ======================
# HOROSCOPE
# ======================

@app.get("/horoscope/today", response_model=HoroscopeResponse)
def horoscope_today(sign: str, lang: str = "ru"):
    if sign not in ZODIAC_SIGNS:
        raise HTTPException(status_code=400, detail="Unknown zodiac sign")

    if lang not in SIGN_NAMES:
        raise HTTPException(status_code=400, detail="Unsupported language")

    text = generate(sign, lang)

    return HoroscopeResponse(
        sign=sign,
        lang=lang,
        date=datetime.utcnow().strftime("%Y-%m-%d"),
        text=text,
    )

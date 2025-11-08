cd ~/Desktop/astrobot
cat > bot.py <<'PY'
import logging, os
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import Update

import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("astrobot")
log.info("=== ASTROBOT v1.12 (webhook tolerant + logs) ===")

bot = Bot(settings.BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

# --- UI: инлайн кнопки со знаками
SIGNS = ["♈ Овен","♉ Телец","♊ Близнецы","♋ Рак","♌ Лев","♍ Дева",
         "♎ Весы","♏ Скорпион","♐ Стрелец","♑ Козерог","♒ Водолей","♓ Рыбы"]

def signs_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=3)
    buttons = [types.InlineKeyboardButton(text=s, callback_data=f"sign:{s}") for s in SIGNS]
    return kb.add(*buttons)

@dp.message_handler(commands=["start"])
async def cmd_start(m: types.Message):
    log.info(f"/start from {m.from_user.id}")
    await m.answer("Привет! ✨ Выбери свой знак зодиака:", reply_markup=signs_keyboard())

@dp.callback_query_handler(lambda c: c.data and c.data.startswith("sign:"))
async def on_sign(c: types.CallbackQuery):
    log.info(f"sign picked by {c.from_user.id}: {c.data}")
    sign = c.data.split(":",1)[1]
    await c.message.answer(f"Знак сохранён: <b>{sign}</b> ✅\nЗавтра пришлю гороскоп в 09:00.")
    await c.answer()

# --- AIOHTTP приложение для вебхука и health
async def handle_webhook(request: web.Request):
    # Telegram может дергать URL без тела/не-POST — отвечаем 200
    if request.method != "POST":
        return web.Response(text="OK")
    try:
        body = await request.json()
    except Exception:
        return web.Response(text="OK")

    upd_id = body.get("update_id")
    log.info(f"Incoming update: {upd_id}")

    try:
        update = Update.de_json(body)  # корректно для aiogram 2.x
        await dp.process_update(update)
    except Exception as e:
        log.exception("Update processing error: %s", e)
        # всё равно 200, чтобы Telegram не копил ошибки
        return web.Response(text="OK")

    return web.Response(text="OK")

async def handle_health(request: web.Request):
    return web.Response(text="OK")

def make_app():
    app = web.Application()
    app.router.add_post(settings.WEBHOOK_PATH, handle_webhook)
    app.router.add_get(settings.WEBHOOK_PATH, handle_webhook)  # допускаем GET
    app.router.add_get("/health", handle_health)
    return app

async def on_startup(app: web.Application):
    public_url = os.getenv("PUBLIC_URL", "").rstrip("/")
    if not public_url:
        log.warning("PUBLIC_URL пуст. Укажи через env после запуска ngrok.")
        return
    try:
        await bot.delete_webhook()
        await bot.set_webhook(
            url=public_url + settings.WEBHOOK_PATH,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"]
        )
        log.info(f"Webhook set to: {public_url + settings.WEBHOOK_PATH}")
    except Exception as e:
        log.exception("Failed to set webhook: %s", e)

async def on_cleanup(app: web.Application):
    await bot.delete_webhook()
    await dp.storage.close()
    await dp.storage.wait_closed()
    await bot.session.close()

def main():
    app = make_app()
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    web.run_app(app, host=settings.HOST, port=settings.PORT)

if __name__ == "__main__":
    main()
PY


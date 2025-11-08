import os, logging
from dotenv import load_dotenv; load_dotenv()
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN","")
bot = Bot(BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def start(m: types.Message):
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("Нажми меня", callback_data="ping"))
    await m.answer("Тест inline-кнопки:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data=="ping")
async def cb(call: types.CallbackQuery):
    await bot.answer_callback_query(call.id)  # убирает «часики»
    await call.message.answer("✅ Callback получен!")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

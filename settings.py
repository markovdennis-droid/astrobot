import os
from dotenv import load_dotenv
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
HOST = "0.0.0.0"
PORT = 8080
WEBHOOK_PATH = "/telegram/webhook"
# Для ngrok будет вида: https://<subdomain>.ngrok-free.app
PUBLIC_URL = os.getenv("PUBLIC_URL", "").rstrip("/")
assert BOT_TOKEN, "BOT_TOKEN пустой!"

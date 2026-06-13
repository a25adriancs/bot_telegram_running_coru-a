import asyncio
from telegram import Update
from telegram.ext import Application
from bot.config import TELEGRAM_TOKEN
from bot.handlers import get_handlers
from flask import Flask, request

# 1. Renombramos a 'telegram_bot' para que Vercel NO la confunda con el servidor web
telegram_bot = Application.builder().token(TELEGRAM_TOKEN).build()

# Añadimos los handlers
for handler in get_handlers():
    telegram_bot.add_handler(handler)

async def handle_webhook(update_data):
    await telegram_bot.initialize()
    update = Update.de_json(update_data, telegram_bot.bot)
    await telegram_bot.process_update(update)

# 2. ESTA es la variable que Vercel necesita encontrar en el nivel superior
app = Flask(__name__)

@app.route('/api/webhook', methods=['POST'])
def webhook():
    update_data = request.get_json()
    asyncio.run(handle_webhook(update_data))
    return 'OK'

@app.route('/')
def home():
    return 'Bot running en Vercel'
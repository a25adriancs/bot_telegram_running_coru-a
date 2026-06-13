import asyncio
from telegram import Update
from telegram.ext import Application
from bot.config import TELEGRAM_TOKEN
from bot.database import init_db
from bot.handlers import get_handlers

# Inicializamos la app fuera de la función para que sea reutilizable
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Añadimos los handlers una sola vez al cargar el módulo
for handler in get_handlers():
    application.add_handler(handler)

# Esta es la función que Vercel llamará cada vez que Telegram envíe algo
async def handle_webhook(update_data):
    await application.initialize()
    update = Update.de_json(update_data, application.bot)
    await application.process_update(update)
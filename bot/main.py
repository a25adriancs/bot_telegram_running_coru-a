import asyncio
from telegram import Update
from telegram.ext import Application
from bot.config import TELEGRAM_TOKEN
from bot.database import init_db
from bot.handlers import get_handlers
from flask import Flask, request

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
    app = Flask(__name__)

@app.route('/api/webhook', methods=['POST'])
def webhook():
    update_data = request.get_json()
    asyncio.run(handle_webhook(update_data))
    return 'OK'

@app.route('/')
def home():
    return 'Bot running'
3 — Crea vercel.json en la raíz del proyecto
json{
  "builds": [
    { "src": "bot/main.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/(.*)", "dest": "bot/main.py" }
  ]
}
app = Flask(__name__)

@app.route('/api/webhook', methods=['POST'])
def webhook():
    update_data = request.get_json()
    asyncio.run(handle_webhook(update_data))
    return 'OK'

@app.route('/')
def home():
    return 'Bot running'
3 — Crea vercel.json en la raíz del proyecto
json{
  "builds": [
    { "src": "bot/main.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/(.*)", "dest": "bot/main.py" }
  ]
}
app = Flask(__name__)

@app.route('/api/webhook', methods=['POST'])
def webhook():
    update_data = request.get_json()
    asyncio.run(handle_webhook(update_data))
    return 'OK'

@app.route('/')
def home():
    return 'Bot running'
3 — Crea vercel.json en la raíz del proyecto
json{
  "builds": [
    { "src": "bot/main.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/(.*)", "dest": "bot/main.py" }
  ]
}

app = Flask(__name__)

@app.route('/api/webhook', methods=['POST'])
def webhook():
    update_data = request.get_json()
    asyncio.run(handle_webhook(update_data))
    return 'OK'

@app.route('/')
def home():
    return 'Bot running'
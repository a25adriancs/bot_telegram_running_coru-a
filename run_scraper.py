import os
import json
import requests
import asyncio  # 1. IMPORTANTE: Importar asyncio
from bot.scrapers import scrape_all_sources

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_notification(race):
    message = (
        f"🏃 *NUEVA CARRERA DETECTADA*\n\n"
        f"📌 *{race['name']}*\n"
        f"📅 Fecha: {race['date']}\n"
        f"📍 Lugar: {race.get('location', 'N/A')}\n"
        f"🔗 [Más información]({race['registration_link']})\n"
        f"📍 Fuente: {race['source']}"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Me apunto", "callback_data": "apunto_click"},
                {"text": "❌ Paso", "callback_data": "paso_click"}
            ],
            [
                {"text": "🤔 Me lo pienso", "callback_data": "pienso_click"}
            ]
        ]
    }

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "reply_markup": json.dumps(keyboard),
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, data=payload, timeout=15)
        print(f"  Telegram -> {response.status_code}")
    except Exception as e:
        print(f"  ERROR enviando a Telegram: {e}")

def run():
    print("DEBUG: Iniciando proceso de scraping...")

    print("DEBUG: Ejecutando scrape_all_sources...")
    try:
        # 2. IMPORTANTE: Usar asyncio.run() para ejecutar la función asíncrona
        races = asyncio.run(scrape_all_sources())
    except Exception as e:
        print(f"ERROR en scraping: {e}")
        return

    print(f"DEBUG: {len(races)} carreras encontradas en total")

    for race in races:
        try:
            print(f"  📤 Enviando notificación: {race['name']}")
            send_telegram_notification(race)
        except Exception as e:
            print(f"  ERROR procesando '{race.get('name')}': {e}")

    print(f"DEBUG: Proceso terminado. {len(races)} carreras procesadas.")

if __name__ == '__main__':
    run()


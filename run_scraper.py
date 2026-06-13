import os
import json
import requests
import asyncio
import re
from bot.scrapers import scrape_all_sources

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def limpiar_nombre_callback(nombre):
    """Simplifica el nombre para que quepa en los 64 bytes de límite del callback de Telegram"""
    # Elimina caracteres especiales y lo pasa a minúsculas
    nombre_limpio = re.sub(r'[^a-zA-Z0-9\s]', '', nombre).lower().strip()
    # Reemplaza espacios por guiones y recorta para asegurar que no pase del límite
    return "-".join(nombre_limpio.split()[:4])[:40]

def send_telegram_notification(race):
    # Generamos un identificador de texto único para esta carrera
    race_slug = limpiar_nombre_callback(race['name'])

    message = (
        f"🏃 *NUEVA CARRERA DETECTADA*\n\n"
        f"📌 *{race['name']}*\n"
        f"📅 Fecha: {race['date']}\n"
        f"📍 Lugar: {race.get('location', 'N/A')}\n"
        f"🔗 [Más información]({race['registration_link']})\n"
        f"📍 Fuente: {race['source']}"
    )

    # Modificado: Ahora envía el formato 'accion_identificador' que el bot puede separar con .split("_")
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Me apunto", "callback_data": f"apunto_{race_slug}"},
                {"text": "❌ Paso", "callback_data": f"paso_{race_slug}"}
            ],
            [
                {"text": "🤔 Me lo pienso", "callback_data": f"pienso_{race_slug}"}
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
    

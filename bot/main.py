import os
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")

# --- CONEXIÓN A BASE DE DATOS (Supabase) ---
def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("La variable DATABASE_URL no está configurada.")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# --- FUNCIÓN AUXILIAR PARA ENVIAR MENSAJES ---
def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        # Forzamos a imprimir el código de estado que nos devuelve Telegram (ej: 200, 401, 400)
        print(f"DEBUG TELEGRAM RESPONSE: {response.status_code} - {response.text}", flush=True)
    except Exception as e:
        print(f"Error enviando mensaje a Telegram: {e}", flush=True)

# --- LÓGICA DE LOS COMANDOS ---
def handle_start(chat_id, user_first_name):
    welcome_text = (
        f"🏃‍♂️ ¡Bienvenido, {user_first_name}!\n\n"
        "Te ayudaré a ver las carreras de running disponibles en A Coruña y Galicia.\n\n"
        "*Comando disponible:*\n"
        "👉 /mostrar_carreras - Ver las próximas carreras guardadas"
    )
    send_telegram_message(chat_id, welcome_text)

def handle_mostrar_carreras(chat_id):
    send_telegram_message(chat_id, "🔍 Buscando las últimas carreras en la base de datos...")
    
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            query = """
                SELECT id, name, date, location, registration_link 
                FROM races 
                WHERE date::date >= CURRENT_DATE 
                ORDER BY date::date ASC 
                LIMIT 5
            """
            cursor.execute(query)
            races = cursor.fetchall()

        if not races:
            send_telegram_message(
                chat_id, 
                "🤷‍♂️ No hay carreras futuras disponibles en la base de datos ahora mismo.\n\n"
                "💡 *Nota:* Tu tabla `races` de Supabase está actualmente vacía."
            )
            return

        for race in races:
            fecha_formateada = race['date'].strftime('%d/%m/%Y') if hasattr(race['date'], 'strftime') else race['date']
            race_text = (
                f"🏁 *{race['name']}*\n"
                f"📅 Fecha: {fecha_formateada}\n"
                f"📍 Lugar: {race['location']}\n"
                f"🔗 [Más información]({race['registration_link']})"
            )
            send_telegram_message(chat_id, race_text)

    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error al consultar las carreras: {e}")
    finally:
        if connection: 
            connection.close()

# --- SERVER FLASK ---
app = Flask(__name__)

@app.route('/api/webhook', methods=['POST'])
def webhook():
    try:
        update = request.get_json()
        # Forzamos la salida inmediata al log de Vercel
        print(f"DEBUG UPDATE RECIBIDO: {update}", flush=True)
        
        if not update or "message" not in update:
            return 'OK', 200
            
        message = update["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "").strip()
        user_first_name = message["from"].get("first_name", "Corredor")

        if text.startswith("/start"):
            handle_start(chat_id, user_first_name)
        elif text.startswith("/mostrar_carreras"):
            handle_mostrar_carreras(chat_id)
        else:
            print(f"Texto recibido no es un comando válido: {text}", flush=True)
            
    except Exception as e:
        print(f"ERROR en webhook: {e}", flush=True)
        
    return 'OK', 200

@app.route('/')
def home():
    return 'Bot running successfully!'

if __name__ == '__main__':
    app.run(debug=True)

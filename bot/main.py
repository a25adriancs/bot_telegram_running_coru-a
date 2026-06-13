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
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"DEBUG TELEGRAM RESPONSE: {response.status_code}", flush=True)
    except Exception as e:
        print(f"Error enviando mensaje a Telegram: {e}", flush=True)

# --- LÓGICA DE LOS COMANDOS ---

def handle_start(chat_id, user_first_name):
    welcome_text = (
        f"🏃‍♂️ ¡Bienvenido de nuevo, {user_first_name}!\n\n"
        "<b>Comandos disponibles:</b>\n"
        "👉 /mostrar_carreras - Ver las próximas 5 carreras generales\n"
        "🔍 /buscar_carreras [Lugar] - Buscar carreras (ej: <code>/buscar_carreras Coruña</code>)\n"
        "⏱ /registrar_marca [Carrera] | [Marca] | [Año] - Guardar marca\n"
        "📋 /mis_carreras - Ver carreras a las que te has apuntado\n"
        "🤔 /pendientes - Ver carreras en 'Me lo pienso'\n"
        "📅 /carreras_proximas - Ver tus carreras más cercanas en el tiempo"
    )
    send_telegram_message(chat_id, welcome_text)

def handle_mostrar_carreras(chat_id):
    send_telegram_message(chat_id, "🔍 Buscando las últimas carreras generales...")
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            query = "SELECT id, name, date, location, registration_link FROM races WHERE date::date >= CURRENT_DATE ORDER BY date::date ASC LIMIT 5"
            cursor.execute(query)
            races = cursor.fetchall()

        if not races:
            send_telegram_message(chat_id, "🤷‍♂️ No hay carreras futuras disponibles en la base de datos.")
            return

        for race in races:
            fecha_formateada = race['date'].strftime('%d/%m/%Y') if hasattr(race['date'], 'strftime') else race['date']
            race_text = (
                f"🏁 <b>{race['name']}</b>\n"
                f"📅 Fecha: {fecha_formateada}\n"
                f"📍 Lugar: {race['location']}\n"
                f"🔗 <a href='{race['registration_link']}'>Más información</a>"
            )
            send_telegram_message(chat_id, race_text)
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error: {e}")
    finally:
        if connection: connection.close()

# 1. /buscar_carreras [Lugar]
def handle_buscar_carreras(chat_id, text_argument):
    if not text_argument:
        send_telegram_message(chat_id, "⚠️ Por favor, introduce un lugar a buscar.\nEjemplo: <code>/buscar_carreras Coruña</code>")
        return

    send_telegram_message(chat_id, f"🔎 Buscando carreras en: <b>{text_argument}</b>...")
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            query = "SELECT name, date, location, registration_link FROM races WHERE location ILIKE %s AND date::date >= CURRENT_DATE ORDER BY date::date ASC LIMIT 5"
            cursor.execute(query, (f"%{text_argument}%",))
            races = cursor.fetchall()

        if not races:
            send_telegram_message(chat_id, f"🤷‍♂️ No encontré próximas carreras en '{text_argument}'.")
            return

        for race in races:
            fecha_formateada = race['date'].strftime('%d/%m/%Y') if hasattr(race['date'], 'strftime') else race['date']
            race_text = (
                f"🏁 <b>{race['name']}</b>\n"
                f"📅 Fecha: {fecha_formateada}\n"
                f"📍 Lugar: {race['location']}\n"
                f"🔗 <a href='{race['registration_link']}'>Más información</a>"
            )
            send_telegram_message(chat_id, race_text)
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error: {e}")
    finally:
        if connection: connection.close()

# 2. /registrar_marca [Carrera] | [Marca] | [Año]
def handle_registrar_marca(chat_id, text_argument):
    if not text_argument or "|" not in text_argument:
        send_telegram_message(
            chat_id, 
            "⏱ <b>Uso correcto del comando:</b>\n"
            "<code>/registrar_marca [Nombre Carrera] | [Tu Marca] | [Año]</code>\n\n"
            "💡 <i>Ejemplo:</i> <code>/registrar_marca San Silvestre | 42:15 | 2025</code>"
        )
        return

    try:
        parts = text_argument.split("|")
        if len(parts) < 3:
            send_telegram_message(chat_id, "⚠️ Recuerda separar los 3 datos usando dos barras verticales <code>|</code>.")
            return

        carrera = parts[0].strip()
        marca = parts[1].strip()
        anio = parts[2].strip()

        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Inserta directamente en tu tabla 'personal_records' que vimos en tu captura
            query = "INSERT INTO personal_records (race_name, time, date) VALUES (%s, %s, %s)"
            cursor.execute(query, (carrera, marca, anio))
            connection.commit()

        send_telegram_message(chat_id, f"✅ <b>¡Marca guardada con éxito!</b>\n\n🏃‍♂️ Carrera: {carrera}\n⏱ Marca: {marca}\n📅 Año: {anio}")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error al guardar en personal_records: {e}")
    finally:
        if 'connection' in locals() and connection: connection.close()

# 3. /mis_carreras (Carreras con estatus 'apuntado')
def handle_mis_carreras(chat_id):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            query = """
                SELECT r.name, r.date, r.location 
                FROM races r 
                JOIN user_races ur ON r.id = ur.race_id 
                WHERE ur.status = 'apuntado' 
                ORDER BY r.date::date ASC
            """
            cursor.execute(query)
            races = cursor.fetchall()

        if not races:
            send_telegram_message(chat_id, "📋 No tienes ninguna carrera guardada como aceptada/apuntada aún.")
            return

        response = "📋 <b>Tus Carreras Guardadas:</b>\n\n"
        for race in races:
            fecha = race['date'].strftime('%d/%m/%Y') if hasattr(race['date'], 'strftime') else race['date']
            response += f"• <b>{race['name']}</b>\n  📍 {race['location']} ({fecha})\n\n"
        send_telegram_message(chat_id, response)
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error: {e}")
    finally:
        if connection: connection.close()

# 4. /pendientes (Carreras con estatus 'pienso')
def handle_pendientes(chat_id):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            query = """
                SELECT r.name, r.date 
                FROM races r 
                JOIN user_races ur ON r.id = ur.race_id 
                WHERE ur.status = 'pienso' 
                ORDER BY r.date::date ASC
            """
            cursor.execute(query)
            races = cursor.fetchall()

        if not races:
            send_telegram_message(chat_id, "🤔 No tienes carreras pendientes en la lista de 'Me lo pienso'.")
            return

        response = "🤔 <b>Carreras que te estás pensando:</b>\n\n"
        for race in races:
            fecha = race['date'].strftime('%d/%m/%Y') if hasattr(race['date'], 'strftime') else race['date']
            response += f"• {race['name']} — <i>{fecha}</i>\n"
        send_telegram_message(chat_id, response)
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error: {e}")
    finally:
        if connection: connection.close()

# 5. /carreras_proximas (Carreras apuntadas que ocurrirán pronto)
def handle_carreras_proximas(chat_id):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            query = """
                SELECT r.name, r.date, r.location 
                FROM races r 
                JOIN user_races ur ON r.id = ur.race_id 
                WHERE ur.status = 'apuntado' AND r.date::date >= CURRENT_DATE 
                ORDER BY r.date::date ASC 
                LIMIT 3
            """
            cursor.execute(query)
            races = cursor.fetchall()

        if not races:
            send_telegram_message(chat_id, "📅 No tienes próximas carreras agendadas a corto plazo.")
            return

        response = "📅 <b>Tus próximas carreras oficiales:</b>\n\n"
        for race in races:
            fecha = race['date'].strftime('%d/%m/%Y') if hasattr(race['date'], 'strftime') else race['date']
            response += f"🏃‍♂️ <b>{race['name']}</b>\n📅 {fecha} | 📍 {race['location']}\n\n"
        send_telegram_message(chat_id, response)
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error: {e}")
    finally:
        if connection: connection.close()


# --- SERVER FLASK ---
app = Flask(__name__)

@app.route('/api/webhook', methods=['POST'])
def webhook():
    try:
        update = request.get_json()
        print(f"DEBUG UPDATE RECIBIDO: {update}", flush=True)
        
        if not update or "message" not in update:
            return 'OK', 200
            
        message = update["message"]
        chat_id = message["chat"]["id"]
        text_full = message.get("text", "").strip()
        user_first_name = message["from"].get("first_name", "Corredor")

        # Separamos el comando del argumento (si es que existe)
        parts = text_full.split(" ", 1)
        command = parts[0].lower()
        argument = parts[1].strip() if len(parts) > 1 else ""

        if command.startswith("/start"):
            handle_start(chat_id, user_first_name)
        elif command.startswith("/mostrar_carreras"):
            handle_mostrar_carreras(chat_id)
        elif command.startswith("/buscar_carreras"):
            handle_buscar_carreras(chat_id, argument)
        elif command.startswith("/registrar_marca"):
            handle_registrar_marca(chat_id, argument)
        elif command.startswith("/mis_carreras"):
            handle_mis_carreras(chat_id)
        elif command.startswith("/pendientes"):
            handle_pendientes(chat_id)
        elif command.startswith("/carreras_proximas"):
            handle_carreras_proximas(chat_id)
        else:
            print(f"Texto recibido no es un comando mapeado: {text_full}", flush=True)
            
    except Exception as e:
        print(f"ERROR en webhook: {e}", flush=True)
        
    return 'OK', 200

@app.route('/')
def home():
    return 'Bot running successfully!'

if __name__ == '__main__':
    app.run(debug=True)

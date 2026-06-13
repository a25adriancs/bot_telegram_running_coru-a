import os
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request

# 🚀 AQUÍ IMPORTAS TUS SCRAPERS ACTUALES
# Ejemplo: from bot.scrapers import scraping_carreiras, scraping_atletismo
# De momento, crearemos una función simulada abajo para que veas cómo se integra.

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
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error enviando mensaje: {e}", flush=True)

# --- SIMULACIÓN DE SCRAPING EN TIEMPO REAL POR MUNICIPIO ---
def rascar_por_municipio(municipio):
    """
    Aquí conectarías la lógica de tus archivos de scraping filtrando por municipio.
    Devuelve una lista de diccionarios con las carreras encontradas en el momento.
    """
    # Esto es una simulación de lo que rascarían tus scripts en CarreirasGalegas/AtletismoGal
    resultados = [
        {
            "name": f"I Carreira Popular Concello de {municipio.title()}",
            "date": "25/10/2026",
            "location": municipio.title(),
            "link": "https://www.carreirasgalegas.com"
        }
    ]
    return resultados


# --- LÓGICA DE LOS COMANDOS ---

def handle_start(chat_id, user_first_name):
    welcome_text = (
        f"🏃‍♂️ ¡Bienvenido al panel de control, {user_first_name}!\n\n"
        "<b>📋 Gestión de Carreras Futuras:</b>\n"
        "👉 /mostrar_carreras - Ver próximas 5 carreras de la BD\n"
        "🔍 /buscar_carreras [Lugar] - Filtrar BD por localidad\n"
        "🌐 /buscar_municipio [Nombre] - Scraper en directo (CarreirasGalegas/AtletismoGal)\n\n"
        "<b>⏱ Tus Marcas e Historial:</b>\n"
        "📝 /registrar_marca [Carrera] | [Marca] | [Año] - Guardar marca\n"
        "📊 /mi_historial - Ver todas tus carreras y tiempos pasados\n"
        "🏆 /mis_records - Ver tus mejores tiempos guardados\n"
        "🗑 /borrar_marca [Nombre exacta] - Eliminar un registro\n\n"
        "<b>📅 Tu Agenda:</b>\n"
        "📋 /mis_carreras - Carreras en las que estás apuntado\n"
        "🤔 /pendientes - Lista de 'Me lo pienso'\n"
        "⏱ /carreras_proximas - Tus 3 carreras más cercanas"
    )
    send_telegram_message(chat_id, welcome_text)

# (handle_mostrar_carreras, handle_buscar_carreras, handle_mis_carreras, handle_pendientes y handle_carreras_proximas se mantienen igual que en el código anterior...)

# [NUEVO] /mi_historial
def handle_mi_historial(chat_id):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT race_name, time, date FROM personal_records ORDER BY date DESC, race_name ASC")
            records = cursor.fetchall()

        if not records:
            send_telegram_message(chat_id, "🤷‍♂️ Aún no tienes marcas registradas en tu historial. ¡Usa /registrar_marca!")
            return

        response = "📊 <b>Tu Historial de Carreras Completadas:</b>\n\n"
        for rec in records:
            response += f"🏁 <b>{rec['race_name']}</b> ({rec['date']})\n⏱ Tiempo: <code>{rec['time']}</code>\n\n"
        send_telegram_message(chat_id, response)
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error al leer el historial: {e}")
    finally:
        if connection: connection.close()

# [NUEVO] /buscar_municipio [Concello] (Scraper en Vivo)
def handle_buscar_municipio(chat_id, municipio):
    if not municipio:
        send_telegram_message(chat_id, "⚠️ Indica el municipio a rastrear. Ejemplo: <code>/buscar_municipio Arteixo</code>")
        return

    send_telegram_message(chat_id, f"⚡ Lanzando scraper en directo en Carreiras Galegas y AtletismoGal para: <b>{municipio}</b>...")
    
    try:
        # Llamamos a la función que conecta con tus archivos scraper de la carpeta bot/
        carreras_encontradas = rascar_por_municipio(municipio)
        
        if not carreras_encontradas:
            send_telegram_message(chat_id, f"🤷‍♂️ No se detectó ninguna carrera nueva hoy en las webs oficiales para '{municipio}'.")
            return

        for race in carreras_encontradas:
            text = (
                f"🏃‍♂️ <b>¡CARRERA DETECTADA EN SCRAPER VIVO!</b>\n\n"
                f"📌 <b>{race['name']}</b>\n"
                f"📅 Fecha: {race['date']}\n"
                f"📍 Lugar: {race['location']}\n"
                f"🔗 <a href='{race['link']}'>Enlace de Inscripción</a>"
            )
            send_telegram_message(chat_id, text)
    except Exception as e:
        send_telegram_message(chat_id, f"❌ El scraper ha fallado o tardó demasiado: {e}")

# [RECOMENDADO] /mis_records
def handle_mis_records(chat_id):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT race_name, time, date FROM personal_records ORDER BY time ASC LIMIT 3")
            records = cursor.fetchall()

        if not records:
            send_telegram_message(chat_id, "🤷‍♂️ No hay registros para calcular tus récords.")
            return

        response = "🏆 <b>Tus mejores marcas registradas:</b>\n\n"
        for i, rec in enumerate(records, start=1):
            response += f"{i}️⃣ <b>{rec['time']}</b> — {rec['race_name']} ({rec['date']})\n"
        send_telegram_message(chat_id, response)
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error: {e}")
    finally:
        if connection: connection.close()

# [RECOMENDADO] /borrar_marca [Nombre]
def handle_borrar_marca(chat_id, carrera_nombre):
    if not carrera_nombre:
        send_telegram_message(chat_id, "⚠️ Indica el nombre exacto de la carrera a borrar.\nEjemplo: <code>/borrar_marca San Silvestre</code>")
        return

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM personal_records WHERE race_name ILIKE %s", (carrera_nombre,))
            filas_borradas = cursor.rowcount
            connection.commit()

        if filas_borradas > 0:
            send_telegram_message(chat_id, f"🗑 ¡Registro de <b>{carrera_nombre}</b> eliminado correctamente de tu historial!")
        else:
            send_telegram_message(chat_id, f"🤷‍♂️ No encontré ninguna carrera llamada '{carrera_nombre}' en tu historial.")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error al borrar: {e}")
    finally:
        if connection: connection.close()


# --- SERVER FLASK ---
app = Flask(__name__)

@app.route('/api/webhook', methods=['POST'])
def webhook():
    try:
        update = request.get_json()
        if not update or "message" not in update:
            return 'OK', 200
            
        message = update["message"]
        chat_id = message["chat"]["id"]
        text_full = message.get("text", "").strip()
        user_first_name = message["from"].get("first_name", "Corredor")

        parts = text_full.split(" ", 1)
        command = parts[0].lower()
        argument = parts[1].strip() if len(parts) > 1 else ""

        # ENRUTADOR DE COMANDOS
        if command.startswith("/start"):
            handle_start(chat_id, user_first_name)
        elif command.startswith("/mostrar_carreras"):
            # (Tu lógica existente...)
            pass
        elif command.startswith("/buscar_carreras"):
            # (Tu lógica existente...)
            pass
        elif command.startswith("/registrar_marca"):
            # (Definido en el código anterior)
            pass
        elif command.startswith("/mi_historial"):
            handle_mi_historial(chat_id)
        elif command.startswith("/buscar_municipio"):
            handle_buscar_municipio(chat_id, argument)
        elif command.startswith("/mis_records"):
            handle_mis_records(chat_id)
        elif command.startswith("/borrar_marca"):
            handle_borrar_marca(chat_id, argument)
            
    except Exception as e:
        print(f"ERROR en webhook: {e}", flush=True)
        
    return 'OK', 200

@app.route('/')
def home():
    return 'Bot running successfully!'
    

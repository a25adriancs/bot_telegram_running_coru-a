import os
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request
from bs4 import BeautifulSoup  # <-- Añadido para el scraper rápido de atletismo.gal

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


# --- 🏃‍♂️ SCRAPER RÁPIDO EN VIVO (Solo atletismo.gal por limitaciones de Vercel) ---
def scrape_atletismo_gal_live(municipio: str):
    """Scrapea atletismo.gal en tiempo real filtrando por el municipio solicitado"""
    races = []
    url = "https://atletismo.gal/competicions/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Error en scraper vivo: {e}", flush=True)
        return races

    soup = BeautifulSoup(response.text, 'html.parser')
    articles = soup.find_all('article', class_='competition')

    for article in articles:
        # Extraer Ubicación (concello)
        location = None
        loc_div = article.find('div', class_=lambda c: c and 'basis-3/12' in c)
        if not loc_div:
            loc_div = article.find('div', class_=lambda c: c and 'basis-5/12' in c)
        if loc_div:
            location = loc_div.get_text(strip=True)

        # 🎯 FILTRAR EN VIVO: Si el municipio no coincide con lo que busca el usuario, saltamos
        if not location or municipio.lower() not in location.lower():
            continue

        # Extraer Fecha (formato DD/MM/YYYY)
        date_div = article.find('div', class_=lambda c: c and 'bg-red' in c)
        date_str = "N/A"
        if date_div:
            span = date_div.find('span')
            if span:
                date_str = span.get_text(strip=True)

        # Nombre y enlace
        h2 = article.find('h2')
        name = "Carrera sin nombre"
        link = "#"
        if h2:
            a = h2.find('a')
            if a:
                name = a.get_text(strip=True)
                link = a.get('href')

        races.append({
            'name': name,
            'date': date_str,
            'location': location,
            'registration_link': link
        })
    return races


# --- LÓGICA DE LOS COMANDOS ---

def handle_start(chat_id, user_first_name):
    welcome_text = (
        f"🏃‍♂️ ¡Bienvenido al panel de control, {user_first_name}!\n\n"
        "<b>📋 Gestión de Carreras Futuras:</b>\n"
        "👉 /mostrar_carreras - Ver próximas 5 carreras de la BD\n"
        "🔍 /buscar_carreras [Lugar] - Filtrar la BD por localidad\n"
        "🌐 /buscar_municipio [Nombre] - Buscar en vivo (Atletismo.gal + BD Carreiras)\n\n"
        "<b>⏱ Tus Marcas e Historial:</b>\n"
        "📝 /registrar_marca [Carrera] | [Marca] | [Año] - Guardar marca\n"
        "📊 /mi_historial - Ver todas tus carreras hechas y tiempos\n"
        "🏆 /mis_records - Ver tus 3 mejores marcas absolutas\n"
        "🗑 /borrar_marca [Nombre exacto] - Eliminar un registro\n\n"
        "<b>📅 Tu Agenda:</b>\n"
        "📋 /mis_carreras - Carreras a las que estás apuntado\n"
        "🤔 /pendientes - Lista de 'Me lo pienso'\n"
        "📅 /carreras_proximas - Tus próximas metas oficiales"
    )
    send_telegram_message(chat_id, welcome_text)

# [NUEVO] /buscar_municipio (Híbrido: Scraper rápido + BD para evitar bloqueos de Playwright)
def handle_buscar_municipio(chat_id, municipio):
    if not municipio:
        send_telegram_message(chat_id, "⚠️ Indica el municipio a rastrear. Ejemplo: <code>/buscar_municipio Arteixo</code>")
        return

    send_telegram_message(chat_id, f"🔎 Buscando en vivo en <b>Atletismo.gal</b> e historial de Base de Datos para: <i>{municipio}</i>...")
    
    # 1. Ejecutar el scraper rápido compatible con Vercel
    carreras_vivas = scrape_atletismo_gal_live(municipio)
    
    # 2. Buscar en la base de datos (donde cae lo de CarreirasGalegas vía tu script scraping_run)
    carreras_bd = []
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            query = "SELECT name, date, location, registration_link FROM races WHERE location ILIKE %s AND date::date >= CURRENT_DATE"
            cursor.execute(query, (f"%{municipio}%",))
            carreras_bd = cursor.fetchall()
    except Exception as e:
        print(f"Error consultando BD en comando municipio: {e}", flush=True)
    finally:
        if connection: connection.close()

    # Combinar y mostrar resultados
    encontradas = False

    if carreras_vivas:
        encontradas = True
        for race in carreras_vivas:
            text = f"🌐 <b>[En vivo - Atletismo.gal]</b>\n🏁 <b>{race['name']}</b>\n📅 Fecha: {race['date']}\n📍 Lugar: {race['location']}\n🔗 <a href='{race['registration_link']}'>Inscripción</a>"
            send_telegram_message(chat_id, text)

    if carreras_bd:
        encontradas = True
        for race in carreras_bd:
            fecha_f = race['date'].strftime('%d/%m/%Y') if hasattr(race['date'], 'strftime') else race['date']
            text = f"🗄 <b>[Base de Datos / CarreirasGalegas]</b>\n🏁 <b>{race['name']}</b>\n📅 Fecha: {fecha_f}\n📍 Lugar: {race['location']}\n🔗 <a href='{race['registration_link']}'>Inscripción</a>"
            send_telegram_message(chat_id, text)

    if not encontradas:
        send_telegram_message(chat_id, f"🤷‍♂️ No encontré eventos futuros en las webs oficiales ni en la BD para '{municipio}'.")

# [NUEVO] /mi_historial (Ver todas las carreras hechas y marcas)
def handle_mi_historial(chat_id):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT race_name, time, date FROM personal_records ORDER BY date DESC, race_name ASC")
            records = cursor.fetchall()

        if not records:
            send_telegram_message(chat_id, "🤷‍♂️ Aún no tienes marcas registradas en tu historial. ¡Usa <code>/registrar_marca</code>!")
            return

        response = "📊 <b>Tu Historial Completo de Carreras:</b>\n\n"
        for rec in records:
            response += f"🏁 <b>{rec['race_name']}</b> ({rec['date']})\n⏱ Tiempo: <code>{rec['time']}</code>\n\n"
        send_telegram_message(chat_id, response)
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error al leer el historial: {e}")
    finally:
        if connection: connection.close()

# [NUEVO] /mis_records (Ver tus mejores marcas)
def handle_mis_records(chat_id):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT race_name, time, date FROM personal_records ORDER BY time ASC LIMIT 3")
            records = cursor.fetchall()

        if not records:
            send_telegram_message(chat_id, "🤷‍♂️ No hay registros cargados para calcular tus récords.")
            return

        response = "🏆 <b>Tus Mejores Marcas (Top 3 Histórico):</b>\n\n"
        for i, rec in enumerate(records, start=1):
            response += f"{i}️⃣ <b>{rec['time']}</b> — {rec['race_name']} ({rec['date']})\n"
        send_telegram_message(chat_id, response)
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error: {e}")
    finally:
        if connection: connection.close()

# [NUEVO] /borrar_marca [Nombre]
def handle_borrar_marca(chat_id, carrera_nombre):
    if not carrera_nombre:
        send_telegram_message(chat_id, "⚠️ Indica el nombre de la carrera a borrar.\nEjemplo: <code>/borrar_marca San Silvestre</code>")
        return

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM personal_records WHERE race_name ILIKE %s", (carrera_nombre,))
            filas_borradas = cursor.rowcount
            connection.commit()

        if filas_borradas > 0:
            send_telegram_message(chat_id, f"🗑 ¡Registro de <b>{carrera_nombre}</b> eliminado correctamente!")
        else:
            send_telegram_message(chat_id, f"🤷‍♂️ No encontré ninguna carrera llamada '{carrera_nombre}' en tu historial.")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error al borrar: {e}")
    finally:
        if connection: connection.close()


# (El resto de funciones como handle_mostrar_carreras, handle_buscar_carreras, handle_mis_carreras, handle_pendientes se mantienen igual...)

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

        if command.startswith("/start"):
            handle_start(chat_id, user_first_name)
        elif command.startswith("/mostrar_carreras"):
            # Llama a tu función existente
            pass
        elif command.startswith("/buscar_carreras"):
            # Llama a tu función existente
            pass
        elif command.startswith("/registrar_marca"):
            # Llama a tu función existente
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
        

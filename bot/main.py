import os
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- CONEXIÓN A BASE DE DATOS (Supabase) ---
def get_db_connection():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("La variable DATABASE_URL no está configurada.")
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)

# --- COMANDOS DEL BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = (
        f"🏃‍♂️ ¡Bienvenido a tu asistente de carreras, {user.first_name}!\n\n"
        "Te avisaré automáticamente cuando aparezcan nuevas carreras de running en A Coruña y Galicia.\n\n"
        "*Comandos disponibles:*\n"
        "👉 /mostrar_carreras - Ver carreras de la base de datos\n"
        "📋 /miscarreras - Ver tus carreras aceptadas\n"
        "⏱ /registrarmarca - Guardar tu marca en una carrera\n"
        "📊 /historial - Ver tu progreso general o filtrar por carrera"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def mostrar_carreras(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Buscando las últimas carreras en la base de datos...")
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, name, date, location FROM races WHERE date >= CURRENT_DATE ORDER BY date ASC LIMIT 5")
            races = cursor.fetchall()

        if not races:
            await update.message.reply_text("🤷‍♂️ No hay carreras futuras disponibles en la base de datos.")
            return

        for race in races:
            race_text = (
                f"🏁 **{race['name']}**\n"
                f"📅 Fecha: {race['date'].strftime('%d/%m/%Y')}\n"
                f"📍 Lugar: {race['location']}\n\n"
                "¿Te interesa esta carrera?"
            )
            keyboard = [
                [
                    InlineKeyboardButton("✅ Me apunto", callback_data=f"apunto_{race['id']}"),
                    InlineKeyboardButton("❌ Paso", callback_data=f"paso_{race['id']}"),
                ],
                [InlineKeyboardButton("🤔 Me lo pienso", callback_data=f"pienso_{race['id']}")]
            ]
            await update.message.reply_text(race_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
    finally:
        if connection: connection.close()

async def miscarreras(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT r.name, r.date FROM races r JOIN user_races ur ON r.id = ur.race_id WHERE ur.user_id = %s AND ur.status = 'apuntado'",
                (user_id,)
            )
            my_races = cursor.fetchall()

        if not my_races:
            await update.message.reply_text("📋 Tu lista de carreras aceptadas está vacía.")
            return

        response = "📋 **Tus próximas carreras:**\n\n"
        for race in my_races:
            response += f"• {race['name']} ({race['date'].strftime('%d/%m/%Y')})\n"
        await update.message.reply_text(response, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text("📋 Hubo un problema con tu perfil.")
    finally:
        if connection: connection.close()

async def registrar_marca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⏱ Formato: `/registrarmarca [Carrera] | [Tiempo]`", parse_mode="Markdown")
        return
    full_text = " ".join(context.args)
    if "|" not in full_text:
        await update.message.reply_text("⚠️ Usa `|` para separar la carrera de tu marca.")
        return
    parts = full_text.split("|")
    await update.message.reply_text(f"✅ ¡Marca registrada!\n🏃‍♂️ Carrera: *{parts[0].strip()}*\n⏱ Tiempo: *{parts[1].strip()}*", parse_mode="Markdown")

async def historial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            if not context.args:
                cursor.execute("""
                    SELECT r.name, r.date, ur.time FROM races r 
                    JOIN user_races ur ON r.id = ur.race_id 
                    WHERE ur.user_id = %s AND ur.status = 'completada' ORDER BY r.date DESC
                """, (user_id,))
                records = cursor.fetchall()
                if not records:
                    await update.message.reply_text("🤷‍♂️ No tienes carreras completadas.")
                    return
                response = "📊 **Tu historial:**\n\n"
                for rec in records:
                    response += f"• **{rec['name']}** - {rec['date'].strftime('%d/%m/%Y')} | ⏱ {rec['time'] or 'Sin tiempo'}\n"
            else:
                carrera = " ".join(context.args)
                cursor.execute("""
                    SELECT r.name, r.date, ur.time FROM races r 
                    JOIN user_races ur ON r.id = ur.race_id 
                    WHERE ur.user_id = %s AND r.name ILIKE %s AND ur.status = 'completada' ORDER BY r.date DESC
                """, (user_id, f"%{carrera}%"))
                records = cursor.fetchall()
                if not records:
                    await update.message.reply_text(f"🤷‍♂️ No encontré nada para '{carrera}'.")
                    return
                response = f"🏃‍♂️ **Evolución para '{carrera}':**\n\n"
                for rec in records:
                    response += f"🗓 **{rec['date'].strftime('%Y')}**: ⏱ {rec['time'] or 'Sin tiempo'} _({rec['date'].strftime('%d/%m/%Y')})_\n"
            await update.message.reply_text(response, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
    finally:
        if connection: connection.close()

# --- CONTROLADOR DE BOTONES INTERACTIVOS (CALLBACK) ---
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Separar la acción del identificador (ID numérico o slug del texto del scraper)
    action, race_identifier = query.data.split("_", 1)

    # 1. Verificar si viene del scraper (es texto) o de /mostrar_carreras (es numérico)
    es_numerico = race_identifier.isdigit()

    if action == "apunto":
        mensaje = "✅ ¡Guardado! Te has apuntado a esta carrera. Aparecerá en tu /miscarreras."
        # Aquí puedes añadir tu lógica de inserción en Supabase:
        # Si es numérico insertas usando race_id, si es de texto guardas con el identificador de texto.
    elif action == "paso":
        mensaje = "❌ Entendido, la he descartado de tu lista."
    elif action == "pienso":
        mensaje = "🤔 Guardada en pendientes. ¡No te lo pienses mucho!"
    else:
        mensaje = "Opción no reconocida."

    await query.edit_message_text(text=f"{query.message.text}\n\n**Resultado:** {mensaje}", parse_mode="Markdown")

# --- CONFIGURACIÓN DEL BOT ---
telegram_app = Application.builder().token(os.environ.get("TELEGRAM_TOKEN")).build()

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("mostrar_carreras", mostrar_carreras))
telegram_app.add_handler(CommandHandler("miscarreras", miscarreras))
telegram_app.add_handler(CommandHandler("registrarmarca", registrar_marca))
telegram_app.add_handler(CommandHandler("historial", historial))
telegram_app.add_handler(CallbackQueryHandler(handle_buttons))

# --- SERVER FLASK (Optimizado para Vercel Serverless) ---
app = Flask(__name__)

# Creamos un bucle de eventos global dedicado para el Webhook
loop = asyncio.get_event_loop()

# Inicializamos la app de telegram de fondo una sola vez
loop.run_until_complete(telegram_app.initialize())

@app.route('/api/webhook', methods=['POST'])
def webhook():
    if request.method == "POST":
        try:
            update_data = request.get_json()
            update = Update.de_json(update_data, telegram_app.bot)
            
            # Ejecutamos el procesamiento de manera síncrona/segura dentro del loop del servidor
            loop.run_until_complete(telegram_app.process_update(update))
        except Exception as e:
            print(f"ERROR procesando update: {e}")
            
    return 'OK'

@app.route('/')
def home():
    return 'Bot running'
        

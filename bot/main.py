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

# --- COMANDO /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = (
        f"🏃‍♂️ ¡Bienvenido, {user.first_name}!\n\n"
        "Te ayudaré a ver las carreras de running disponibles en A Coruña y Galicia.\n\n"
        "*Comando disponible:*\n"
        "👉 /mostrar_carreras - Ver las próximas carreras guardadas"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# --- COMANDO /mostrar_carreras (Corregido para Supabase) ---
async def mostrar_carreras(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Buscando las últimas carreras en la base de datos...")
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Solución al error de tipos: Añadido '::date' para forzar la conversión de texto a fecha
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
            await update.message.reply_text("🤷‍♂️ No hay carreras futuras disponibles en la base de datos ahora mismo.")
            return

        for race in races:
            # Formateamos la fecha si viene como objeto date, o la mostramos directa si es texto
            fecha_formateada = race['date'].strftime('%d/%m/%Y') if hasattr(race['date'], 'strftime') else race['date']
            
            race_text = (
                f"🏁 **{race['name']}**\n"
                f"📅 Fecha: {fecha_formateada}\n"
                f"📍 Lugar: {race['location']}\n"
                f"🔗 [Más información]({race['registration_link']})"
            )

            # Botón simple informativo ya que no guardamos datos de usuarios
            keyboard = [[InlineKeyboardButton("🔗 Ir a la web", url=race['registration_link'])]]
            
            await update.message.reply_text(
                race_text, 
                reply_markup=InlineKeyboardMarkup(keyboard), 
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error al consultar las carreras: {e}")
    finally:
        if connection: 
            connection.close()

# --- CONFIGURACIÓN DEL BOT ---
telegram_app = Application.builder().token(os.environ.get("TELEGRAM_TOKEN")).build()

# Registramos solo los comandos que realmente vas a usar
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("mostrar_carreras", mostrar_carreras))

# --- SERVER FLASK (Vercel Serverless) ---
app = Flask(__name__)

loop = asyncio.get_event_loop()
loop.run_until_complete(telegram_app.initialize())

@app.route('/api/webhook', methods=['POST'])
def webhook():
    if request.method == "POST":
        try:
            update_data = request.get_json()
            update = Update.de_json(update_data, telegram_app.bot)
            loop.run_until_complete(telegram_app.process_update(update))
        except Exception as e:
            print(f"ERROR procesando update: {e}")
            
    return 'OK'

@app.route('/')
def home():
    return 'Bot running'
            

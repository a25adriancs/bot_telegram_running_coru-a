import os
import asyncio
import pymysql
from urllib.parse import urlparse
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- CONEXIÓN A BASE DE DATOS (Adaptada a tu DATABASE_URL) ---
def get_db_connection():
    db_url = os.environ.get("DATABASE_URL")

    if db_url:
        url = urlparse(db_url)
        return pymysql.connect(
            host=url.hostname,
            port=url.port or 3306,
            user=url.username,
            password=url.password,
            database=url.path[1:],
            ssl_verify_identity=True,
            cursorclass=pymysql.cursors.DictCursor
        )
    else:
        return pymysql.connect(
            host=os.environ.get("DB_HOST"),
            user=os.environ.get("DB_USER"),
            password=os.environ.get("DB_PASSWORD"),
            database=os.environ.get("DB_NAME"),
            ssl_verify_identity=True,
            cursorclass=pymysql.cursors.DictCursor
        )

# --- COMANDO /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = (
        f"🏃‍♂️ ¡Bienvenido a tu asistente de carreras, {user.first_name}!\n\n"
        "Te avisaré automáticamente cuando aparezcan nuevas carreras de running en A Coruña y Galicia.\n\n"
        "**Comandos disponibles:**\n"
        "👉 /mostrar_carreras - Ver carreras de la base de datos\n"
        "📋 /miscarreras - Ver tus carreras aceptadas\n"
        "⏱ /registrarmarca - Guardar tu marca en una carrera\n"
        "📊 /historial - Ver tu progreso general o filtrar por carrera"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# --- COMANDO /mostrar_carreras ---
async def mostrar_carreras(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Buscando las últimas carreras en la base de datos...")

    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, name, date, location FROM races WHERE date >= CURDATE() ORDER BY date ASC LIMIT 5")
            races = cursor.fetchall()

        if not races:
            await update.message.reply_text("🤷‍♂️ No hay carreras futuras disponibles en la base de datos ahora mismo.")
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
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(race_text, reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Error al consultar las carreras: {e}")
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()

# --- COMANDO /miscarreras ---
async def miscarreras(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT r.name, r.date FROM races r JOIN user_races ur ON r.id = ur.race_id WHERE ur.user_id = %s AND ur.status = 'apuntado'",
                (user_id,)
            )
            my_races = cursor.fetchall()

        if not my_races:
            await update.message.reply_text(
                "📋 Tu lista de carreras aceptadas está vacía.\n\n"
                "Usa /mostrar_carreras y pulsa en **✅ Me apunto**."
            )
            return

        response = "📋 **Tus próximas carreras:**\n\n"
        for race in my_races:
            response += f"• {race['name']} ({race['date'].strftime('%d/%m/%Y')})\n"
        await update.message.reply_text(response, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text("📋 Todavía no tienes carreras registradas o hubo un problema con tu perfil.")
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()

# --- COMANDO /registrarmarca ---
async def registrar_marca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⏱ **Uso del comando registrar marca:**\n"
            "Formato: `/registrarmarca [Nombre de Carrera] | [Tu tiempo]`\n\n"
            "💡 _Ejemplo:_ `/registrarmarca San Silvestre | 45:20`",
            parse_mode="Markdown"
        )
        return

    full_text = " ".join(context.args)
    if "|" not in full_text:
        await update.message.reply_text("⚠️ Recuerda usar la barra vertical `|` para separar el nombre de la carrera de tu marca.")
        return

    parts = full_text.split("|")
    carrera = parts[0].strip()
    tiempo = parts[1].strip()

    await update.message.reply_text(f"✅ ¡Marca registrada con éxito!\n🏃‍♂️ Carrera: *{carrera}*\n⏱ Tiempo: *{tiempo}*", parse_mode="Markdown")

# --- COMANDO /historial ---
async def historial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:

            if not context.args:
                await update.message.reply_text("📊 Buscando tu historial completo de carreras...")
                query = """
                    SELECT r.name, r.date, ur.time
                    FROM races r
                    JOIN user_races ur ON r.id = ur.race_id
                    WHERE ur.user_id = %s AND ur.status = 'completada'
                    ORDER BY r.date DESC
                """
                cursor.execute(query, (user_id,))
                records = cursor.fetchall()

                if not records:
                    await update.message.reply_text("🤷‍♂️ Aún no tienes ninguna carrera registrada como completada.")
                    return

                response = "📊 **Tu historial completo de carreras:**\n\n"
                for rec in records:
                    fecha = rec['date'].strftime('%d/%m/%Y')
                    tiempo = rec['time'] if rec['time'] else "Sin tiempo"
                    response += f"• **{rec['name']}** - {fecha} | ⏱ {tiempo}\n"

            else:
                carrera_buscada = " ".join(context.args)
                await update.message.reply_text(f"🔎 Buscando marcas históricas para: *{carrera_buscada}*...", parse_mode="Markdown")

                query = """
                    SELECT r.name, r.date, ur.time
                    FROM races r
                    JOIN user_races ur ON r.id = ur.race_id
                    WHERE ur.user_id = %s AND r.name LIKE %s AND ur.status = 'completada'
                    ORDER BY r.date DESC
                """
                cursor.execute(query, (user_id, f"%{carrera_buscada}%"))
                records = cursor.fetchall()

                if not records:
                    await update.message.reply_text(f"🤷‍♂️ No se encontró ninguna carrera coincidente con '{carrera_buscada}'.")
                    return

                response = f"🏃‍♂️ **Evolución por años para '{carrera_buscada}':**\n\n"
                for rec in records:
                    año = rec['date'].strftime('%Y')
                    fecha = rec['date'].strftime('%d/%m/%Y')
                    tiempo = rec['time'] if rec['time'] else "Sin tiempo"
                    response += f"🗓 **{año}**: ⏱ {tiempo} _({fecha})_\n"

            await update.message.reply_text(response, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Error al consultar el historial: {e}")
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()

# --- CONTROLADOR DE BOTONES INTERACTIVOS (CALLBACK) ---
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, race_id = query.data.split("_")

    if action == "apunto":
        mensaje = "✅ ¡Guardado! Te has apuntado a esta carrera. Aparecerá en tu /miscarreras."
    elif action == "paso":
        mensaje = "❌ Entendido, la he descartado de tu lista."
    elif action == "pienso":
        mensaje = "🤔 Guardada en pendientes. ¡No te lo pienses mucho!"

    await query.edit_message_text(text=f"{query.message.text}\n\n**Resultado:** {mensaje}", parse_mode="Markdown")

# --- INSTANCIA GLOBAL Y CONFIGURACIÓN DEL BOT DE TELEGRAM ---
telegram_app = Application.builder().token(os.environ.get("TELEGRAM_TOKEN")).build()

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("mostrar_carreras", mostrar_carreras))
telegram_app.add_handler(CommandHandler("miscarreras", miscarreras))
telegram_app.add_handler(CommandHandler("registrarmarca", registrar_marca))
telegram_app.add_handler(CommandHandler("historial", historial))
telegram_app.add_handler(CallbackQueryHandler(handle_buttons))


async def handle_webhook(update_data):
    await telegram_app.initialize()
    update = Update.de_json(update_data, telegram_app.bot)
    await telegram_app.process_update(update)


# --- APP WEB (Flask) - Lo que Vercel ejecuta ---
app = Flask(__name__)

@app.route('/api/webhook', methods=['POST'])
def webhook():
    asyncio.run(handle_webhook(request.get_json()))
    return 'OK'

@app.route('/')
def home():
    return 'Bot running'

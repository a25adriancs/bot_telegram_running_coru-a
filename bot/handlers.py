from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler
from bot.database import (
    add_race, race_exists, set_user_race_status, get_user_race_status,
    get_race_by_id, add_pending_reminder
)
from bot.config import TELEGRAM_CHAT_ID
from telegram.constants import ParseMode
from datetime import datetime, timedelta
import re
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# 🛡️ EL PORTERO DE DISCOTECA (Decorador de seguridad)
def restricted(func):
    """Restringe el uso del bot únicamente a tu ID de Telegram."""
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if str(user_id) != str(TELEGRAM_CHAT_ID):
            logger.warning(f"Acceso denegado al usuario {user_id}.")
            return # Ignora el mensaje silenciosamente
        return await func(update, context, *args, **kwargs)
    return wrapped

async def send_race_notification(race_data: dict, context: ContextTypes.DEFAULT_TYPE):
    """Envía una notificación de nueva carrera con botones inline."""
    chat_id = TELEGRAM_CHAT_ID
    
    message = (
        f"🏃 <b>NUEVA CARRERA DETECTADA</b>\n\n"
        f"📌 <b>{race_data['name']}</b>\n"
        f"📅 Fecha: {race_data['date']}\n"
        f"📍 Lugar: {race_data.get('location', 'N/A')}\n"
        f"🔗 <a href='{race_data['registration_link']}'>Más información</a>\n"
        f"📍 Fuente: {race_data['source']}"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Me apunto", callback_data=f"accept_{race_data['race_id']}"),
            InlineKeyboardButton("❌ Paso", callback_data=f"reject_{race_data['race_id']}")
        ],
        [
            InlineKeyboardButton("🤔 Me lo pienso", callback_data=f"pending_{race_data['race_id']}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )

@restricted # Protegemos el callback
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los callbacks de los botones inline de forma robusta."""
    query = update.callback_query
    # Respondemos SIEMPRE a Telegram lo antes posible para que no se quede el relojito cargando
    await query.answer()
    
    try:
        action, race_id = query.data.split('_')
        race_id = int(race_id)
        
        race = get_race_by_id(race_id)
        if not race:
            await query.edit_message_text("❌ <i>Esta carrera ya no está disponible en la base de datos.</i>", parse_mode=ParseMode.HTML)
            return
        
        if action == 'accept':
            set_user_race_status(race_id, 'accepted')
            message = (
                f"✅ *¡Te has apuntado!*\n\n"
                f"📌 {race['name']}\n"
                f"📅 {race['date']}\n\n"
                f"🔗 [Inscripción directa]({race['registration_link']})\n\n"
                f"Te recordaré 3 días antes de la carrera."
            )
            await query.edit_message_text(message, parse_mode='Markdown')
        
        elif action == 'reject':
            set_user_race_status(race_id, 'rejected')
            message = f"❌ *No te avisaré más de esta carrera*\n\n📌 {race['name']}"
            await query.edit_message_text(message, parse_mode='Markdown')
        
        elif action == 'pending':
            set_user_race_status(race_id, 'pending')
            reminder_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            add_pending_reminder(race_id, reminder_date)
            message = (
                f"🤔 *Te lo pensarás*\n\n"
                f"📌 {race['name']}\n"
                f"📅 {race['date']}\n\n"
                f"Te recordaré en 7 días."
            )
            await query.edit_message_text(message, parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error procesando callback: {e}")
        await query.edit_message_text("⚠️ Hubo un error al procesar tu respuesta.")

@restricted # Protegemos el comando
async def miscorreras_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra las carreras que el usuario ha aceptado."""
    from bot.database import get_accepted_races
    
    races = get_accepted_races()
    
    if not races:
        message = "📭 *No tienes carreras aceptadas*\n\nUsa los botones cuando te avise de una nueva carrera para añadirla."
        await update.message.reply_text(message, parse_mode='Markdown')
        return
    
    message = "🏃 *MIS CARRERAS*\n\n"
    for race in races:
        message += (
            f"📌 *{race['name']}*\n"
            f"📅 {race['date']}\n"
            f"📏 {race['distance'] or 'N/A'}\n"
            f"💰 {race['price'] or 'N/A'}\n"
            f"🔗 [Inscripción]({race['registration_link']})\n\n"
        )
    await update.message.reply_text(message, parse_mode='Markdown', disable_web_page_preview=True)

@restricted # Protegemos el comando
async def registrarmarca_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Registra una marca personal: /registrarmarca [nombre] [tiempo] [fecha]"""
    from bot.database import add_personal_record
    
    if len(context.args) < 3:
        message = (
            "❌ *Uso incorrecto*\n\n"
            "Formato: `/registrarmarca [nombre carrera] [tiempo] [fecha]`\n\n"
            "Ejemplo: `/registrarmarca San Silvestre 45:30 31/12/2024`\n\n"
            "Formato tiempo: MM:SS o HH:MM:SS\n"
            "Formato fecha: DD/MM/YYYY"
        )
        await update.message.reply_text(message, parse_mode='Markdown')
        return
    
    race_name = context.args[0]
    time = context.args[1]
    date_str = context.args[2]
    
    try:
        parts = date_str.split('/')
        if len(parts) == 3:
            date = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
        else:
            raise ValueError
    except:
        message = "❌ *Formato de fecha incorrecto*\n\nUsa DD/MM/YYYY"
        await update.message.reply_text(message, parse_mode='Markdown')
        return
    
    if not re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', time):
        message = "❌ *Formato de tiempo incorrecto*\n\nUsa MM:SS o HH:MM:SS"
        await update.message.reply_text(message, parse_mode='Markdown')
        return
    
    add_personal_record(race_name, time, date)
    
    message = (
        f"✅ *Marca guardada*\n\n"
        f"📌 {race_name}\n"
        f"⏱️ {time}\n"
        f"📅 {date_str}"
    )
    await update.message.reply_text(message, parse_mode='Markdown')

@restricted # Protegemos el comando
async def historial_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el historial de marcas de una carrera: /historial [nombre carrera]"""
    from bot.database import get_personal_records
    
    if not context.args:
        message = (
            "❌ *Uso incorrecto*\n\n"
            "Formato: `/historial [nombre carrera]`\n\n"
            "Ejemplo: `/historial San Silvestre`"
        )
        await update.message.reply_text(message, parse_mode='Markdown')
        return
    
    race_name = ' '.join(context.args)
    records = get_personal_records(race_name)
    
    if not records:
        message = f"📭 *No hay marcas para* {race_name}"
        await update.message.reply_text(message, parse_mode='Markdown')
        return
    
    records_sorted = sorted(records, key=lambda x: x['date'])
    message = f"📊 *HISTORIAL: {race_name}*\n\n"
    
    previous_time = None
    for i, record in enumerate(records_sorted):
        year = record['date'][:4]
        time = record['time']
        
        comparison = ""
        if previous_time:
            comparison = compare_times(previous_time, time)
        
        message += f"📅 {year}: ⏱️ {time} {comparison}\n"
        previous_time = time
    
    best_record = min(records_sorted, key=lambda x: time_to_seconds(x['time']))
    message += f"\n🏆 *Mejor marca*: {best_record['time']} ({best_record['date'][:4]})"
    
    await update.message.reply_text(message, parse_mode='Markdown')

def compare_times(time1: str, time2: str) -> str:
    seconds1 = time_to_seconds(time1)
    seconds2 = time_to_seconds(time2)
    diff = abs(seconds2 - seconds1)
    diff_str = seconds_to_time(diff)
    
    if seconds2 < seconds1:
        return f"📈 (-{diff_str})"
    elif seconds2 > seconds1:
        return f"📉 (+{diff_str})"
    else:
        return "➡️ (=)"

def time_to_seconds(time_str: str) -> int:
    parts = time_str.split(':')
    if len(parts) == 2:
        minutes, seconds = map(int, parts)
        return minutes * 60 + seconds
    elif len(parts) == 3:
        hours, minutes, seconds = map(int, parts)
        return hours * 3600 + minutes * 60 + seconds
    return 0

def seconds_to_time(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"

@restricted # Protegemos el comando start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mensaje de bienvenida al iniciar el bot."""
    message = (
        "🏃 *¡Bienvenido a tu asistente de carreras!*\n\n"
        "Te avisaré automáticamente cuando aparezcan nuevas carreras de running "
        "en A Coruña y Galicia.\n\n"
        "*Comandos disponibles:*\n"
        "📋 /miscorreras - Ver tus carreras aceptadas\n"
        "⏱️ /registrarmarca [carrera] [tiempo] [fecha] - Guardar tu marca\n"
        "📊 /historial [carrera] - Ver tu progreso por años\n\n"
        "Cuando detecte una carrera nueva, te dejaré elegir entre:\n"
        "✅ Me apunto | ❌ Paso | 🤔 Me lo pienso"
    )
    await update.message.reply_text(message, parse_mode='Markdown')

def get_handlers():
    """Devuelve la lista de handlers para el bot."""
    return [
        CommandHandler('start', start_command),
        CallbackQueryHandler(button_callback, pattern='^(accept|reject|pending)_'),
        CommandHandler('miscorreras', miscorreras_command),
        CommandHandler('registrarmarca', registrarmarca_command),
        CommandHandler('historial', historial_command),
    ]
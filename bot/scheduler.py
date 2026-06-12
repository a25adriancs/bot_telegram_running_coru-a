from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram.constants import ParseMode
from bot.scrapers import scrape_all_sources
from bot.database import (
    race_exists, add_race, get_user_race_status,
    get_pending_reminders, mark_reminder_sent,
    get_races_needing_reminder, mark_reminder_sent_for_race,
    get_race_by_id
)
from bot.handlers import send_race_notification
from bot.config import TELEGRAM_CHAT_ID
from telegram import Bot
import asyncio

scheduler = AsyncIOScheduler()

async def daily_scraping_job(context):
    """Job diario de scraping para encontrar carreras nuevas."""
    print(f"[{asyncio.get_event_loop().time()}] Iniciando scraping diario...")
    
    races = scrape_all_sources()
    new_races_count = 0
    
    for race in races:
        # Verificar si la carrera ya existe
        if not race_exists(race['name'], race['date'], race['registration_link']):
            # Añadir a la base de datos
            race_id = add_race(
                race['name'],
                race['date'],
                race['distance'],
                race['price'],
                race['registration_link'],
                race['source'],
                race.get('location', 'N/A')
            )
            # Añadir race_id al diccionario para la notificación
            race['race_id'] = race_id
            
            # Verificar si el usuario ya ha rechazado esta carrera
            user_status = get_user_race_status(race_id)
            if user_status != 'rejected':
                # Enviar notificación
                await send_race_notification(race, context)
                new_races_count += 1
                print(f"  Nueva carrera: {race['name']} - {race['date']}")
    
    print(f"Scraping completado. {new_races_count} carreras nuevas encontradas.")

async def pending_reminders_job(context):
    """Job para enviar recordatorios de carreras en 'me lo pienso'."""
    print(f"[{asyncio.get_event_loop().time()}] Verificando recordatorios pendientes...")
    
    reminders = get_pending_reminders()
    
    for reminder in reminders:
        try:
            # Enviar recordatorio
            bot = context.bot
            chat_id = TELEGRAM_CHAT_ID
            
            message = (
                f"🤔 *¿Te lo has pensado?*\n\n"
                f"📌 *{reminder['name']}*\n"
                f"📅 {reminder['date']}\n"
                f"🔗 [Inscripción]({reminder['registration_link']})\n\n"
                f"¿Te apuntas o pasas?"
            )
            
            from bot.handlers import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [
                [
                    InlineKeyboardButton("✅ Me apunto", callback_data=f"accept_{reminder['race_id']}"),
                    InlineKeyboardButton("❌ Paso", callback_data=f"reject_{reminder['race_id']}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='Markdown',
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
            
            # Marcar como enviado
            mark_reminder_sent(reminder['id'])
            print(f"  Recordatorio enviado: {reminder['name']}")

            scheduler.add_job(
    pending_reminders_job,
    trigger=CronTrigger(minute=0),
    id='pending_reminders',
    name='Recordatorios "me lo pienso"',
    replace_existing=True,
    args=[application]
)
            
        except Exception as e:
            print(f"  Error enviando recordatorio: {e}")

async def race_reminder_job(context):
    """Job para enviar recordatorios 3 días antes de carreras aceptadas."""
    print(f"[{asyncio.get_event_loop().time()}] Verificando carreras próximas...")
    
    races = get_races_needing_reminder(days_before=3)
    
    for race in races:
        try:
            bot = context.bot
            chat_id = TELEGRAM_CHAT_ID
            
            message = (
                f"⏰ *RECORDATORIO*\n\n"
                f"📌 *{race['name']}*\n"
                f"📅 {race['date']} (en 3 días)\n"
                f"📏 {race['distance'] or 'N/A'}\n"
                f"🔗 [Inscripción]({race['registration_link']})\n\n"
                f"¡No te olvides de inscribirte!"
            )
            
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            # Marcar recordatorio como enviado
            mark_reminder_sent_for_race(race['id'])
            print(f"  Recordatorio enviado: {race['name']}")
            
        except Exception as e:
            print(f"  Error enviando recordatorio: {e}")

def setup_scheduler(application):
    """Configura y arranca el scheduler con todos los jobs."""
    # Job de scraping diario a las 9:00 AM
    scheduler.add_job(
        daily_scraping_job,
        trigger=CronTrigger(hour=9, minute=0),
        id='daily_scraping',
        name='Scraping diario de carreras',
        replace_existing=True,
        args=[application]
    )
    
    # Job de recordatorios pendientes cada hora
    scheduler.add_job(
        pending_reminders_job,
        trigger=CronTrigger(minute=0),
        id='pending_reminders',
        name='Recordatorios "me lo pienso"',
        replace_existing=True,
        args=[application]
    )
    
    # Job de recordatorios de carreras cada día a las 8:00 AM
    scheduler.add_job(
        race_reminder_job,
        trigger=CronTrigger(hour=8, minute=0),
        id='race_reminders',
        name='Recordatorios 3 días antes',
        replace_existing=True,
        args=[application]
    )
    
    scheduler.start()
    print("Scheduler iniciado con jobs:")
    print("  - Scraping diario: 09:00")
    print("  - Recordatorios pendientes: cada hora")
    print("  - Recordatorios carreras: 08:00")

def shutdown_scheduler():
    """Detiene el scheduler."""
    scheduler.shutdown()
    print("Scheduler detenido")

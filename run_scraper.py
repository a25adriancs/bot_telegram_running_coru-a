import sys
import os
# Añade el directorio actual al path de búsqueda de módulos
sys.path.append(os.getcwd())
import asyncio
from bot.config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
from bot.database import init_db, race_exists, add_race
from bot.scrapers import scrape_all_sources
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

async def main():
    print("Iniciando trabajo de scraping en GitHub Actions...")
    
    # Asegurarnos de que las tablas existen en PostgreSQL
    init_db()
    
    bot = Bot(token=TELEGRAM_TOKEN)
    races = await scrape_all_sources()
    new_races_count = 0
    
    for race in races:
        if not race_exists(race['name'], race['date'], race['registration_link']):
            # 1. Añadir a la base de datos
            race_id = add_race(
                race['name'], race['date'], race['distance'],
                race['price'], race['registration_link'],
                race['source'], race.get('location', 'N/A')
            )
            
            # 2. Construir y enviar el mensaje directamente
            if race_id:
                message = (
                    f"🏃 <b>NUEVA CARRERA DETECTADA</b>\n\n"
                    f"📌 <b>{race['name']}</b>\n"
                    f"📅 Fecha: {race['date']}\n"
                    f"📍 Lugar: {race.get('location', 'N/A')}\n"
                    f"🔗 <a href='{race['registration_link']}'>Más información</a>\n"
                    f"📍 Fuente: {race['source']}"
                )
                
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Me apunto", callback_data=f"accept_{race_id}"),
                        InlineKeyboardButton("❌ Paso", callback_data=f"reject_{race_id}")
                    ],
                    [InlineKeyboardButton("🤔 Me lo pienso", callback_data=f"pending_{race_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                try:
                    await bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text=message,
                        parse_mode=ParseMode.HTML,
                        reply_markup=reply_markup,
                        disable_web_page_preview=True
                    )
                    new_races_count += 1
                    print(f"  Nueva carrera enviada: {race['name']}")
                except Exception as e:
                    print(f"Error enviando mensaje a Telegram: {e}")

    print(f"Scraping completado. {new_races_count} carreras nuevas enviadas.")

if __name__ == '__main__':
    asyncio.run(main())
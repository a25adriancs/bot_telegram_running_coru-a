import asyncio
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from bot.scrapers import scrape_all_sources
from bot.database import init_db, race_exists, add_race
from bot.config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID


async def main():
    init_db()

    print("Scrapeando carreras...")
    races = scrape_all_sources()
    print(f"Encontradas {len(races)} carreras de A Coruña\n")

    bot = Bot(token=TELEGRAM_TOKEN)

    for race in races:
        # Guardar en base de datos (si no existe ya)
        race_id = add_race(
            race['name'],
            race['date'],
            race['distance'],
            race['price'],
            race['registration_link'],
            race['source'],
            race.get('location', 'N/A')
        )

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
            [
                InlineKeyboardButton("🤔 Me lo pienso", callback_data=f"pending_{race_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )

        print(f"Enviado: {race['name']}")

    print("\n¡Listo!")


if __name__ == '__main__':
    asyncio.run(main())
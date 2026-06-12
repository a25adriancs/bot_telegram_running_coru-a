import asyncio
from telegram.ext import Application
from bot.config import TELEGRAM_TOKEN
from bot.database import init_db
from bot.handlers import get_handlers
from bot.scheduler import setup_scheduler, shutdown_scheduler

async def main():
    """Función principal del bot."""
    # Inicializar base de datos
    print("Inicializando base de datos...")
    init_db()
    print("Base de datos inicializada.")
    
    # Crear aplicación de Telegram
    print("Iniciando bot de Telegram...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Añadir handlers
    for handler in get_handlers():
        application.add_handler(handler)
    
    # Configurar scheduler
    setup_scheduler(application)
    
    # Iniciar bot
    print("Bot iniciado. Presiona Ctrl+C para detener.")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    try:
        # Mantener el bot corriendo
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\nDeteniendo bot...")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        shutdown_scheduler()
        print("Bot detenido.")

if __name__ == '__main__':
    asyncio.run(main())

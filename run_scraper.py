import sys
import os
import asyncio
from  bot.scrapers import scrape_all_sources
from bot.database import init_db

async def run():
    print("DEBUG: Iniciando proceso de scraping...")
    
    # 1. Inicializar BD
    try:
        init_db()
        print("DEBUG: Base de datos conectada.")
    except Exception as e:
        print(f"ERROR conectando a BD: {e}")
        return

    # 2. Ejecutar Scraper
    try:
        print("DEBUG: Ejecutando scrape_all_sources...")
        # Asegúrate de que esta función sea async
        await scrape_all_sources()
        print("DEBUG: Scrape finalizado con éxito.")
    except Exception as e:
        print(f"ERROR en scraping: {e}")
        return

    print("DEBUG: Proceso terminado exitosamente.")

if __name__ == '__main__':
    # Añadimos el path actual para que encuentre los módulos
    sys.path.append(os.getcwd())
    
    # Ejecutamos el ciclo de eventos
    asyncio.run(run())
    # El script termina aquí automáticamente, liberando el proceso en GitHub
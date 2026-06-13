import os
import json
import requests
import pymysql
from urllib.parse import urlparse
from bot.scrapers import scrape_all_sources

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
DATABASE_URL = os.environ.get("DATABASE_URL")


def get_db_connection():
    url = urlparse(DATABASE_URL)
    return pymysql.connect(
        host=url.hostname,
        port=url.port or 3306,
        user=url.username,
        password=url.password,
        database=url.path[1:],
        ssl_verify_identity=True,
        cursorclass=pymysql.cursors.DictCursor
    )


def init_db(conn):
    with conn.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS races (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                date DATE NOT NULL,
                distance VARCHAR(50),
                price VARCHAR(50),
                registration_link VARCHAR(500) NOT NULL,
                source VARCHAR(100),
                location VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_race (name, date, registration_link)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_races (
                id INT AUTO_INCREMENT PRIMARY KEY,
                race_id INT NOT NULL,
                user_id BIGINT NOT NULL,
                status VARCHAR(20) NOT NULL,
                time VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_user_race (race_id, user_id)
            )
        """)
    conn.commit()


def race_exists(conn, name, date, link):
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT id FROM races WHERE name = %s AND date = %s AND registration_link = %s",
            (name, date, link)
        )
        return cursor.fetchone()


def add_race(conn, race):
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT INTO races (name, date, distance, price, registration_link, source, location)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            race['name'], race['date'], race.get('distance', 'N/A'),
            race.get('price', 'N/A'), race['registration_link'],
            race['source'], race.get('location', 'N/A')
        ))
        conn.commit()
        return cursor.lastrowid


def send_telegram_notification(race, race_id):
    message = (
        f"🏃 *NUEVA CARRERA DETECTADA*\n\n"
        f"📌 *{race['name']}*\n"
        f"📅 Fecha: {race['date']}\n"
        f"📍 Lugar: {race.get('location', 'N/A')}\n"
        f"🔗 [Más información]({race['registration_link']})\n"
        f"📍 Fuente: {race['source']}"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Me apunto", "callback_data": f"apunto_{race_id}"},
                {"text": "❌ Paso", "callback_data": f"paso_{race_id}"}
            ],
            [
                {"text": "🤔 Me lo pienso", "callback_data": f"pienso_{race_id}"}
            ]
        ]
    }

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "reply_markup": json.dumps(keyboard),
        "disable_web_page_preview": True
    }
    response = requests.post(url, data=payload, timeout=15)
    print(f"  Telegram -> {response.status_code}")


def run():
    print("DEBUG: Iniciando proceso de scraping...")

    try:
        conn = get_db_connection()
        init_db(conn)
        print("DEBUG: Base de datos conectada.")
    except Exception as e:
        print(f"ERROR conectando a BD: {e}")
        return

    print("DEBUG: Ejecutando scrape_all_sources...")
    try:
        races = scrape_all_sources()
    except Exception as e:
        print(f"ERROR en scraping: {e}")
        conn.close()
        return

    print(f"DEBUG: {len(races)} carreras encontradas en total")

    new_count = 0
    for race in races:
        try:
            if not race_exists(conn, race['name'], race['date'], race['registration_link']):
                race_id = add_race(conn, race)
                send_telegram_notification(race, race_id)
                new_count += 1
                print(f"  ✅ Nueva: {race['name']}")
            else:
                print(f"  ⏭️  Ya existe: {race['name']}")
        except Exception as e:
            print(f"  ERROR procesando '{race.get('name')}': {e}")

    conn.close()
    print(f"DEBUG: Proceso terminado. {new_count} carreras nuevas notificadas.")


if __name__ == '__main__':
    run()

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from bot.config import DATABASE_URL

def init_db():
    """Inicializa la base de datos con todas las tablas necesarias en PostgreSQL."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Tabla de carreras (SERIAL sustituye a AUTOINCREMENT)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS races (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                date TEXT NOT NULL,
                distance TEXT,
                price TEXT,
                registration_link TEXT NOT NULL,
                source TEXT NOT NULL,
                location TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, date, registration_link)
            )
        ''')
        
        # Tabla de estado de carreras para el usuario
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_races (
                id SERIAL PRIMARY KEY,
                race_id INTEGER NOT NULL,
                status TEXT NOT NULL,  -- 'accepted', 'rejected', 'pending'
                reminder_sent INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (race_id) REFERENCES races(id),
                UNIQUE(race_id)
            )
        ''')
        
        # Tabla de marcas personales
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS personal_records (
                id SERIAL PRIMARY KEY,
                race_name TEXT NOT NULL,
                time TEXT NOT NULL,
                date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de recordatorios "me lo pienso"
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_reminders (
                id SERIAL PRIMARY KEY,
                race_id INTEGER NOT NULL,
                reminder_date DATE NOT NULL,
                sent INTEGER DEFAULT 0,
                FOREIGN KEY (race_id) REFERENCES races(id)
            )
        ''')

@contextmanager
def get_db():
    """Context manager para conexiones a PostgreSQL."""
    # Usamos RealDictCursor para que los resultados actúen como diccionarios
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def race_exists(name, date, registration_link):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id FROM races 
            WHERE name = %s AND date = %s AND registration_link = %s
        ''', (name, date, registration_link))
        return cursor.fetchone() is not None

def add_race(name, date, distance, price, registration_link, source, location='N/A'):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO races (name, date, distance, price, registration_link, source, location)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (name, date, registration_link) DO NOTHING
            RETURNING id
        ''', (name, date, distance, price, registration_link, source, location))
        result = cursor.fetchone()
        
        # Si no se insertó (porque ya existía), buscamos el ID
        if not result:
            cursor.execute('''
                SELECT id FROM races 
                WHERE name = %s AND date = %s AND registration_link = %s
            ''', (name, date, registration_link))
            result = cursor.fetchone()
            
        return result['id'] if result else None

def get_race_by_id(race_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM races WHERE id = %s', (race_id,))
        return cursor.fetchone()

def set_user_race_status(race_id, status):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_races (race_id, status, created_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (race_id) 
            DO UPDATE SET status = EXCLUDED.status, created_at = CURRENT_TIMESTAMP
        ''', (race_id, status))

def get_user_race_status(race_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT status FROM user_races WHERE race_id = %s', (race_id,))
        result = cursor.fetchone()
        return result['status'] if result else None

def get_accepted_races():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.*, ur.created_at as accepted_date
            FROM races r
            JOIN user_races ur ON r.id = ur.race_id
            WHERE ur.status = 'accepted'
            ORDER BY r.date ASC
        ''')
        return cursor.fetchall()

def add_pending_reminder(race_id, reminder_date):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO pending_reminders (race_id, reminder_date)
            VALUES (%s, %s)
        ''', (race_id, reminder_date))

def get_pending_reminders():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT pr.*, r.name, r.date, r.registration_link
            FROM pending_reminders pr
            JOIN races r ON pr.race_id = r.id
            WHERE pr.sent = 0 AND pr.reminder_date <= CURRENT_DATE
        ''')
        return cursor.fetchall()

def mark_reminder_sent(reminder_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE pending_reminders SET sent = 1 WHERE id = %s', (reminder_id,))

def get_races_needing_reminder(days_before=3):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.*, ur.reminder_sent
            FROM races r
            JOIN user_races ur ON r.id = ur.race_id
            WHERE ur.status = 'accepted' 
            AND ur.reminder_sent = 0
            AND date(r.date) = CURRENT_DATE + (%s * INTERVAL '1 day')
        ''', (days_before,))
        return cursor.fetchall()

def mark_reminder_sent_for_race(race_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE user_races SET reminder_sent = 1 WHERE race_id = %s
        ''', (race_id,))

def add_personal_record(race_name, time, date):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO personal_records (race_name, time, date)
            VALUES (%s, %s, %s)
        ''', (race_name, time, date))

def get_personal_records(race_name=None):
    with get_db() as conn:
        cursor = conn.cursor()
        if race_name:
            cursor.execute('''
                SELECT * FROM personal_records 
                WHERE race_name ILIKE %s
                ORDER BY date DESC
            ''', (f'%{race_name}%',)) # ILIKE ignora mayúsculas/minúsculas en Postgres
        else: 
            cursor.execute('SELECT * FROM personal_records ORDER BY date DESC')
        return cursor.fetchall()
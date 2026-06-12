import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'races.db')

def init_db():
    """Inicializa la base de datos con todas las tablas necesarias."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Tabla de carreras
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS races (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                date TEXT NOT NULL,
                distance TEXT,
                price TEXT,
                registration_link TEXT NOT NULL,
                source TEXT NOT NULL,
                location TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, date, registration_link)
            )
        ''')
        
        # Tabla de estado de carreras para el usuario
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_races (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                race_id INTEGER NOT NULL,
                status TEXT NOT NULL,  -- 'accepted', 'rejected', 'pending'
                reminder_sent INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (race_id) REFERENCES races(id),
                UNIQUE(race_id)
            )
        ''')
        
        # Tabla de marcas personales
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS personal_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                race_name TEXT NOT NULL,
                time TEXT NOT NULL,  -- formato: HH:MM:SS o MM:SS
                date TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de recordatorios "me lo pienso"
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                race_id INTEGER NOT NULL,
                reminder_date TEXT NOT NULL,
                sent INTEGER DEFAULT 0,
                FOREIGN KEY (race_id) REFERENCES races(id)
            )
        ''')
        
        conn.commit()

@contextmanager
def get_db():
    """Context manager para conexiones a la base de datos."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def race_exists(name, date, registration_link):
    """Verifica si una carrera ya existe en la base de datos."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id FROM races 
            WHERE name = ? AND date = ? AND registration_link = ?
        ''', (name, date, registration_link))
        return cursor.fetchone() is not None

def add_race(name, date, distance, price, registration_link, source, location='N/A'):
    """Añade una nueva carrera a la base de datos."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO races (name, date, distance, price, registration_link, source, location)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, date, distance, price, registration_link, source, location))
        return cursor.lastrowid

def get_race_by_id(race_id):
    """Obtiene una carrera por su ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM races WHERE id = ?', (race_id,))
        return cursor.fetchone()

def set_user_race_status(race_id, status):
    """Establece el estado de una carrera para el usuario."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO user_races (race_id, status, created_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (race_id, status))

def get_user_race_status(race_id):
    """Obtiene el estado de una carrera para el usuario."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT status FROM user_races WHERE race_id = ?', (race_id,))
        result = cursor.fetchone()
        return result['status'] if result else None

def get_accepted_races():
    """Obtiene todas las carreras aceptadas por el usuario."""
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
    """Añade un recordatorio pendiente para 'me lo pienso'."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO pending_reminders (race_id, reminder_date)
            VALUES (?, ?)
        ''', (race_id, reminder_date))

def get_pending_reminders():
    """Obtiene recordatorios pendientes que no han sido enviados."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT pr.*, r.name, r.date, r.registration_link
            FROM pending_reminders pr
            JOIN races r ON pr.race_id = r.id
            WHERE pr.sent = 0 AND pr.reminder_date <= date('now')
        ''')
        return cursor.fetchall()

def mark_reminder_sent(reminder_id):
    """Marca un recordatorio como enviado."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE pending_reminders SET sent = 1 WHERE id = ?', (reminder_id,))

def get_races_needing_reminder(days_before=3):
    """Obtiene carreras que necesitan recordatorio (X días antes)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.*, ur.reminder_sent
            FROM races r
            JOIN user_races ur ON r.id = ur.race_id
            WHERE ur.status = 'accepted' 
            AND ur.reminder_sent = 0
            AND date(r.date) = date('now', '+' || ? || ' days')
        ''', (days_before,))
        return cursor.fetchall()

def mark_reminder_sent_for_race(race_id):
    """Marca que se ha enviado el recordatorio para una carrera."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE user_races SET reminder_sent = 1 WHERE race_id = ?
        ''', (race_id,))

def add_personal_record(race_name, time, date):
    """Añade una marca personal."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO personal_records (race_name, time, date)
            VALUES (?, ?, ?)
        ''', (race_name, time, date))

def get_personal_records(race_name=None):
    """Obtiene marcas personales, filtrando por carrera si se especifica."""
    with get_db() as conn:
        cursor = conn.cursor()
        if race_name:
            cursor.execute('''
                SELECT * FROM personal_records 
                WHERE race_name LIKE ?
                ORDER BY date DESC
            ''', (f'%{race_name}%',))
        else:
            cursor.execute('SELECT * FROM personal_records ORDER BY date DESC')
        return cursor.fetchall()

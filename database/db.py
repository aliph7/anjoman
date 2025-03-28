import sqlite3
import os
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    pass

DB_PATH = "sci_bot.db"

def get_connection():
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"Error connecting to database: {str(e)}")
        raise DatabaseError("Cannot connect to database")

@contextmanager
def transaction():
    with get_connection() as conn:
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction rolled back due to: {str(e)}")
            raise

def setup_database():
    with transaction() as conn:
        c = conn.cursor()
        
        # ایجاد جداول اگه وجود نداشته باشن
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            field TEXT,
            student_id TEXT,
            phone TEXT,
            email TEXT,
            registered INTEGER DEFAULT 0
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            photo TEXT
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            cost INTEGER NOT NULL,
            description TEXT,
            photo TEXT
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            cost INTEGER NOT NULL,
            description TEXT,
            photo TEXT
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL,
            item_title TEXT NOT NULL,
            payment_photo TEXT,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )''')
        
        # اضافه کردن ستون photo به جدول‌های موجود اگه وجود نداشته باشه
        c.execute('''ALTER TABLE events ADD COLUMN photo TEXT''') if not any(col[1] == "photo" for col in c.execute("PRAGMA table_info(events)")) else None
        c.execute('''ALTER TABLE courses ADD COLUMN photo TEXT''') if not any(col[1] == "photo" for col in c.execute("PRAGMA table_info(courses)")) else None
        c.execute('''ALTER TABLE visits ADD COLUMN photo TEXT''') if not any(col[1] == "photo" for col in c.execute("PRAGMA table_info(visits)")) else None
        
        c.execute("CREATE INDEX IF NOT EXISTS idx_registrations_user_id ON registrations(user_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_registrations_status ON registrations(status)")
        
        logger.info("Database setup completed with indices and photo columns")

def get_user(user_id: str):
    with transaction() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return c.fetchone()

def update_user(user_id: str, data: dict):
    with transaction() as conn:
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO users (user_id, name, field, student_id, phone, email, registered)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                  (user_id, data.get("name"), data.get("field"), data.get("student_id"), 
                   data.get("phone"), data.get("email"), 1))
        logger.info(f"User updated: {user_id}")

def get_events():
    with transaction() as conn:
        c = conn.cursor()
        c.execute("SELECT title, date, description, photo FROM events")
        events = c.fetchall()
        return [{"title": e["title"], "date": e["date"], "description": e["description"], "photo": e["photo"]} for e in events]

def add_event(title: str, date: str, description: str, photo: str = None):
    with transaction() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO events (title, date, description, photo) VALUES (?, ?, ?, ?)", 
                  (title, date, description, photo))
        logger.info(f"Event added: {title}")

def get_courses():
    with transaction() as conn:
        c = conn.cursor()
        c.execute("SELECT title, cost, description, photo FROM courses")
        courses = c.fetchall()
        return [{"title": c["title"], "cost": c["cost"], "description": c["description"], "photo": c["photo"]} for c in courses]

def add_course(*, title: str, cost: int, description: str, photo: str = None):
    if not title or len(title.strip()) < 3:
        raise DatabaseError("عنوان دوره باید حداقل ۳ کاراکتر باشد")
    if cost < 0:
        raise DatabaseError("هزینه نمی‌تواند منفی باشد")
    with transaction() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO courses (title, cost, description, photo) VALUES (?, ?, ?, ?)", 
                  (title, cost, description, photo))
        logger.info(f"Course added: {title}, cost={cost}, desc={description}")

def get_visits():
    with transaction() as conn:
        c = conn.cursor()
        c.execute("SELECT title, cost, description, photo FROM visits")
        visits = c.fetchall()
        return [{"title": v["title"], "cost": v["cost"], "description": v["description"], "photo": v["photo"]} for v in visits]

def add_visit(title: str, cost: int, description: str, photo: str = None):
    if not title or len(title.strip()) < 3:
        raise DatabaseError("عنوان بازدید باید حداقل ۳ کاراکتر باشد")
    if cost < 0:
        raise DatabaseError("هزینه نمی‌تواند منفی باشد")
    with transaction() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO visits (title, cost, description, photo) VALUES (?, ?, ?, ?)", 
                  (title, cost, description, photo))
        logger.info(f"Visit added: {title}, cost={cost}, desc={description}")

def add_registration(user_id: str, reg_type: str, item_title: str, payment_photo: str) -> int:
    with transaction() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO registrations (user_id, type, item_title, payment_photo) VALUES (?, ?, ?, ?)",
                  (user_id, reg_type, item_title, payment_photo))
        reg_id = c.lastrowid
        logger.info(f"Registration added: {reg_id} for user {user_id}")
        return reg_id

def get_registration(reg_id: int):
    with transaction() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM registrations WHERE id = ?", (reg_id,))
        return c.fetchone()

def update_registration_status(reg_id: int, status: str):
    with transaction() as conn:
        c = conn.cursor()
        c.execute("UPDATE registrations SET status = ? WHERE id = ?", (status, reg_id))
        logger.info(f"Registration {reg_id} status updated to {status}")

def get_all_registrations():
    with transaction() as conn:
        c = conn.cursor()
        c.execute('''SELECT r.id, r.user_id, r.type, r.item_title, r.status, u.name 
                     FROM registrations r 
                     JOIN users u ON r.user_id = u.user_id 
                     WHERE u.registered = 1''')
        registrations = c.fetchall()
        return registrations

def delete_course(title: str):
    with transaction() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM courses WHERE title = ?", (title,))
        c.execute("DELETE FROM registrations WHERE type = 'course' AND item_title = ?", (title,))
        logger.info(f"Course {title} and related registrations deleted")

def delete_visit(title: str):
    with transaction() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM visits WHERE title = ?", (title,))
        c.execute("DELETE FROM registrations WHERE type = 'visit' AND item_title = ?", (title,))
        logger.info(f"Visit {title} and related registrations deleted")

def get_all_registered_users():
    with transaction() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE registered = 1")
        users = c.fetchall()
        return [user["user_id"] for user in users]
import sqlite3
from datetime import datetime

DB_PATH = 'database.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        trial_start TEXT,
        is_paid INTEGER DEFAULT 0,
        lang TEXT
    )''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id=?', (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {'user_id': row[0], 'trial_start': row[1], 'is_paid': bool(row[2]), 'lang': row[3]}
    return None

def save_trial_start(user_id, lang):
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO users (user_id, trial_start, is_paid, lang) VALUES (?, ?, 0, ?)', (user_id, now, lang))
    conn.commit()
    conn.close()

def set_paid(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE users SET is_paid=1 WHERE user_id=?', (user_id,))
    conn.commit()
    conn.close()

def is_paid(user_id):
    user = get_user(user_id)
    return user and user['is_paid']

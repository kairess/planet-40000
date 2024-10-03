import sqlite3
import os
from flask import g, Flask

DB_FILE = 'db.sqlite3'

app = Flask(__name__)

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_FILE)
        db.row_factory = sqlite3.Row
    return db

def create_tables(cursor):
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        steam_id TEXT,
        login_count INTEGER DEFAULT 1,
        last_login DATETIME DEFAULT CURRENT_TIMESTAMP,
        money INTEGER DEFAULT 100,
        current_planet TEXT DEFAULT '/static/planets/Earth_50.png',
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS inventories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        steam_id TEXT,
        planet_name TEXT,
        planet_path TEXT,
        price INTEGER DEFAULT 0,
        status TEXT DEFAULT 'inventory',
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

if not os.path.exists(DB_FILE):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    create_tables(cursor)
    print("새로운 DB 파일이 생성되었습니다.")
else:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    create_tables(cursor)
    print("기존 DB 파일에 연결되었습니다.")

import sqlite3
from flask import g

DATABASE = 'data/example.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

def create_db():
    """Create the database tables."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userID TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            filepath TEXT
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fileid INTEGER,
            userid TEXT,
            platform TEXT,
            no_of_tests INTEGER,
            time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, completed INTEGER DEFAULT 0,
            FOREIGN KEY (fileid) REFERENCES files (id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Options (name TEXT)
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT,
            job_id INTEGER,
            FOREIGN KEY (job_id) REFERENCES jobs (id)
            )
        """)
        
        
        # cur.execute("""
        #     CREATE TABLE IF NOT EXISTS jobs (
        #         id INTEGER PRIMARY KEY AUTOINCREMENT,
        #         fileid INTEGER,
        #         userid TEXT,
        #         platform TEXT,
        #         no_of_tests INTEGER,
        #         file_name TEXT,
        #         FOREIGN KEY (fileid) REFERENCES files (id)
        #     );
        # """)
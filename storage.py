import sqlite3
import os
from dataclasses import dataclass
from typing import List, Optional
import secrets
import time

from env import MAGIC_LINK_EXPIRY_SECONDS

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'solicitations.db')

# User model
@dataclass
class User:
    id: int
    email: str
    is_admin: bool = False

# Token model
@dataclass
class MagicLinkToken:
    token: str
    email: str
    expires_at: float


# Persistent storage using SQLite
def setup_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                is_admin INTEGER
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS filters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                criteria TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT,
                email TEXT,
                expires_at REAL
            )
        ''')
        conn.commit()

def add_user(email: str, is_admin: bool = False) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('REPLACE INTO users (email, is_admin) VALUES (?, ?)',
                       (email, int(is_admin)))
        conn.commit()
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        return cursor.fetchone()[0]

def get_user(email: str) -> Optional[User]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, email, is_admin FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        if row:
            return User(id=row[0], email=row[1], is_admin=bool(row[2]))
        return None

def generate_magic_token(email: str) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = time.time() + MAGIC_LINK_EXPIRY_SECONDS
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('REPLACE INTO tokens (token, email, expires_at) VALUES (?, ?, ?)',
                       (token, email, expires_at))
        conn.commit()
    return token

def get_email_for_token(token: str) -> Optional[str]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT email, expires_at FROM tokens WHERE token = ?', (token,))
        row = cursor.fetchone()
        if row and time.time() < row[1]:
            return row[0]
        return None

def invalidate_token(token: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM tokens WHERE token = ?', (token,))
        conn.commit()

def list_users() -> List[User]:
    users: List[User] = []
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, email, is_admin FROM users')
        for id_, email, is_admin in cursor.fetchall():
            users.append(User(id=id_, email=email, is_admin=bool(is_admin)))
    return users

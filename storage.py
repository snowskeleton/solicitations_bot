import sqlite3
import os
from dataclasses import dataclass
from typing import Dict, List, Optional
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


# Schedule model
@dataclass
class Schedule:
    id: int
    user_id: int
    name: str
    monday: Optional[str]
    tuesday: Optional[str]
    wednesday: Optional[str]
    thursday: Optional[str]
    friday: Optional[str]
    saturday: Optional[str]
    sunday: Optional[str]


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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                monday TEXT,
                tuesday TEXT,
                wednesday TEXT,
                thursday TEXT,
                friday TEXT,
                saturday TEXT,
                sunday TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        conn.commit()

def add_user(email: str, is_admin: bool = False) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT OR IGNORE INTO users (email, is_admin) VALUES (?, ?)', (email, int(is_admin)))
        cursor.execute(
            'UPDATE users SET is_admin = ? WHERE email = ?', (int(is_admin), email))
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


# Schedule-related functions
def get_schedules_for_user(user_id: int) -> List[Schedule]:
    schedules: List[Schedule] = []
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT id, user_id, name, monday, tuesday, wednesday, thursday, friday, saturday, sunday
               FROM schedules WHERE user_id = ?''', (user_id,))
        for row in cursor.fetchall():
            schedules.append(Schedule(*row))
    return schedules


def get_schedule_by_id(schedule_id: int) -> Optional[Schedule]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT id, user_id, name, monday, tuesday, wednesday, thursday, friday, saturday, sunday
               FROM schedules WHERE id = ?''', (schedule_id,))
        row = cursor.fetchone()
        print(row)
        return Schedule(*row) if row else None


def add_schedule(user_id: int, schedule: Dict[str, str]) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO schedules (
                user_id, name, monday, tuesday, wednesday,
                thursday, friday, saturday, sunday
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            schedule.get("name", ""),
            schedule.get("Monday"),
            schedule.get("Tuesday"),
            schedule.get("Wednesday"),
            schedule.get("Thursday"),
            schedule.get("Friday"),
            schedule.get("Saturday"),
            schedule.get("Sunday")
        ))
        conn.commit()
        return cursor.lastrowid


# Update a schedule by id with given updates
def update_schedule(schedule_id: int, updates: Dict[str, str]) -> None:
    if not updates:
        return
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        fields = []
        values = []
        for key, value in updates.items():
            fields.append(f"{key.lower()} = ?")
            values.append(value)
        values.append(schedule_id)
        cursor.execute(f'''
            UPDATE schedules
            SET {", ".join(fields)}
            WHERE id = ?
        ''', values)
        conn.commit()

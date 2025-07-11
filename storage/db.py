# Filter model
import sqlite3
import os
from typing import Dict, List, Optional
import secrets
import time

from env import MAGIC_LINK_EXPIRY_SECONDS

from .models import User, Schedule, Filter

from data_sources.Solicitation import Solicitations

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'solicitations.db')


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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schedule_id INTEGER NOT NULL,
                run_date TEXT NOT NULL
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

def get_user_by_id(id: int) -> Optional[User]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, email, is_admin FROM users WHERE id = ?', (id,))
        row = cursor.fetchone()
        if row:
            return User(id=row[0], email=row[1], is_admin=bool(row[2]))
        return None

def get_all_users() -> List[User]:
    users: List[User] = []
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, email, is_admin FROM users')
        for row in cursor.fetchall():
            users.append(User(id=row[0], email=row[1], is_admin=bool(row[2])))
    return users

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


# Filters
def get_filters_for_user(user_id: int) -> List[Filter]:
    filters: List[Filter] = []
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, user_id, name, criteria FROM filters WHERE user_id = ?', (user_id,))
        for row in cursor.fetchall():
            filters.append(Filter(*row))
    return filters


def get_filter_by_id(filter_id: int) -> Optional[Filter]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, user_id, name, criteria FROM filters WHERE id = ?', (filter_id,))
        row = cursor.fetchone()
        return Filter(*row) if row else None


def add_filter(user_id: int, name: str, criteria: str) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO filters (user_id, name, criteria) VALUES (?, ?, ?)', (user_id, name, criteria))
        conn.commit()
        result = cursor.lastrowid
        if result is None:
            raise RuntimeError("Failed to insert filter")
        return result


def update_filter(filter_id: int, name: str, criteria: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE filters SET name = ?, criteria = ? WHERE id = ?', (name, criteria, filter_id))
        conn.commit()


def delete_filter(filter_id: int) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM filters WHERE id = ?', (filter_id,))
        conn.commit()


# Schedules
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
        result = cursor.lastrowid
        if result is None:
            raise RuntimeError("Failed to insert schedule")
        return result


def update_schedule(schedule_id: int, updates: Dict[str, str]) -> None:
    if not updates:
        return
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        fields: List[str] = []
        values: List[str] = []
        for key, value in updates.items():
            fields.append(f"{key.lower()} = ?")
            values.append(value)
        values.append(str(schedule_id))
        cursor.execute(f'''
            UPDATE schedules
            SET {", ".join(fields)}
            WHERE id = ?
        ''', values)
        conn.commit()


def delete_schedule(schedule_id: int) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM schedules WHERE id = ?', (schedule_id,))
        conn.commit()

def has_run_today(schedule_id: int, date_str: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM job_runs WHERE schedule_id = ? AND run_date = ?', (schedule_id, date_str))
        return cursor.fetchone() is not None

def mark_as_run(schedule_id: int, date_str: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO job_runs (schedule_id, run_date) VALUES (?, ?)', (schedule_id, date_str))
        conn.commit()

def get_all_schedules() -> List[Schedule]:
    schedules: List[Schedule] = []
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, user_id, name, monday, tuesday, wednesday, thursday, friday, saturday, sunday
            FROM schedules
        ''')
        for row in cursor.fetchall():
            schedules.append(Schedule(*row))
    return schedules

def get_all_schedule_user_ids() -> List[int]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT user_id FROM schedules')
        return [row[0] for row in cursor.fetchall()]


# Solicitations
def setup_solicitations_table():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS solicitations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                solicitation_id TEXT UNIQUE,
                entity_name TEXT,
                state TEXT,
                open_date TEXT,
                department TEXT,
                posted_date TEXT,
                title TEXT,
                status TEXT,
                solicitation_number TEXT,
                description TEXT,
                url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()


def save_solicitations(solicitations: Solicitations) -> None:
    """Save a list of solicitations to the database."""
    setup_solicitations_table()
    print(f"Saving {len(solicitations)} solicitations to database...")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        for solicitation in solicitations:
            cursor.execute('''
                INSERT OR REPLACE INTO solicitations (
                    solicitation_id, entity_name, state, open_date, department,
                    posted_date, title, status, solicitation_number, description, url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                solicitation.solicitation_id or solicitation.Id,
                solicitation.EntityName,
                solicitation.state,
                solicitation.open_date,
                solicitation.department,
                solicitation.posted_date,
                solicitation.title,
                solicitation.status,
                solicitation.solicitation_number,
                solicitation.description,
                solicitation.url
            ))
        conn.commit()
    print(f"Successfully saved {len(solicitations)} solicitations to database")


def get_all_solicitations() -> Solicitations:
    """Get all solicitations from the database."""
    setup_solicitations_table()
    from data_sources.Solicitation import Solicitation
    solicitations = Solicitations()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT solicitation_id, entity_name, state, open_date, department,
                   posted_date, title, status, solicitation_number, description, url
            FROM solicitations
            ORDER BY created_at DESC
        ''')
        rows = cursor.fetchall()
        print(f"Retrieved {len(rows)} solicitations from database")
        for row in rows:
            solicitations.append(Solicitation(
                Id=row[0] or "",
                EntityName=row[1] or "",
                state=row[2],
                open_date=row[3],
                department=row[4],
                posted_date=row[5],
                title=row[6],
                status=row[7],
                solicitation_number=row[8],
                description=row[9],
                url=row[10]
            ))
    return solicitations


def get_solicitations_by_source(entity_name: str) -> Solicitations:
    """Get solicitations from a specific source."""
    setup_solicitations_table()
    from data_sources.Solicitation import Solicitation
    solicitations = Solicitations()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT solicitation_id, entity_name, state, open_date, department,
                   posted_date, title, status, solicitation_number, description, url
            FROM solicitations
            WHERE entity_name = ?
            ORDER BY created_at DESC
        ''', (entity_name,))
        rows = cursor.fetchall()
        print(
            f"Retrieved {len(rows)} solicitations from database for source: {entity_name}")
        for row in rows:
            solicitations.append(Solicitation(
                Id=row[0] or "",
                EntityName=row[1] or "",
                state=row[2],
                open_date=row[3],
                department=row[4],
                posted_date=row[5],
                title=row[6],
                status=row[7],
                solicitation_number=row[8],
                description=row[9],
                url=row[10]
            ))
    return solicitations


def clear_solicitations_by_source(entity_name: str) -> None:
    """Clear all solicitations from a specific source."""
    setup_solicitations_table()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'DELETE FROM solicitations WHERE entity_name = ?', (entity_name,))
        conn.commit()


def clear_all_solicitations() -> None:
    """Clear all solicitations from the database."""
    setup_solicitations_table()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM solicitations')
        conn.commit()

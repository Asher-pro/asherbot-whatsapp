"""
Conversation memory and reminders using SQLite.
"""

import sqlite3
import os
from datetime import datetime, timezone
from config import settings


def _get_db_path() -> str:
    db_path = settings.DATABASE_PATH
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    return db_path


def _connect():
    return sqlite3.connect(_get_db_path())


def init_db():
    """Create tables if they don't exist."""
    conn = _connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_phone
        ON messages(phone, timestamp DESC)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            reminder_text TEXT NOT NULL,
            remind_at DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            delivered INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_reminders_due
        ON reminders(remind_at, delivered)
    """)
    conn.commit()
    conn.close()


def save_message(phone: str, role: str, content: str):
    conn = _connect()
    conn.execute(
        "INSERT INTO messages (phone, role, content) VALUES (?, ?, ?)",
        (phone, role, content),
    )
    conn.commit()
    conn.close()


def get_history(phone: str, limit: int = 20) -> list[dict]:
    conn = _connect()
    cursor = conn.execute(
        """
        SELECT role, content FROM (
            SELECT role, content, timestamp
            FROM messages
            WHERE phone = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ) sub ORDER BY timestamp ASC
        """,
        (phone, limit),
    )
    history = [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]
    conn.close()
    return history


# --- Reminders ---

def create_reminder(phone: str, text: str, remind_at: str) -> int:
    """Create a reminder. remind_at should be ISO format UTC datetime string."""
    conn = _connect()
    cursor = conn.execute(
        "INSERT INTO reminders (phone, reminder_text, remind_at) VALUES (?, ?, ?)",
        (phone, text, remind_at),
    )
    reminder_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return reminder_id


def get_due_reminders() -> list[dict]:
    """Get all reminders that are due and not yet delivered."""
    conn = _connect()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.execute(
        "SELECT id, phone, reminder_text, remind_at FROM reminders WHERE remind_at <= ? AND delivered = 0",
        (now,),
    )
    reminders = [
        {"id": row[0], "phone": row[1], "reminder_text": row[2], "remind_at": row[3]}
        for row in cursor.fetchall()
    ]
    conn.close()
    return reminders


def mark_reminder_delivered(reminder_id: int):
    conn = _connect()
    conn.execute("UPDATE reminders SET delivered = 1 WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()


def get_pending_reminders(phone: str) -> list[dict]:
    """Get all pending (undelivered) reminders for a phone number."""
    conn = _connect()
    cursor = conn.execute(
        "SELECT id, reminder_text, remind_at FROM reminders WHERE phone = ? AND delivered = 0 ORDER BY remind_at ASC",
        (phone,),
    )
    reminders = [
        {"id": row[0], "reminder_text": row[1], "remind_at": row[2]}
        for row in cursor.fetchall()
    ]
    conn.close()
    return reminders

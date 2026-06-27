import os
import sqlite3
import uuid
from datetime import datetime

DB_PATH = "chat_history.db"

def init_chat_db():
    """Initializes schemas for both conversational sessions and messages."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Create table for tracking chat threads/sessions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id TEXT PRIMARY KEY,
            title TEXT,
            created_at TEXT
        )
    """)
    
    # 2. Create table for individual messages with timestamp and feedback states
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            timestamp TEXT,
            feedback TEXT,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

# --- SESSION CRUD OPERATORS ---

def create_chat_session(title="New Conversation"):
    """Generates a new independent thread partition."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    session_id = str(uuid.uuid4())
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    cursor.execute(
        "INSERT INTO chat_sessions (session_id, title, created_at) VALUES (?, ?, ?)",
        (session_id, title, date_str)
    )
    conn.commit()
    conn.close()
    return {"session_id": session_id, "title": title}

def get_all_sessions():
    """Retrieves all conversation logs sorted newest first."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT session_id, title, created_at FROM chat_sessions ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{"session_id": r[0], "title": r[1], "created_at": r[2]} for r in rows]

def rename_chat_session(session_id, new_title):
    """Updates the display title of a chat sidebar item."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE chat_sessions SET title = ? WHERE session_id = ?", (new_title, session_id))
    conn.commit()
    conn.close()

def delete_chat_session(session_id):
    """Purges an entire conversation thread and its messages from disk storage."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON") # Turn on cascade delete
    cursor.execute("DELETE FROM chat_sessions WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

# --- MESSAGE LOG OPERATORS ---

def add_chat_message(session_id, role, content):
    """Appends an individual token sequence payload element into history log."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    time_str = datetime.now().strftime("%I:%M %p") # Format as "11:45 PM"
    
    cursor.execute(
        "INSERT INTO chat_messages (session_id, role, content, timestamp, feedback) VALUES (?, ?, ?, ?, ?)",
        (session_id, role, content, time_str, "none")
    )
    message_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"message_id": message_id, "timestamp": time_str}

def get_session_history(session_id):
    """Fetches full historical context array for an individual conversation thread."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, role, content, timestamp, feedback FROM chat_messages WHERE session_id = ? ORDER BY id ASC",
        (session_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": r[0], "role": r[1], "content": r[2], "timestamp": r[3], "feedback": r[4]}
        for r in rows
    ]

def submit_message_feedback(message_id, feedback_type):
    """Updates the feedback state flag (thumbs_up, thumbs_down, none)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE chat_messages SET feedback = ? WHERE id = ?", (feedback_type, message_id))
    conn.commit()
    conn.close()

# Auto-initialize database tracking when file loads
init_chat_db()
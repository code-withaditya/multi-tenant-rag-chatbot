import os
import sqlite3
from datetime import datetime

# Document Parsing Extensions
import docx
from bs4 import BeautifulSoup
import pandas as pd
from pypdf import PdfReader

# Internal Project Ingestion Bridge
from src.database import VectorDBManager

DB_PATH = "documents_meta.db"
STORAGE_DIR = "./data/storage"

# Ensure physical upload storage space path exists
os.makedirs(STORAGE_DIR, exist_ok=True)

# =====================================================================
# 📊 DATABASE METADATA TRACKER (SQLite) - MULTI-TENANT ISOLATED
# =====================================================================

def init_db():
    """Initializes the multi-tenant tracking schema to safely partition document states."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # CHANGED: Added session_id column and restricted uniqueness to the composite pairs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS docs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            session_id TEXT,
            file_size_kb REAL,
            upload_date TEXT,
            status TEXT,
            UNIQUE(filename, session_id)
        )
    """)
    conn.commit()
    conn.close()


def add_document(filename, file_size_bytes, session_id):
    """Registers a new workspace document asset mapped to an isolated session."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    size_kb = round(file_size_bytes / 1024, 2)
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        # CHANGED: Explicitly tie insertions to the localized session token
        cursor.execute(
            "INSERT INTO docs (filename, session_id, file_size_kb, upload_date, status) VALUES (?, ?, ?, ?, ?)",
            (filename, session_id, size_kb, date_str, "Processing")
        )
    except sqlite3.IntegrityError:
        # If file was uploaded previously inside this specific session, reset its status tracking
        cursor.execute(
            "UPDATE docs SET status = 'Processing' WHERE filename = ? AND session_id = ?", 
            (filename, session_id)
        )
    conn.commit()
    conn.close()


def update_document_status(filename, status, session_id):
    """Updates status records scoped strictly to a targeted user's sandbox ledger."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # CHANGED: Constrained query parameter targeting via session validation check
    cursor.execute(
        "UPDATE docs SET status = ? WHERE filename = ? AND session_id = ?", 
        (status, filename, session_id)
    )
    conn.commit()
    conn.close()


def get_all_documents(session_id):
    """Returns lists containing data elements filtered strictly by active session visibility."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # CHANGED: Implemented SELECT filtering clause to block cross-tenant database extraction leaks
    cursor.execute(
        "SELECT filename, file_size_kb, upload_date, status FROM docs WHERE session_id = ?", 
        (session_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"filename": r[0], "size_kb": r[1], "date": r[2], "status": r[3]} for r in rows]


def remove_document_meta(filename, session_id):
    """Purges tracking schema indexes matching a unique session-bound target asset."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # CHANGED: Enforced safety criteria bounding so deletions don't bleed out into alternative workspaces
    cursor.execute("DELETE FROM docs WHERE filename = ? AND session_id = ?", (filename, session_id))
    conn.commit()
    conn.close()


# =====================================================================
# 📑 MULTI-FORMAT TEXT EXTRACTORS & WORKERS
# =====================================================================

def extract_text(file_path, filename):
    """
    Reads local assets from disk storage and safely isolates raw strings 
    across 6 targeted format configurations.
    """
    ext = filename.split('.')[-1].lower()
    text = ""
    
    if ext == "pdf":
        reader = PdfReader(file_path)
        text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        
    elif ext == "docx":
        doc = docx.Document(file_path)
        text = "\n".join([p.text for p in doc.paragraphs])
        
    elif ext in ["txt", "md"]:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
            
    elif ext == "csv":
        df = pd.read_csv(file_path)
        text = df.to_string()
        
    elif ext == "html":
        with open(file_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
            text = soup.get_text(separator="\n")
            
    return text


def process_and_embed_background(filename, file_path, session_id):
    """
    Runs structural text extractions asynchronously and forwards payload data 
    straight through your active VectorDBManager ingestion core.
    """
    try:
        # 1. Parse raw text out of physical storage container source
        raw_text = extract_text(file_path, filename)
        
        if not raw_text.strip():
            raise ValueError("No extractable string text content detected inside document.")
            
        # 2. Vectorize and index structural components directly using your DB Engine
        db_manager = VectorDBManager()
        db_manager.add_text_to_db(raw_text, filename=filename, session_id=session_id)
        
        # 3. Commit Completed workflow log to SQLite tracking schemas
        # CHANGED: Passed through session_id parameter to guarantee clean isolation tracking
        update_document_status(filename, "Completed", session_id)
        print(f"✅ Successfully processed and embedded document: {filename} under session {session_id}")
        
    except Exception as e:
        print(f"❌ Background pipeline extraction failed for {filename}: {str(e)}")
        # CHANGED: Passed through session_id parameter for failure mapping
        update_document_status(filename, f"Failed: {str(e)}", session_id)


# Boot operations initialize structural components immediately on application launch
init_db()
import sqlite3
import os

# Matching your file from the VS Code explorer
DB_NAME = "documents_meta.db"

print(f"🔍 Inspecting database: {DB_NAME}...\n")

if not os.path.exists(DB_NAME):
    print(f"⚠️ {DB_NAME} file was not found. Creating a fresh database file...")

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# 1. Fetch all existing tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [t[0] for t in cursor.fetchall()]
print(f"📊 Found tables: {tables}")

if "docs" in tables:
    # The table exists! Let's check its columns
    cursor.execute("PRAGMA table_info(docs);")
    columns = [col[1] for col in cursor.fetchall()]
    print(f"📋 Current columns in 'docs': {columns}")
    
    if "session_id" not in columns:
        try:
            cursor.execute("ALTER TABLE docs ADD COLUMN session_id TEXT;")
            conn.commit()
            print("\n✅ Success! Added 'session_id' column to your existing 'docs' table.")
        except Exception as e:
            print(f"\n❌ Failed to add column: {e}")
    else:
        print("\n✨ 'session_id' already exists! No changes needed.")
else:
    # The database is completely empty. Let's build the full table structure.
    print("\n📝 'docs' table does not exist yet. Building it from scratch with 'session_id'...")
    try:
        cursor.execute("""
            CREATE TABLE docs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                file_size_kb REAL,
                upload_date TEXT,
                status TEXT,
                session_id TEXT
            );
        """)
        conn.commit()
        print("✅ Success! 'docs' table created perfectly with all required columns.")
    except Exception as e:
        print(f"❌ Failed to create table: {e}")

conn.close()
print("\n🚀 All done! You can now start your uvicorn server.")
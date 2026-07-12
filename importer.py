import sqlite3
import sys
from pathlib import Path

def import_old_db(old_path, new_path):
    # Connect to new DB (creates it if missing)
    new_conn = sqlite3.connect(str(new_path))
    new_conn.executescript("""
        PRAGMA synchronous = OFF;
        PRAGMA journal_mode = MEMORY;
        PRAGMA cache_size = -2000000;   -- 2GB cache (adjust if you have RAM)
    """)

    # Create tables if they don't exist (schema from app)
    new_conn.executescript("""
        CREATE TABLE IF NOT EXISTS entry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS entry_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            value TEXT NOT NULL,
            FOREIGN KEY (entry_id) REFERENCES entry (id)
        );
        -- We'll create indexes after import for speed
    """)

    # Attach the old database
    new_conn.execute(f"ATTACH DATABASE '{old_path}' AS old")

    # Turn off foreign keys to speed up inserts
    new_conn.execute("PRAGMA foreign_keys = OFF")

    # Begin a transaction (we'll commit in chunks to avoid giant WAL)
    new_conn.execute("BEGIN TRANSACTION")

    # Copy entries
    print("Copying entries...")
    new_conn.execute("INSERT INTO entry (id, created) SELECT id, created FROM old.entry")
    entries_count = new_conn.execute("SELECT COUNT(*) FROM entry").fetchone()[0]
    print(f"Copied {entries_count} entries.")

    # Copy data rows – chunked to avoid huge memory usage
    # We'll do it in batches of 1 million rows because old DB has no index
    # but we can use LIMIT/OFFSET to page through old.entry_data.
    # However, LIMIT/OFFSET on a table without index is still a scan, but only once per chunk.
    # Since we have no index, we can't use WHERE id BETWEEN efficiently.
    # Better: use the rowid (implicit) which is sequential.
    # We'll use rowid range.
    print("Copying data rows...")

    # Get total rows in old.entry_data
    total_data = new_conn.execute("SELECT COUNT(*) FROM old.entry_data").fetchone()[0]
    print(f"Total data rows to copy: {total_data}")

    chunk_size = 500000  # half a million rows per chunk
    offset = 0
    copied = 0

    while offset < total_data:
        # Use rowid because it's sequential and indexed internally
        # But entry_data has a primary key 'id' which is also rowid alias.
        # We can select using id BETWEEN ? AND ? if we know min/max id.
        # Let's get min and max id from old.entry_data.
        if offset == 0:
            min_id, max_id = new_conn.execute(
                "SELECT MIN(id), MAX(id) FROM old.entry_data"
            ).fetchone()
            if min_id is None:
                break
            current_id = min_id
        else:
            current_id += chunk_size   # we'll increment by chunk_size

        # Copy a chunk using id range (assumes ids are roughly sequential)
        new_conn.execute(
            "INSERT INTO entry_data (entry_id, name, value) "
            "SELECT entry_id, name, value FROM old.entry_data "
            "WHERE id BETWEEN ? AND ?",
            (current_id, current_id + chunk_size - 1)
        )
        copied += new_conn.total_changes
        print(f"Copied {copied} data rows so far...")
        new_conn.commit()
        new_conn.execute("BEGIN TRANSACTION")
        offset += chunk_size

    new_conn.commit()

    # Detach old DB
    new_conn.execute("DETACH DATABASE old")

    # Create indexes
    print("Creating indexes (this may take a few minutes)...")
    new_conn.executescript("""
        CREATE INDEX idx_entry_created ON entry(created);
        CREATE INDEX idx_entry_data_entry_id ON entry_data(entry_id);
        CREATE INDEX idx_entry_data_name ON entry_data(name);
    """)
    new_conn.commit()

    # Re-enable foreign keys
    new_conn.execute("PRAGMA foreign_keys = ON")

    new_conn.close()
    print("🎉 Import completed successfully!")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python importer.py /path/to/old/weather.sqlite")
        sys.exit(1)
    old_path = Path(sys.argv[1])
    if not old_path.exists():
        print(f"Old database not found: {old_path}")
        sys.exit(1)
    new_path = Path('instance/weather.sqlite')
    print(f"Importing from {old_path} to {new_path}")
    import_old_db(str(old_path), str(new_path))

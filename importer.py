import sqlite3
import sys
from pathlib import Path

def import_old_db(old_db_path, new_db_path):
    old_conn = sqlite3.connect(old_db_path)
    old_conn.row_factory = sqlite3.Row
    new_conn = sqlite3.connect(new_db_path)
    new_conn.executescript("""
        PRAGMA foreign_keys = OFF;
        BEGIN TRANSACTION;
    """)

    # Read old entries
    old_entries = old_conn.execute("SELECT * FROM entry ORDER BY id").fetchall()
    total = len(old_entries)
    print(f"Found {total} entries to import.")

    batch_size = 1000
    for i in range(0, total, batch_size):
        batch = old_entries[i:i+batch_size]
        # Insert entries
        for entry in batch:
            new_conn.execute(
                "INSERT INTO entry (id, created) VALUES (?, ?)",
                (entry['id'], entry['created'])
            )
        # Insert entry_data
        for entry in batch:
            data_rows = old_conn.execute(
                "SELECT name, value FROM entry_data WHERE entry_id = ?",
                (entry['id'],)
            ).fetchall()
            for row in data_rows:
                new_conn.execute(
                    "INSERT INTO entry_data (entry_id, name, value) VALUES (?, ?, ?)",
                    (entry['id'], row['name'], row['value'])
                )
        print(f"Imported {min(i+batch_size, total)} entries")

    new_conn.execute("COMMIT;")
    new_conn.close()
    old_conn.close()
    print("Import completed.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python importer.py /path/to/old/weather.sqlite")
        sys.exit(1)
    old_path = Path(sys.argv[1])
    if not old_path.exists():
        print(f"Old database not found: {old_path}")
        sys.exit(1)

    # Use the same path as the app's instance folder (mounted volume)
    new_path = Path('instance/weather.sqlite')
    print(f"Importing from {old_path} to {new_path}")
    import_old_db(old_path, new_path)

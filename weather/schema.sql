DROP TABLE IF EXISTS entry;
DROP TABLE IF EXISTS entry_data;

CREATE TABLE entry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE entry_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    value TEXT NOT NULL,
    FOREIGN KEY (entry_id) REFERENCES entry (id)
);

CREATE INDEX idx_entry_created ON entry(created);
CREATE INDEX idx_entry_data_entry_id ON entry_data(entry_id);
CREATE INDEX idx_entry_data_name ON entry_data(name);

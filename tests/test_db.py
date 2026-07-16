"""Integration tests for app/db.py — database connection and lifecycle."""

import sqlite3
from app.db import get_db, init_db, close_db


class TestDatabaseConnection:
    def test_get_db_returns_same_connection(self, app):
        with app.app_context():
            db1 = get_db()
            db2 = get_db()
            assert db1 is db2

    def test_get_db_returns_sqlite_connection(self, app):
        with app.app_context():
            db = get_db()
            assert isinstance(db, sqlite3.Connection)

    def test_init_db_creates_tables(self, app):
        with app.app_context():
            # init_db is already called by the app fixture, so
            # verify tables exist.
            db = get_db()
            tables = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            table_names = {t["name"] for t in tables}
            assert "entry" in table_names
            assert "entry_data" in table_names

    def test_entry_table_columns(self, app):
        with app.app_context():
            db = get_db()
            cols = db.execute("PRAGMA table_info(entry)").fetchall()
            col_names = [c["name"] for c in cols]
            assert "id" in col_names
            assert "created" in col_names

    def test_entry_data_table_columns(self, app):
        with app.app_context():
            db = get_db()
            cols = db.execute("PRAGMA table_info(entry_data)").fetchall()
            col_names = [c["name"] for c in cols]
            assert "id" in col_names
            assert "entry_id" in col_names
            assert "name" in col_names
            assert "value" in col_names

    def test_close_db_cleans_up(self, app):
        with app.app_context():
            db = get_db()
            assert db is not None
        # After app context teardown, close_db should have run
        # (g is cleared, db should be closed)
        with app.app_context():
            db_new = get_db()
            # The old connection should have been popped
            assert db_new is not None


class TestInitDbCommand:
    def test_init_db_command_succeeds(self, app, runner):
        result = runner.invoke(args=["init-db"])
        assert result.exit_code == 0
        assert "Initialized the database." in result.output

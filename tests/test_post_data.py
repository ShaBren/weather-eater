"""Integration tests for app/post_data.py — weather data ingestion endpoint."""

from app.db import get_db
from tests.conftest import post_reading, METRIC_IDS


class TestPostData:
    def test_post_full_reading(self, client):
        post_reading(client)
        with client.application.app_context():
            db = get_db()
            count = db.execute("SELECT COUNT(*) FROM entry_data").fetchone()[0]
            # All 24 metrics should be stored
            assert count == 24

    def test_post_single_metric(self, client):
        client.get("/post_data?tempf=72.5")
        with client.application.app_context():
            db = get_db()
            rows = db.execute("SELECT name, value FROM entry_data").fetchall()
            assert len(rows) == 1
            assert rows[0]["name"] == "tempf"
            assert rows[0]["value"] == "72.5"

    def test_post_no_params(self, client):
        resp = client.get("/post_data")
        assert resp.status_code == 200
        with client.application.app_context():
            db = get_db()
            entry_count = db.execute("SELECT COUNT(*) FROM entry").fetchone()[0]
            data_count = db.execute("SELECT COUNT(*) FROM entry_data").fetchone()[0]
            assert entry_count == 1
            assert data_count == 0

    def test_post_unknown_metric_stored(self, client):
        client.get("/post_data?custom_metric=abc")
        with client.application.app_context():
            db = get_db()
            row = db.execute(
                "SELECT name, value FROM entry_data WHERE name='custom_metric'"
            ).fetchone()
            assert row is not None
            assert row["value"] == "abc"

    def test_post_data_returns_ok(self, client):
        resp = client.get("/post_data?tempf=72.5")
        assert resp.status_code == 200
        assert resp.data == b"OK"

    def test_multiple_entries_are_distinct(self, client):
        post_reading(client, tempf="70.0")
        post_reading(client, tempf="75.0")
        with client.application.app_context():
            db = get_db()
            entries = db.execute(
                "SELECT COUNT(*) as cnt FROM entry"
            ).fetchone()["cnt"]
            assert entries == 2
            temps = db.execute(
                "SELECT value FROM entry_data WHERE name='tempf' ORDER BY entry_id"
            ).fetchall()
            assert [t["value"] for t in temps] == ["70.0", "75.0"]

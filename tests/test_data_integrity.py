"""Data integrity and edge-case tests."""

import pytest
from datetime import datetime, timedelta
from app.db import get_db
from tests.conftest import (
    post_reading, seed_entries, seed_entry_with_timestamp,
    SAMPLE_READING, METRIC_IDS,
)


class TestDataIntegrity:
    def test_entry_created_timestamp_auto(self, client):
        """Verify DEFAULT CURRENT_TIMESTAMP is populated on insert via the API."""
        post_reading(client)
        with client.application.app_context():
            db = get_db()
            created = db.execute("SELECT created FROM entry").fetchone()["created"]
            assert created is not None
            # SQLite with PARSE_DECLTYPES returns a datetime object
            from datetime import datetime
            assert isinstance(created, datetime)
            # Should be within the last minute
            now = datetime.utcnow()
            assert (now - created).total_seconds() < 60

    def test_foreign_key_enforcement(self, client):
        """entry_data with invalid entry_id should fail when FK is enforced."""
        with client.application.app_context():
            db = get_db()
            db.execute("PRAGMA foreign_keys = ON")
            import sqlite3
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO entry_data (entry_id, name, value) VALUES (99999, 'x', 'y')"
                )
            db.execute("PRAGMA foreign_keys = OFF")

    def test_concurrent_inserts_no_conflict(self, client):
        """Two rapid inserts should not interfere."""
        seed_entries(client, 2)
        with client.application.app_context():
            db = get_db()
            count = db.execute("SELECT COUNT(*) FROM entry").fetchone()[0]
            assert count == 2

    def test_full_reading_roundtrip(self, client):
        """POST all 24 metrics, GET /api/latest, verify every metric ID with correct value."""
        post_reading(client)
        resp = client.get("/api/latest")
        data = resp.get_json()["data"]
        for metric_id, expected_value in SAMPLE_READING.items():
            assert metric_id in data, f"Missing in roundtrip: {metric_id}"
            assert data[metric_id]["raw"] == expected_value, (
                f"Value mismatch for {metric_id}: "
                f"expected {expected_value}, got {data[metric_id]['raw']}"
            )

    def test_special_characters_in_values(self, client):
        """Values with quotes, slashes, ampersands should be preserved."""
        client.get('/post_data?stationtype=WS-2000%2FPro&tempf=68%26Sunnier')
        resp = client.get("/api/latest")
        data = resp.get_json()["data"]
        # URL-decoded by Flask
        assert data["stationtype"]["raw"] == "WS-2000/Pro"
        assert data["tempf"]["raw"] == "68&Sunnier"

    def test_numeric_precision_preserved(self, client):
        """Float values should be stored and returned exactly as provided."""
        post_reading(client, baromabsin="29.923", tempf="72.579")
        resp = client.get("/api/latest")
        data = resp.get_json()["data"]
        assert data["baromabsin"]["raw"] == "29.923"
        assert data["tempf"]["raw"] == "72.579"

    def test_missing_metric_in_reading(self, client):
        """A sparse reading should store only what's provided."""
        client.get("/post_data?tempf=72.5&humidity=45")
        resp = client.get("/api/latest")
        result = resp.get_json()["data"]
        assert "tempf" in result
        assert "humidity" in result
        assert "baromabsin" not in result  # not sent
        assert len(result) == 2

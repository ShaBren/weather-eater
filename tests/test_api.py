"""Integration tests for app/api.py — JSON API endpoints."""

import json
from datetime import datetime, timedelta
from tests.conftest import (
    post_reading, seed_entries, seed_entry_with_timestamp,
    SAMPLE_READING, METRIC_IDS, STATION_METRICS,
)


# ── /api/latest ──────────────────────────────────────────────────────────

class TestApiLatest:
    def test_latest_returns_full_reading(self, client):
        post_reading(client)
        resp = client.get("/api/latest")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "id" in data
        assert "created" in data
        assert "data" in data
        # 23 visible metrics (24 total minus PASSKEY which we didn't send)
        assert len(data["data"]) == 24

    def test_latest_404_when_empty(self, client):
        resp = client.get("/api/latest")
        assert resp.status_code == 404
        assert resp.get_json()["error"] == "No data"

    def test_latest_formatted_fields(self, client):
        post_reading(client)
        resp = client.get("/api/latest")
        data = resp.get_json()["data"]["tempf"]
        assert data["raw"] == "72.5"
        assert data["formatted"] == "72.5 °F"
        assert data["unit"] == "degF"
        assert data["label"] == "Temperature (Outdoor)"

    def test_latest_hides_passkey(self, client):
        """PASSKEY is marked hidden and must not appear in API response."""
        client.get("/post_data?tempf=72.5&PASSKEY=abc123")
        resp = client.get("/api/latest")
        result = resp.get_json()
        assert "PASSKEY" not in result["data"]

    def test_latest_returns_most_recent(self, client):
        post_reading(client, tempf="70.0")
        post_reading(client, tempf="75.0")
        resp = client.get("/api/latest")
        data = resp.get_json()["data"]["tempf"]
        assert data["raw"] == "75.0"


# ── /api/history ─────────────────────────────────────────────────────────

class TestApiHistory:
    def test_history_pagination(self, client):
        seed_entries(client, 15)
        resp = client.get("/api/history?limit=5&offset=0")
        assert resp.status_code == 200
        entries = resp.get_json()
        assert len(entries) == 5

    def test_history_offset(self, client):
        seed_entries(client, 10)
        # First page
        resp1 = client.get("/api/history?limit=5&offset=0")
        page1_ids = [e["id"] for e in resp1.get_json()]
        # Second page
        resp2 = client.get("/api/history?limit=5&offset=5")
        page2_ids = [e["id"] for e in resp2.get_json()]
        # No overlap
        assert set(page1_ids).isdisjoint(page2_ids)
        # Total 10
        assert len(page1_ids) + len(page2_ids) == 10

    def test_history_date_filter(self, client):
        today = datetime.utcnow()
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)

        ts_yesterday = yesterday.strftime("%Y-%m-%d %H:%M:%S")
        ts_two_days_ago = two_days_ago.strftime("%Y-%m-%d %H:%M:%S")

        seed_entry_with_timestamp(client, ts_yesterday, tempf="70.0")
        seed_entry_with_timestamp(client, ts_two_days_ago, tempf="65.0")

        start = (yesterday - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        end = (yesterday + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        resp = client.get(f"/api/history?start={start}&end={end}")
        entries = resp.get_json()
        assert len(entries) == 1
        assert entries[0]["data"]["tempf"]["raw"] == "70.0"

    def test_history_empty_result(self, client):
        seed_entries(client, 2)
        # Filter to a far-future date range
        resp = client.get("/api/history?start=2099-01-01T00:00:00&end=2099-01-02T00:00:00")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_history_each_entry_has_expected_shape(self, client):
        post_reading(client)
        resp = client.get("/api/history?limit=1")
        entries = resp.get_json()
        assert len(entries) == 1
        e = entries[0]
        assert "id" in e
        assert "created" in e
        assert "data" in e
        assert "tempf" in e["data"]


# ── /api/daily_stats ─────────────────────────────────────────────────────

class TestApiDailyStats:
    def test_daily_stats_min_max(self, client):
        """Insert 3 tempf values for today and verify min/max."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        seed_entry_with_timestamp(client, f"{today} 10:00:00", tempf="68.0")
        seed_entry_with_timestamp(client, f"{today} 14:00:00", tempf="75.5")
        seed_entry_with_timestamp(client, f"{today} 18:00:00", tempf="71.2")

        resp = client.get("/api/daily_stats")
        assert resp.status_code == 200
        stats = resp.get_json()
        assert stats["min"] == 68.0
        assert stats["max"] == 75.5
        assert stats["date"] == today

    def test_daily_stats_no_data_today(self, client):
        """Seed only yesterday's data — should 404."""
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        seed_entry_with_timestamp(client, f"{yesterday} 12:00:00", tempf="70.0")

        resp = client.get("/api/daily_stats")
        assert resp.status_code == 404

    def test_daily_stats_ignores_other_metrics(self, client):
        """Only tempf values should be counted."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        seed_entry_with_timestamp(client, f"{today} 10:00:00",
                                  tempf="70.0", tempinf="68.0", temp2f="66.0")

        resp = client.get("/api/daily_stats")
        assert resp.status_code == 200
        stats = resp.get_json()
        # min and max should be of tempf only (70.0)
        assert stats["min"] == 70.0
        assert stats["max"] == 70.0


# ── /api/metrics ─────────────────────────────────────────────────────────

class TestApiMetrics:
    def test_metrics_returns_24_items(self, client):
        resp = client.get("/api/metrics")
        assert resp.status_code == 200
        metrics = resp.get_json()
        assert len(metrics) == 24

    def test_metrics_sorted_by_label(self, client):
        resp = client.get("/api/metrics")
        metrics = resp.get_json()
        labels = [m["label"] for m in metrics]
        assert labels == sorted(labels)

    def test_metrics_each_has_id_label_units(self, client):
        resp = client.get("/api/metrics")
        for m in resp.get_json():
            assert "id" in m
            assert "label" in m
            assert "units" in m

    def test_metrics_excludes_passkey(self, client):
        resp = client.get("/api/metrics")
        ids = {m["id"] for m in resp.get_json()}
        assert "PASSKEY" not in ids

    def test_metrics_matches_station_metrics(self, client):
        """Every metric from the STATION_METRICS canonical set should appear."""
        resp = client.get("/api/metrics")
        api_ids = {m["id"] for m in resp.get_json()}
        for metric in STATION_METRICS:
            assert metric["id"] in api_ids, f"Missing from /api/metrics: {metric['id']}"

"""Shared fixtures and test data for the Weather Eater test suite."""

import pytest
from datetime import datetime, timedelta
from app import create_app
from app.db import get_db, init_db

# ── Canonical test data: the user's real 24 station metrics ──────────────

STATION_METRICS = [
    {"id": "baromabsin", "label": "Barometer (Absolute)", "units": "inHg"},
    {"id": "batt2", "label": "Battery Status (Bedroom)", "units": "batt"},
    {"id": "battout", "label": "Battery Status (Outdoor)", "units": "batt"},
    {"id": "batt_co2", "label": "Battery Status (Unknown)", "units": "batt"},
    {"id": "humidity2", "label": "Humidity (Bedroom)", "units": "percentage"},
    {"id": "humidityin", "label": "Humidity (Office)", "units": "percentage"},
    {"id": "humidity", "label": "Humidity (Outdoor)", "units": "percentage"},
    {"id": "maxdailygust", "label": "Max Wind Gust (Today)", "units": "mph"},
    {"id": "dailyrainin", "label": "Rain (Daily)", "units": "inch"},
    {"id": "eventrainin", "label": "Rain (Event)", "units": "inch"},
    {"id": "hourlyrainin", "label": "Rain (Hourly)", "units": "inch"},
    {"id": "monthlyrainin", "label": "Rain (Montly)", "units": "inch"},
    {"id": "totalrainin", "label": "Rain (Total)", "units": "inch"},
    {"id": "weeklyrainin", "label": "Rain (Weekly)", "units": "inch"},
    {"id": "solarradiation", "label": "Solar Radiation", "units": "w/m^2"},
    {"id": "stationtype", "label": "Station Type", "units": "string"},
    {"id": "temp2f", "label": "Temperature (Bedroom)", "units": "degF"},
    {"id": "tempinf", "label": "Temperature (Office)", "units": "degF"},
    {"id": "tempf", "label": "Temperature (Outdoor)", "units": "degF"},
    {"id": "dateutc", "label": "Time of Measurement", "units": "time"},
    {"id": "uv", "label": "UV Index", "units": "int"},
    {"id": "winddir", "label": "Wind Direction", "units": "deg"},
    {"id": "windgustmph", "label": "Wind Gusts", "units": "mph"},
    {"id": "windspeedmph", "label": "Wind Speed", "units": "mph"},
]

METRIC_IDS = {m["id"] for m in STATION_METRICS}
HIDDEN_METRIC_IDS = {"PASSKEY"}

# ── Realistic sample reading ─────────────────────────────────────────────

SAMPLE_READING = {
    "baromabsin": "29.92",
    "batt2": "1",
    "battout": "1",
    "batt_co2": "1",
    "humidity2": "42",
    "humidityin": "38",
    "humidity": "45",
    "maxdailygust": "15.0",
    "dailyrainin": "0.05",
    "eventrainin": "1.25",
    "hourlyrainin": "0.00",
    "monthlyrainin": "2.50",
    "totalrainin": "45.30",
    "weeklyrainin": "0.75",
    "solarradiation": "450.5",
    "stationtype": "WS-2000",
    "temp2f": "68.5",
    "tempinf": "71.0",
    "tempf": "72.5",
    "dateutc": "2024-01-15 14:30:00",
    "uv": "3",
    "winddir": "180",
    "windgustmph": "12.0",
    "windspeedmph": "10.0",
}

# ── App fixture ──────────────────────────────────────────────────────────

@pytest.fixture
def app(tmp_path):
    """Create a Flask app with a temp-file SQLite database for testing.

    Uses tmp_path (not :memory:) so that multiple connections within the
    same test see the same tables.
    """
    db_path = tmp_path / "test.db"
    app = create_app(test_config={"DATABASE": str(db_path), "TESTING": True})
    with app.app_context():
        init_db()
    yield app


@pytest.fixture
def client(app):
    """Flask test client bound to the in-memory app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Flask CLI runner for testing CLI commands."""
    return app.test_cli_runner()


# ── Helper functions ─────────────────────────────────────────────────────

def post_reading(client, **overrides):
    """POST SAMPLE_READING (with optional overrides) to /post_data."""
    params = dict(SAMPLE_READING, **overrides)
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return client.get(f"/post_data?{qs}")


def seed_entries(client, count, base_dt=None, **overrides):
    """Insert *count* readings directly via the DB with staggered timestamps.

    Returns a list of entry IDs.
    """
    if base_dt is None:
        base_dt = datetime.utcnow()

    with client.application.app_context():
        db = get_db()
        entry_ids = []
        for i in range(count):
            ts = (base_dt - timedelta(hours=i)).strftime("%Y-%m-%d %H:%M:%S")
            db.execute("INSERT INTO entry (created) VALUES (?)", (ts,))
            db.commit()
            entry_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            entry_ids.append(entry_id)

            params = dict(SAMPLE_READING, **overrides)
            for name, value in params.items():
                db.execute(
                    "INSERT INTO entry_data (entry_id, name, value) VALUES (?, ?, ?)",
                    (entry_id, name, value),
                )
            db.commit()
    return entry_ids


def seed_entry_with_timestamp(client, ts, **overrides):
    """Insert a single entry with an explicit timestamp string.

    Returns the entry ID.
    """
    with client.application.app_context():
        db = get_db()
        db.execute("INSERT INTO entry (created) VALUES (?)", (ts,))
        db.commit()
        entry_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        params = dict(SAMPLE_READING, **overrides)
        for name, value in params.items():
            db.execute(
                "INSERT INTO entry_data (entry_id, name, value) VALUES (?, ?, ?)",
                (entry_id, name, value),
            )
        db.commit()
    return entry_id

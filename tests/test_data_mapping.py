"""Unit tests for app/data_mapping.py — pure functions with no DB or Flask dependencies."""

import pytest
from app.data_mapping import DataType, DataPoint, degree_to_dir, to_unit_string
from tests.conftest import STATION_METRICS, METRIC_IDS


# ── degree_to_dir ────────────────────────────────────────────────────────

class TestDegreeToDir:
    @pytest.mark.parametrize(
        "degree, expected",
        [
            (0, "N"),
            (11, "N"),
            (350, "N"),
            (360, "N"),
            (12, "NNE"),
            (34, "NNE"),
            (35, "NE"),
            (56, "NE"),
            (57, "ENE"),
            (79, "ENE"),
            (80, "E"),
            (101, "E"),
            (102, "ESE"),
            (124, "ESE"),
            (125, "SE"),
            (146, "SE"),
            (147, "SSE"),
            (169, "SSE"),
            (170, "S"),
            (191, "S"),
            (192, "SSW"),
            (214, "SSW"),
            (215, "SW"),
            (236, "SW"),
            (237, "WSW"),
            (259, "WSW"),
            (260, "W"),
            (281, "W"),
            (282, "WNW"),
            (304, "WNW"),
            (305, "NW"),
            (326, "NW"),
            (327, "NNW"),
            (349, "NNW"),
        ],
    )
    def test_all_boundaries(self, degree, expected):
        assert degree_to_dir(degree) == expected

    @pytest.mark.parametrize(
        "degree, expected",
        [
            (22.5, "NNE"),
            (5, "N"),
            (349, "NNW"),
            (-10, "N"),   # treated as > 349
            (400, "N"),   # > 349
        ],
    )
    def test_edge_cases(self, degree, expected):
        assert degree_to_dir(degree) == expected


# ── to_unit_string ───────────────────────────────────────────────────────

class TestToUnitString:
    def test_inch_singular(self):
        assert to_unit_string("inch", "1") == "1 inch"
        assert to_unit_string("inch", "1.0") == "1.0 inch"

    def test_inch_plural(self):
        # The code uses float(value) > 1, so 2 → plural, 1.0 → singular
        assert to_unit_string("inch", "2") == "2 inches"
        assert to_unit_string("inch", "2.5") == "2.5 inches"

    def test_batt_good(self):
        assert to_unit_string("batt", "1") == "Good"

    def test_batt_low(self):
        assert to_unit_string("batt", "0") == "Low"

    def test_deg_with_direction(self):
        result = to_unit_string("deg", "180")
        assert "180°" in result
        assert "S" in result

    def test_deg_with_north(self):
        result = to_unit_string("deg", "5")
        assert "5° N" == result

    def test_deg_with_west(self):
        result = to_unit_string("deg", "260")
        assert "260°" in result
        assert "W" in result

    @pytest.mark.parametrize(
        "unit, value, expected",
        [
            ("degF", "72.5", "72.5 °F"),
            ("mph", "10.0", "10.0 MPH"),
            ("inHg", "29.92", "29.92 inHg"),
            ("percentage", "45", "45%"),
            ("w/m^2", "450.5", "450.5 w/m^2"),
            ("string", "WS-2000", "WS-2000"),
            ("int", "3", "3"),
            ("time", "2024-01-15 14:30:00", "2024-01-15 14:30:00"),
        ],
    )
    def test_all_real_units(self, unit, value, expected):
        assert to_unit_string(unit, value) == expected

    def test_unknown_unit_falls_through(self):
        assert to_unit_string("furlongs_per_fortnight", "42") == "42"


# ── DataType definitions ─────────────────────────────────────────────────

class TestDataType:
    def test_all_real_metrics_exist(self):
        for metric in STATION_METRICS:
            assert metric["id"] in DataType, f"Missing: {metric['id']}"

    def test_no_extra_keys(self):
        """DataType should not contain stale/deleted metrics beyond the
        known set (24 station metrics + PASSKEY)."""
        expected_keys = METRIC_IDS | {"PASSKEY"}
        actual_keys = set(DataType.keys())
        extra = actual_keys - expected_keys
        assert not extra, f"Unexpected DataType keys: {extra}"

    def test_hidden_fields(self):
        assert DataType["PASSKEY"].hidden is True
        assert DataType["stationtype"].hidden is False
        assert DataType["tempf"].hidden is False
        hidden_count = sum(1 for dp in DataType.values() if dp.hidden)
        assert hidden_count == 1

    @pytest.mark.parametrize(
        "metric_id, expected_label",
        [
            ("tempf", "Temperature (Outdoor)"),
            ("humidity", "Humidity (Outdoor)"),
            ("winddir", "Wind Direction"),
            ("baromabsin", "Barometer (Absolute)"),
            ("dailyrainin", "Rain (Daily)"),
            ("uv", "UV Index"),
            ("windspeedmph", "Wind Speed"),
        ],
    )
    def test_labels_match(self, metric_id, expected_label):
        assert DataType[metric_id].name == expected_label

    def test_presentation_metrics_exist(self):
        """These are the metrics the dashboard shows by default."""
        dashboard_ids = {
            "tempf", "tempinf", "temp2f", "humidity", "humidityin",
            "humidity2", "baromabsin", "windspeedmph", "windgustmph",
            "winddir", "dailyrainin", "uv", "solarradiation",
            "maxdailygust", "battout", "batt2",
        }
        for mid in dashboard_ids:
            assert mid in DataType, f"Dashboard metric missing: {mid}"

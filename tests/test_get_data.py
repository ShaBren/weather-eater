"""Integration tests for app/get_data.py — plain-text latest reading endpoint."""

from tests.conftest import post_reading, METRIC_IDS


class TestGetData:
    def test_get_data_returns_text(self, client):
        post_reading(client)
        resp = client.get("/get_data")
        assert resp.status_code == 200
        # Should contain formatted temperature
        assert b"Temperature (Outdoor): 72.5" in resp.data

    def test_get_data_hides_passkey(self, client):
        """PASSKEY is marked hidden in DataType and must not appear."""
        # Post a reading that includes PASSKEY
        client.get("/post_data?tempf=72.5&PASSKEY=abc123&stationtype=WS-2000")
        resp = client.get("/get_data")
        assert b"PASSKEY" not in resp.data
        assert b"Station MAC Address" not in resp.data

    def test_get_data_includes_stationtype(self, client):
        """stationtype is not hidden and should appear."""
        client.get("/post_data?tempf=72.5&stationtype=WS-2000")
        resp = client.get("/get_data")
        assert b"Station Type" in resp.data

    def test_get_data_with_no_entries(self, client):
        resp = client.get("/get_data")
        assert resp.status_code == 200
        # Should return empty string or very minimal response
        assert resp.data.strip() == b""

    def test_get_data_formats_known_metrics(self, client):
        """Spot-check that several known metrics appear with correct formatting."""
        client.get(
            "/post_data?tempf=72.5&humidity=45&windspeedmph=10.0"
            "&baromabsin=29.92&winddir=180&dailyrainin=2.5"
        )
        resp = client.get("/get_data")
        text = resp.data.decode()
        assert "Temperature (Outdoor): 72.5 °F" in text
        assert "Humidity (Outdoor): 45%" in text
        assert "Wind Speed: 10.0 MPH" in text
        assert "Barometer (Absolute): 29.92 inHg" in text
        assert "180°" in text  # wind direction
        assert "Rain (Daily): 2.5 inches" in text

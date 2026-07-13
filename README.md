
# Weather Eater

Weather Eater is a small Flask application for collecting weather readings from an Ambient Weather-style station, storing them in SQLite, and displaying them in a lightweight dashboard with charts and recent-history views.

## What it does

- Accepts weather metric submissions from an external source
- Stores each reading as an entry with associated metric values
- Serves a browser-based dashboard for current conditions, recent data, and historical charts
- Exposes simple JSON endpoints for latest data, history, daily min/max, and available metrics

## Project structure

- [app/__init__.py](app/__init__.py) creates the Flask app and registers the routes
- [app/post_data.py](app/post_data.py) accepts incoming readings
- [app/get_data.py](app/get_data.py) returns the latest reading as plain text
- [app/api.py](app/api.py) exposes JSON API endpoints
- [app/db.py](app/db.py) manages the SQLite connection and initialization
- [app/data_mapping.py](app/data_mapping.py) defines supported metric names, labels, and units
- [app/static/](app/static/) contains the dashboard HTML, CSS, and JavaScript
- [importer.py](importer.py) imports an older SQLite database into the current schema

## Requirements

- Python 3.11+
- Docker and Docker Compose (recommended)

## Quick start with Docker

1. Clone the repository and change into it:

   ```bash
   git clone https://github.com/ShaBren/weather-eater.git
   cd weather-eater
   ```

2. Build and start the app:

   ```bash
   docker compose up --build -d
   ```

3. Initialize the SQLite database schema:

   ```bash
   docker compose exec weather flask init-db
   ```

4. Open the dashboard in your browser:

   - http://localhost:4902/

The app persists its SQLite database in the local instance folder, so data survives container restarts.

## Sending weather data

The ingestion endpoint accepts query parameters for each metric. Any metric name is stored, but the frontend and API know how to format the known set defined in [app/data_mapping.py](app/data_mapping.py).

Example:

```bash
curl "http://localhost:4902/post_data?tempf=72.5&humidity=45&windspeedmph=10&baromabsin=29.92"
```

The response is plain text: `OK`.

## API endpoints

- `GET /api/latest` returns the most recent entry with formatted values
- `GET /api/history?start=...&end=...&limit=...&offset=...` returns a paginated history of entries
- `GET /api/daily_stats` returns today's min/max temperature for `tempf`
- `GET /api/metrics` returns the list of supported dashboard metrics
- `GET /get_data` returns the latest reading as a plain-text summary

## Database schema

The app uses SQLite with two main tables:

- `entry`: one row per weather reading, with a timestamp
- `entry_data`: one row per metric value associated with an entry

This structure makes it straightforward to store arbitrary weather metrics over time while still keeping the data queryable.

## Importing an older database

If you have an older SQLite database and want to migrate it into the current schema, run:

```bash
python importer.py /path/to/old/weather.sqlite
```

The importer creates the new database at `instance/weather.sqlite` and copies rows from the legacy database.

## Development notes

- The dashboard is a client-side single-page app served from [app/static/](app/static/)
- Chart and dashboard preferences are cached in the browser using local storage
- The app is intentionally lightweight and meant to be run locally or on a small host

## Development proxy

[dev_proxy.py](dev_proxy.py) is a standalone script for developing the SPA against a live remote API without CORS issues. It serves `app/static/` directly and forwards any `/api/*` requests to a configurable upstream host.

To use it:

```bash
pip install requests flask
python dev_proxy.py
```

Then open http://localhost:5000/ in your browser. The SPA&#8217;s existing relative `/api/...` calls are handled by the proxy — no code changes needed.

The upstream target defaults to `http://weather.cubelime.com` and can be changed by editing the `LIVE_API_URL` variable at the top of the script.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.


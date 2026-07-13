
# 🌦️ Ambient Weather Station Dashboard (Weather-Eater)

A robust system that ingests time-series weather reports from an Ambient Weather station, stores the data in a structured SQLite database, and serves a modern Single Page Application (SPA) dashboard for real-time visualization and historical analysis.

## ✨ Features

*   **Automated Data Ingestion:** Securely receives streamed weather metrics via HTTP POST requests.
*   **Structured Persistence:** Uses an efficient key-value model (entry/entry_data) in SQLite to store time-series data.
*   **Dynamic Dashboard SPA:** Serves a responsive Single Page Application that visualizes the latest readings and historical trends.
*   **Advanced API Endpoints:** Dedicated endpoints for fetching paginated history, daily statistics (Min/Max), and metric metadata.

## 🚀 Getting Started

### Prerequisites

*   Python 3.x
*   Docker Engine
*   Docker Compose

### Installation via Docker Compose

The recommended way to run this project is using docker-compose. This handles dependency management and database initialization automatically.

1.  **Clone the repository:**
    
bash
git clone [repository_url] weather-eater
cd weather-eater


2.  **Build and Run Services:**
    
bash
docker compose up --build -d


### Usage Guide (How to Use It)

#### 1. Ingesting Weather Data (The Sender)
To send a new set of weather reports, your external data source (e.g., a script running on the station gateway) must make a **POST** request to the API endpoint: `/post_data`.

**Example Request:**
http
POST /post_data?temperature=72.5&humidity=45&wind=10&pressure=1012 HTTP/1.1
Host: localhost:5000
Content-Type: application/x-www-form-urlencoded



#### 2. Single Page Application (SPA) Dashboard

The dashboard is served by the Flask backend and automatically reads data from the database whenever a user accesses it. It relies on three key API calls to function:

**A. Viewing Latest Readings:**
When first loaded, the dashboard hits the `/get_data endpoint. This call retrieves the most recent set of metrics (the latest weather snapshot) and formats them with appropriate units for immediate display.

*   **Endpoint:**GET /get_data
*   **Function:** Retrieves a single formatted string containing all key/value pairs from the current reading cycle.

**B. Viewing Historical Data (Charting):**
For trend analysis, charts require historical data over a specific time period. The API supports robust querying for this purpose:

*   **Endpoint:**GET /api/history
*   **Parameters:** You can filter by date range?start=...&end=...`), and manage large datasets using pagination?limit=X&offset=Y`).
*   **Data Structure:** Returns a JSON array, where each object represents a full weather entry (including timestamp) and contains nested data for every metric recorded at that time.

**C. System Configuration / Metrics Discovery:**
This endpoint is used by the SPA itself during initialization to ensure it knows which metrics to display, even if they are added or removed from your station's reporting cycle.

*   **Endpoint:**GET /api/metrics
*   **Function:** Returns a JSON list of all active and non-hidden metrics (ID, Label, Units), allowing the dashboard UI to dynamically build its input fields and labels without code changes.

## ⚙️ Technical Architecture Deep Dive (For Developers)

### Database Schema

The project utilizes an SQLite database optimized for time-series data, structured across two main tables:

1.  **entry**: Stores the metadata for a single weather reading event (the timestamp).
    *   id`: Primary Key
    *   created`: The precise date and time of the measurement (UTC).
2.  **entry_data**: Stores the actual key/value metrics associated with an entry ID.
    *   entry_id`: Foreign Key linking back to entry`.
    *   name`: The metric name (e.g., 'temperature', 'humidity').
    *   value`: The raw recorded value.

### Core Components Breakdown

| Component | File(s) | Responsibility | Description |
| :--- | :--- | :--- | :--- |
| **Ingestion Layer** |post_data.py | **Write/Save Data** | Receives key-value pairs from external sources, creates a single entry`, and saves all metrics as associated entry_data records in an atomic transaction. |
| **Data Retrieval API** |api.py | **Read/Query Data** | Provides advanced endpoints/history`, `/daily_stats`) to query specific time ranges, calculate aggregates (Min/Max), or list available metrics for the dashboard. |
| **Dashboard Read Endpoint**|get_data.py | **Display Format** | A simplified endpoint that fetches only the *most recent* reading and formats it into a display-ready string using predefined data mapping rules. |
| **Data Mapping & Logic** |data_mapping.py`,schema.sql | **Model/Validation** | Defines which metrics are valid (DataType`) and controls how raw values are transformed (e.g., converting 'F' to '°F'). |

## 📦 Deployment Details

### Dockerization Strategy

The use ofDockerfile anddocker-compose.yml ensures that the application runs consistently regardless of the host operating system, managing dependencies(requirements.txt) and networking transparently.

*   **Docker Compose:** Orchestrates the entire stack, ensuring the database is initialized and the Flask application server (Gunicorn) starts correctly in production mode.

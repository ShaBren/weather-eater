from flask import Blueprint, request, jsonify
from .db import get_db
from .data_mapping import DataType, to_unit_string
from datetime import datetime

api = Blueprint('api', __name__)

def _format_entry(entry_id, created, data_rows):
    """Convert raw rows into a dict with formatted values."""
    data = {}
    for name, value in data_rows:
        if name in DataType:
            dt = DataType[name]
            if dt.hidden:
                continue
            data[name] = {
                'raw': value,
                'formatted': to_unit_string(dt.units, value),
                'unit': dt.units,
                'label': dt.name
            }
    return {
        'id': entry_id,
        'created': created,
        'data': data
    }

@api.route('/latest')
def latest():
    db = get_db()
    # Get latest entry
    entry = db.execute(
        "SELECT id, created FROM entry ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not entry:
        return jsonify({'error': 'No data'}), 404

    rows = db.execute(
        "SELECT name, value FROM entry_data WHERE entry_id = ?",
        (entry['id'],)
    ).fetchall()
    result = _format_entry(entry['id'], entry['created'], rows)
    return jsonify(result)

@api.route('/history')
def history():
    db = get_db()
    # Query parameters
    start = request.args.get('start')      # ISO format, e.g. 2023-01-01T00:00:00
    end = request.args.get('end')
    limit = request.args.get('limit', default=100, type=int)
    offset = request.args.get('offset', default=0, type=int)

    # Build WHERE clause
    where = []
    params = []
    if start:
        where.append("created >= ?")
        params.append(start)
    if end:
        where.append("created <= ?")
        params.append(end)
    where_clause = "WHERE " + " AND ".join(where) if where else ""

    # Query entries (with limit/offset)
    sql = f"""
        SELECT id, created FROM entry
        {where_clause}
        ORDER BY created DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    entries = db.execute(sql, params).fetchall()

    if not entries:
        return jsonify([])

    # Fetch all data for these entries in one go
    entry_ids = [e['id'] for e in entries]
    placeholders = ','.join(['?'] * len(entry_ids))
    rows = db.execute(
        f"SELECT entry_id, name, value FROM entry_data WHERE entry_id IN ({placeholders})",
        entry_ids
    ).fetchall()

    # Group by entry_id
    data_by_entry = {}
    for r in rows:
        data_by_entry.setdefault(r['entry_id'], []).append((r['name'], r['value']))

    # Assemble response
    result = []
    for e in entries:
        entry_data = data_by_entry.get(e['id'], [])
        result.append(_format_entry(e['id'], e['created'], entry_data))

    return jsonify(result)

@api.route('/daily_stats')
def daily_stats():
    db = get_db()
    # Use UTC date (since timestamps are stored in UTC)
    today_utc = datetime.utcnow().strftime('%Y-%m-%d')
    start = f"{today_utc} 00:00:00"
    end = f"{today_utc} 23:59:59"

    rows = db.execute(
        """SELECT value FROM entry_data 
           WHERE name = 'tempf' 
           AND entry_id IN (
               SELECT id FROM entry 
               WHERE created BETWEEN ? AND ?
           )""",
        (start, end)
    ).fetchall()

    if not rows:
        return jsonify({'error': 'No data for today'}), 404

    temps = [float(row['value']) for row in rows]
    return jsonify({
        'date': today_utc,
        'min': round(min(temps), 1),
        'max': round(max(temps), 1)
    })

@api.route('/metrics')
def list_metrics():
    """Return all non-hidden data points from data_mapping."""
    from .data_mapping import DataType
    metrics = []
    for key, dp in DataType.items():
        if not dp.hidden:
            metrics.append({
                'id': key,
                'label': dp.name,
                'units': dp.units
            })
    return jsonify(sorted(metrics, key=lambda x: x['label']))

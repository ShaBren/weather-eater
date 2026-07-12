from flask import Blueprint
from weather.db import get_db
from weather.data_mapping import DataType, to_unit_string

get_data = Blueprint('get_data', __name__, template_folder='templates')

@get_data.route('/get_data')
def save_data():
    db = get_db()
    rows = db.execute(
        "SELECT name, value FROM entry_data "
        "WHERE entry_id=(SELECT id FROM entry ORDER BY id DESC LIMIT 1);"
    ).fetchall()
    
    data = ""
    for name, value in rows:
        if name in DataType:
            dt = DataType[name]
            if dt.hidden:
                continue
            data += f"{dt.name}: {to_unit_string(dt.units, value)}\n"
    return data

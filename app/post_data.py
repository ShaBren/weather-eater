from flask import Blueprint, request
from .db import get_db

post_data = Blueprint('post_data', __name__, template_folder='templates')

@post_data.route('/post_data')
def save_data():
    db = get_db()
    db.execute("INSERT INTO entry DEFAULT VALUES;")
    db.commit()
    entry_id = db.execute("SELECT last_insert_rowid();").fetchone()[0]
    
    for k, v in request.args.items():
        db.execute(
            "INSERT INTO entry_data (entry_id, name, value) VALUES (?, ?, ?);",
            (entry_id, k, v)
        )
    db.commit()
    return "OK"

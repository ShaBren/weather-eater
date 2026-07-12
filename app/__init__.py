import os
from flask import Flask, send_from_directory
from . import db

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'weather.sqlite'),
    )

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    # ensure instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)

    # Register blueprints
    from .post_data import post_data
    from .get_data import get_data
    from .api import api
    app.register_blueprint(post_data)
    app.register_blueprint(get_data)
    app.register_blueprint(api, url_prefix='/api')

    # Serve SPA from static folder
    @app.route('/')
    def root():
        return send_from_directory(app.static_folder, 'index.html')

    db.init_app(app)
    return app

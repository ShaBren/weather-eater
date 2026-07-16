"""Tests for the Flask app factory (app/__init__.py)."""

from flask import Flask


class TestAppFactory:
    def test_create_app_returns_flask_app(self, app):
        assert isinstance(app, Flask)

    def test_test_config_overrides_database(self, app):
        # The test config should use a temp file, not the default weather.sqlite
        assert "weather.sqlite" not in app.config["DATABASE"]
        assert app.config["DATABASE"].endswith(".db")

    def test_instance_path_exists(self, app):
        import os
        assert os.path.isdir(app.instance_path)

    def test_blueprints_registered(self, app):
        """Verify all three blueprints are registered."""
        blueprints = {bp.name for bp in app.iter_blueprints()}
        assert "post_data" in blueprints
        assert "get_data" in blueprints
        assert "api" in blueprints

    def test_root_serves_index_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Weather Station Dashboard" in resp.data
        assert b"<!DOCTYPE html>" in resp.data

    def test_static_js_served(self, client):
        resp = client.get("/static/script.js")
        assert resp.status_code == 200
        assert b"DOMContentLoaded" in resp.data or b"addEventListener" in resp.data

    def test_static_css_served(self, client):
        resp = client.get("/static/style.css")
        assert resp.status_code == 200
        assert b"font-family" in resp.data

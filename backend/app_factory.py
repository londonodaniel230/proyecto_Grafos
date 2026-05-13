import os

from flask import Flask

from .routes import api_bp


def create_app():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    static_dir = os.path.join(root_dir, "frontend")

    app = Flask(__name__, static_folder=static_dir, static_url_path="")
    app.register_blueprint(api_bp)

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    return app

import logging
import os
from logging.handlers import RotatingFileHandler
from flask import Flask, send_from_directory
from config import config_by_name
from .extensions import scheduler
from .extensions import db
from app.services.keys import build_jwks_for_accounts
from app.models import ZoomAccount


def create_app(config_name: str | None = None) -> Flask:
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    _configure_logging(app)
    _init_extensions(app)
    _register_blueprints(app)
    _register_app_routes(app) 
    _init_scheduler(app)

    app.logger.info(f"Zoomly server started in '{config_name}' mode")
    return app

def _configure_logging(app: Flask) -> None:
    log_level = getattr(logging, app.config.get("LOG_LEVEL", "DEBUG").upper(), logging.DEBUG)
    log_file = app.config.get("LOG_FILE", "./logs/zoomly.log")

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=3)
    file_handler.setFormatter(formatter)

    app.logger.setLevel(log_level)
    app.logger.addHandler(stream_handler)
    app.logger.addHandler(file_handler)


def _init_extensions(app: Flask) -> None:
    db.init_app(app)

    with app.app_context():
        from . import models


def _init_scheduler(app: Flask) -> None:

    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        if not scheduler.running:
            scheduler.start()
            app.logger.info("APScheduler started")

        import atexit
        atexit.register(lambda: scheduler.shutdown(wait=False))


def _register_blueprints(app: Flask) -> None:
    from .blueprints.auth import auth_bp
    from .blueprints.webhooks import webhooks_bp
    from .blueprints.openemr import openemr_bp
    from .blueprints.zoom import zoom_bp
    from .blueprints.config import config_bp
    from .blueprints.audit import audit_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(webhooks_bp)
    app.register_blueprint(openemr_bp)
    app.register_blueprint(zoom_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(audit_bp)

def _register_app_routes(app: Flask) -> None:


    @app.route("/health")
    def health():
        return {"status": "ok", "env": app.config.get("ENV", "development")}


    @app.route("/.well-known/jwks.json")
    def jwks(): 
        accounts = ZoomAccount.query.filter_by(is_active=True).all()
        return build_jwks_for_accounts(accounts), 200
    

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_react(path):
        static_folder = app.static_folder or os.path.join(app.root_path, "static")
        if path and os.path.exists(os.path.join(static_folder, path)):
            return send_from_directory(static_folder, path)
        return send_from_directory(static_folder, "index.html")
import logging
import os
from flask import Flask
from .extensions import db
from config import config_by_name


def create_app(config_name: str | None = None) -> Flask:
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    _configure_logging(app)
    _init_extensions(app)
    _register_blueprints(app)
    _register_health_check(app)

    app.logger.info(f"Zoomly server started in '{config_name}' mode")
    return app


def _configure_logging(app: Flask) -> None:
    log_level = getattr(logging, app.config.get("LOG_LEVEL", "DEBUG").upper(), logging.DEBUG)
    log_file = app.config.get("LOG_FILE", "./logs/zoomly.log")

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file),
        ]
    )


def _init_extensions(app: Flask) -> None:
    db.init_app(app)

    with app.app_context():
        from . import models
        
        db.create_all()


def _register_blueprints(app: Flask) -> None:
    from .blueprints.auth import auth_bp
    from .blueprints.webhooks import webhooks_bp
    from .blueprints.openemr import openemr_bp
    from .blueprints.zoom import zoom_bp
    from .blueprints.config import config_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(webhooks_bp)
    app.register_blueprint(openemr_bp)
    app.register_blueprint(zoom_bp)
    app.register_blueprint(config_bp)


def _register_health_check(app: Flask) -> None:
    @app.route("/health")
    def health():
        return {"status": "ok", "env": app.config.get("ENV", "development")}
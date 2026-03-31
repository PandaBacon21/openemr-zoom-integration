import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "8UocKHpyRzWREC64NKIH")
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///zoomly.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Zoom
    ZOOM_ACCOUNT_ID = os.environ.get("ZOOM_ACCOUNT_ID")
    ZOOM_CLIENT_ID = os.environ.get("ZOOM_CLIENT_ID")
    ZOOM_CLIENT_SECRET = os.environ.get("ZOOM_CLIENT_SECRET")

    # OpenEMR
    OPENEMR_BASE_URL = os.environ.get("OPENEMR_BASE_URL", "http://openemr:8080")
    OPENEMR_CLIENT_ID = os.environ.get("OPENEMR_CLIENT_ID")
    OPENEMR_CLIENT_SECRET = os.environ.get("OPENEMR_CLIENT_SECRET")

    # SMART / JWKS
    JWKS_KEY_PATH = os.environ.get("JWKS_KEY_PATH", "./keys/private.pem")
    APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5000")

    # Logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG")
    LOG_FILE = os.environ.get("LOG_FILE", "./logs/zoomly.log")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
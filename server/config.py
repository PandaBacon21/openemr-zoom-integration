import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Security 
    KEYS_BASE_DIR = os.environ.get("KEYS_BASE_DIR", "/app/keys")
    ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")

    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() in ("true", "1")

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///zoomly.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Zoom
    ZOOM_TOKEN_URL = os.environ.get("ZOOM_TOKEN_URL")
    ZOOM_API_BASE_URL = os.environ.get("ZOOM_API_BASE_URL")
    
    ZOOM_ACCOUNT_ID = os.environ.get("ZOOM_ACCOUNT_ID")
    ZOOM_CLIENT_ID = os.environ.get("ZOOM_CLIENT_ID")
    ZOOM_CLIENT_SECRET = os.environ.get("ZOOM_CLIENT_SECRET")
    ZOOM_WEBHOOK_SECRET_TOKEN = os.environ.get("ZOOM_WEBHOOK_SECRET_TOKEN")

    # OpenEMR
    OPENEMR_BASE_URL = os.environ.get("OPENEMR_BASE_URL", "http://localhost:8300")
    OPENEMR_FHIR_BASE_URL = os.environ.get("OPENEMR_FHIR_BASE_URL", "http://localhost:8300/apis/default/fhir")
    OPENEMR_CLIENT_ID = os.environ.get("OPENEMR_CLIENT_ID")
    OPENEMR_PUBLIC_URL = os.environ.get("OPENEMR_PUBLIC_URL")

    # SMART / JWKS
    JWKS_PRIVATE_PATH = os.environ.get("JWKS_PRIVATE_PATH", "./keys/private.pem")
    KEY_ID = os.environ.get("KEY_ID", "openemr-integration-key-1")

    # Integration Service Public URL
    APP_PUBLIC_URL = os.environ.get("APP_PUBLIC_URL", "http://localhost:5000")

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
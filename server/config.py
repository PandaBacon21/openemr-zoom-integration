import os
from dotenv import load_dotenv

load_dotenv()

OPENEMR_DB_URI = (
        f"mysql+pymysql://"
        f"{os.environ.get('OPENEMR_DB_USER', 'openemr')}:"
        f"{os.environ.get('OPENEMR_DB_PASS', 'openemr')}@"
        f"{os.environ.get('OPENEMR_DB_HOST', 'mariadb')}:"
        f"{os.environ.get('OPENEMR_DB_PORT', '3306')}/"
        f"{os.environ.get('OPENEMR_DB_NAME', 'openemr')}"
    )

def _db_url():
        _db_url = os.environ.get("DATABASE_URL")
        if not _db_url: 
            raise RuntimeError("DATABASE_URL env variable is not set")
        
        if _db_url.startswith("postgres://"):
            _db_url = _db_url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif _db_url.startswith("postgresql://"):
            _db_url = _db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return _db_url

class Config:
    # Security 
    KEYS_BASE_DIR = os.environ.get("KEYS_BASE_DIR", "/app/keys")
    ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")

    # Protected Endpoints
    API_KEY = os.environ.get("API_KEY")

    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY")
    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() in ("true", "1")

    # Database
    SQLALCHEMY_DATABASE_URI = _db_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        # Sized for the gevent worker (100 concurrent greenlets). SQLAlchemy
        # defaults (pool_size=5 + max_overflow=10) would starve the pool under
        # bursts; bumping both keeps queries from queueing on connection checkout.
        "pool_size": 20,
        "max_overflow": 30,
        # Validate connections on checkout — long-lived greenlets can hold
        # idle connections across CTI sessions; Postgres may close them
        # server-side without the client noticing.
        "pool_pre_ping": True,
        # Force recycling after 30 min to dodge Postgres's idle timeout.
        "pool_recycle": 1800,
    }

    # OpenEMR
    OPENEMR_BASE_URL = os.environ.get("OPENEMR_BASE_URL", "http://localhost:8300")
    OPENEMR_FHIR_BASE_URL = os.environ.get("OPENEMR_FHIR_BASE_URL", "http://localhost:8300/apis/default/fhir")
    OPENEMR_CLIENT_ID = os.environ.get("OPENEMR_CLIENT_ID")
    OPENEMR_PUBLIC_URL = os.environ.get("OPENEMR_PUBLIC_URL")

    # OpenEMR for direct database connection for appointment type retrieval
    OPENEMR_DB_URI = OPENEMR_DB_URI

    OPENEMR_SCOPES = os.environ.get("OPENEMR_SCOPES", "").split()
    # SMART / JWKS
    KEYS_BASE_DIR = os.environ.get("KEYS_BASE_DIR", "/app/keys")

    # Integration Service Public URL
    APP_PUBLIC_URL = os.environ.get("APP_PUBLIC_URL", "http://localhost:5000")
    APP_INTERNAL_URL = os.environ.get("APP_INTERNAL_URL", "http://zoom-bridge:5000")

    # OpenEMR -> Flask Secret
    OPENEMR_FLASK_SECRET = os.environ.get("OPENEMR_FLASK_SECRET")

    # Logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG")
    LOG_FILE = os.environ.get("LOG_FILE", "./logs/zoomly.log")

    # React Config Page
    CONFIG_ADMIN_PASSWORD = os.environ.get("CONFIG_ADMIN_PASSWORD")
    CONFIG_JWT_SECRET = os.environ.get("CONFIG_JWT_SECRET")

    # DbGate DB browser (reverse-proxied at /admin/db) — non-prod only.
    # Default off so a prod deploy without the flag never exposes the browser.
    ENABLE_DBGATE = os.environ.get("ENABLE_DBGATE", "false").lower() in ("true", "1")

    # Epic-ZCC CTI middleware. When off the `/zoomly/<id>/interconnect-amcurprd-oauth/*`
    # blueprint is not registered, so every Epic-shaped endpoint returns 404.
    # Default off
    ENABLE_EPIC_ZCC = os.environ.get("ENABLE_EPIC_ZCC", "false").lower() in ("true", "1")

    # Fixed client ID registered in the Zoom App in Epic's Marketplace
    EPIC_ZCC_CLIENT_ID = os.environ.get("EPIC_ZCC_CLIENT_ID")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
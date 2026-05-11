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


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
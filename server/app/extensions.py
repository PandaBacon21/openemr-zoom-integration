from flask import current_app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from apscheduler.schedulers.background import BackgroundScheduler

db = SQLAlchemy()
scheduler = BackgroundScheduler()

def get_encryption_key():
    """
    Returns the encryption key for EncryptedType fields. 
    Must be a callable for SQLAlchemy-Utils
    """
    key = current_app.config.get("ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("ENCRYPTION_KEY is not configured")
    return key


def get_openemr_db_engine():
    """
    Returns a SQLAlchemy engine connected to OpenEMR's MariaDB.
    Used for direct DB queries when no API endpoint exists.

    Memoized on the Flask app so all 40+ callsites share one engine and its
    connection pool. A fresh engine per call (the previous behavior) would
    burn a TCP + MySQL auth handshake (~5-50ms) on every query and risk
    connection storms under the gevent worker.
    """
    app = current_app._get_current_object()  # type: ignore[attr-defined]
    if not hasattr(app, "_openemr_engine"):
        app._openemr_engine = create_engine(
            app.config["OPENEMR_DB_URI"],
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,
            pool_recycle=1800,
        )
    return app._openemr_engine
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
    """
    return create_engine(current_app.config["OPENEMR_DB_URI"])
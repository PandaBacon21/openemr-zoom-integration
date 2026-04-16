from flask import current_app
from flask_sqlalchemy import SQLAlchemy
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
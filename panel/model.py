from datetime import datetime, timezone
from . import db
import sqlalchemy as sql

# db: sql = db

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    enabled = db.Column(db.Boolean, default=True)
    prompt = db.Column(db.Text)


class API_KEYS(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(120))
    key = db.Column(db.String(350))
    updated = db.Column(db.DateTime(True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Ignored_Accounts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String(120), unique=True)


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


class UserMemory(db.Model):
    """Long-term per-user facts (name, country, UID...) so the bot never forgets them."""
    __tablename__ = 'user_memory'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.BigInteger, nullable=False, index=True)
    key = db.Column(db.String(60), nullable=False)
    value = db.Column(db.Text)
    updated = db.Column(db.DateTime(True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    __table_args__ = (db.UniqueConstraint('user_id', 'key', name='uq_user_memory_user_key'),)

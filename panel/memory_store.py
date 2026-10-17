"""
Storage for long-term user memory.

Uses SQLAlchemy Core on the engine directly (not db.session) on purpose:
the panel listens to every db.session commit to schedule a settings
refresh, and memory writes happen on every chat message, which must not
trigger that.
"""

from datetime import datetime, timezone
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from . import app, db
from .model import UserMemory


def load_facts(user_id: int) -> dict:
    try:
        with app.app_context():
            tbl = UserMemory.__table__
            with db.engine.connect() as conn:
                rows = conn.execute(select(tbl.c.key, tbl.c.value).where(tbl.c.user_id == user_id)).all()
            return {k: v for k, v in rows if v}
    except Exception as e:
        print(f'[memory] load failed for {user_id}: {e}', flush=True)
        return {}


def save_facts(user_id: int, facts: dict):
    if not facts:
        return
    try:
        with app.app_context():
            tbl = UserMemory.__table__
            now = datetime.now(timezone.utc)
            with db.engine.begin() as conn:
                for key, value in facts.items():
                    stmt = pg_insert(tbl).values(user_id=user_id, key=str(key)[:60], value=str(value), updated=now)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['user_id', 'key'],
                        set_=dict(value=stmt.excluded.value, updated=now),
                    )
                    conn.execute(stmt)
    except Exception as e:
        print(f'[memory] save failed for {user_id}: {e}', flush=True)


def forget_user(user_id: int):
    try:
        with app.app_context():
            with db.engine.begin() as conn:
                conn.execute(delete(UserMemory.__table__).where(UserMemory.__table__.c.user_id == user_id))
    except Exception as e:
        print(f'[memory] forget failed for {user_id}: {e}', flush=True)

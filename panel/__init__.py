import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
FLASK_SECRET_KEY = os.environ.get('FLASK_SECRET_KEY')
DATABASE_URL = os.environ.get('DATABASE_URL')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
if not FLASK_SECRET_KEY or not DATABASE_URL or not ADMIN_PASSWORD:
    raise RuntimeError('Missing required environment variable(s): FLASK_SECRET_KEY, DATABASE_URL, ADMIN_PASSWORD must all be set.')
app.secret_key = FLASK_SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PASSWORD'] = ADMIN_PASSWORD

db = SQLAlchemy(app)

from .model import Settings, API_KEYS, Ignored_Accounts

@app.context_processor
def global_context():
    return dict(
        script_start='<script>',
        script_end='</script>',
    )

from . import routes

with app.app_context():
    db.create_all()
    if not Settings.query.first():
        db.session.add(Settings(enabled=True, prompt=''))
        db.session.commit()




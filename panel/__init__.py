from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'oilr0-jei4i8-isiwiri-mri48wufj'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://neondb_owner:npg_0HSQqacziG7F@ep-aged-unit-a12kc26d-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PASSWORD'] = '@Manbadman365#'

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




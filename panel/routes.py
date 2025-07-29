from . import app, db, Settings, API_KEYS, Ignored_Accounts
from flask import request, render_template, redirect, flash
from datetime import datetime, timezone
from threading import Thread
from time import sleep
from contextlib import nullcontext
from sqlalchemy import event
import hashlib, random, asyncio, nest_asyncio
from .api_checker import checkAPI
nest_asyncio.apply()


AUTH_HASH = hashlib.sha256(app.config['PASSWORD'].encode()).hexdigest()
PROVIDERS = dict(
    groq='Groq.com',
    gemini='Gemini (Google AI Studio)',
    cloudflare='Cloudflare AI',
    together='Together.ai'
)
DATA_UPDATE_ID = None
API_CHECK_DATA = dict(running=False, data='', last_checked=None)


def set_data(with_context = True):
    def map_ignore(x):
        try: return int(x.identifier)
        except: return x.identifier.replace('@', '')

    with app.app_context() if with_context else nullcontext():
        data_settings = Settings.query.first()
        data_api_keys = API_KEYS.query.all()
        data_ignore_list = Ignored_Accounts.query.all()
        app.config['AI_SETTINGS'] = dict(enabled=data_settings.enabled, prompt=data_settings.prompt)
        app.config['AI_API_KEYS'] = list(map(lambda x: (x.provider, x.key), data_api_keys))
        app.config['AI_IGNORE_LIST'] = list(map(map_ignore, data_ignore_list))

def update_data_in_background(delay = 30):
    global DATA_UPDATE_ID
    DATA_UPDATE_ID = random.randint(10000000, 999999999)
    def pre_func(d, dui):
        sleep(d)
        if DATA_UPDATE_ID == dui:
            set_data()

    Thread(target=pre_func, args=(delay, DATA_UPDATE_ID), daemon=True).start()

set_data()

@event.listens_for(db.session.__class__, "after_commit")
def after_commit(session):
    update_data_in_background()


def time_ago_short(dt: datetime) -> str:
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt

    seconds = int(delta.total_seconds())

    if seconds < 60:
        return f"{seconds}s"

    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    parts = []
    if days: parts.append(f"{days}d")
    if hours: parts.append(f"{hours}h")
    if minutes and len(parts) < 2: parts.append(f"{minutes}m")
    if seconds and len(parts) < 2: parts.append(f"{seconds}s")

    return ' '.join(parts[:2])

def is_logedin():
    s = request.cookies.get('auth')
    if s == AUTH_HASH:
        return True
    return False


@app.route('/', methods=['GET', 'POST'])
def home():
    if not is_logedin(): return redirect('/login')
    dt = Settings.query.first()
    if request.method == 'POST':
        if request.form.get('purge') == 'yes':
            set_data(False)
            flash('Cache Refreshed Successfully', 'success')
            return redirect('/')
        enabled = request.form.get('enabled') == 'on'
        prompt = request.form.get('prompt', '')
        dt.enabled = enabled
        dt.prompt = prompt
        db.session.commit()
        flash('Settings saved', 'success')
    
    return render_template('home.html', enabled=dt.enabled, prompt=dt.prompt)

@app.route('/keys', methods=['GET', 'POST'])
def keys():
    if not is_logedin(): return redirect('/login')
    if request.method == 'POST':
        del_id = request.form.get('del', type=int)
        if del_id:
            if kdldb := API_KEYS.query.get(del_id):
                db.session.delete(kdldb)
                db.session.commit()
                flash('That API Key deleted successfully', 'success')
                return redirect('/keys')
        kid = request.form.get('id')
        provider = request.form.get('provider')
        key = request.form.get('key')
        try: kid = int(kid)
        except: pass
        if kid == 'new':
            db.session.add(API_KEYS(provider=provider, key=key))
            db.session.commit()
            flash('API Key added successfully', 'success')
        else:
            if kitdb := API_KEYS.query.get(kid):
                kitdb.provider = provider
                kitdb.key = key
                db.session.commit()
                flash('API Key saved successfully', 'success')


    kdb = list(map(lambda x: dict(id=x.id, provider=x.provider, key=x.key, updated=time_ago_short(x.updated)), API_KEYS.query.order_by(API_KEYS.updated.desc()).all()))
    kdb = [dict(id='new', provider=None, key=None, updated=None), *kdb]
    return render_template('keys.html', key_dbs=kdb, PROVIDERS=PROVIDERS)

@app.route('/keys/check', methods=['GET', 'POST'])
def keys_check():
    def tfn(x):
        asyncio.run(checkAPI(x, API_CHECK_DATA))

    if request.method == 'POST':
        ak = API_KEYS.query.all()
        all_keys = list(map(lambda x: (x.provider, x.key), ak))
        Thread(target=tfn, args=(all_keys,), daemon=True).start()
        flash('Checking process is starting', 'success')
        return redirect('/keys/check')
    
    modACD = API_CHECK_DATA.copy()
    if lc := modACD.get('last_checked'): modACD['last_checked'] = time_ago_short(lc) + ' ago'
        
    return render_template('keys_check.html', fn=modACD)

@app.route('/ignore', methods=['GET', 'POST'])
def ignore():
    if not is_logedin(): return redirect('/login')
    if request.method == 'POST':
        identifier = request.form.get('identifier', '')
        if idt := identifier.strip():
            try: int(idt)
            except:
                if not idt.startswith('@'):
                    idt = '@' + idt
            db.session.add(Ignored_Accounts(identifier=idt))
            db.session.commit()
            flash(f'"{idt}" added to ignore list', 'success')

        ig_id = request.form.get('id', type=int)
        if ig_id:
            if igit := Ignored_Accounts.query.get(ig_id):
                db.session.delete(igit)
                db.session.commit()
                flash(f'"{igit.identifier}" deleted', 'success')

    igl = Ignored_Accounts.query.all()
    return render_template('ignore.html', ignore_list=igl)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logedin(): return redirect('/')
    if request.method == 'POST':
        pwd = request.form.get('pass')
        if pwd == app.config['PASSWORD']:
            r = redirect('/')
            r.set_cookie('auth', AUTH_HASH, 7 * 24 * 60 * 60)
            return r
        else:
            flash('Invalid Password', 'error')
    return render_template('login.html')


import os, secrets, logging
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from flask import Flask, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash
from .db import register_db, get_db
from .admin import bp as admin_bp
from .license_api import bp as license_bp

def create_app(test_config=None):
    app=Flask(__name__,instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True,exist_ok=True)
    app.config.from_mapping(
      SECRET_KEY=os.environ.get('AIMLD_SESSION_SECRET',''),
      LICENSE_PEPPER=os.environ.get('AIMLD_LICENSE_PEPPER',''),
      DATABASE_PATH=os.environ.get('AIMLD_DATABASE_PATH',str(Path(app.instance_path)/'aimld.sqlite3')),
      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE','true').lower()=='true',
      MAX_CONTENT_LENGTH=1024*1024, JSON_SORT_KEYS=False)
    if test_config: app.config.update(test_config)
    if not app.config['SECRET_KEY'] or len(app.config['SECRET_KEY'])<32: raise RuntimeError('Set AIMLD_SESSION_SECRET to a random secret of at least 32 characters')
    if not app.config['LICENSE_PEPPER'] or len(app.config['LICENSE_PEPPER'])<32: raise RuntimeError('Set AIMLD_LICENSE_PEPPER to a random secret of at least 32 characters')
    logging.basicConfig(level=os.environ.get('LOG_LEVEL','INFO'))
    Limiter(get_remote_address, app=app, default_limits=['300 per hour'], storage_uri=os.environ.get('RATELIMIT_STORAGE_URI', 'memory://'))
    @app.template_filter('vn_time')
    def vn_time(value):
        if not value: return '—'
        try:
            dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
            if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(ZoneInfo('Asia/Ho_Chi_Minh')).strftime('%d/%m/%Y %H:%M:%S')
        except (ValueError, TypeError):
            return str(value)
    app.jinja_env.globals['vn_timezone_label'] = 'Giờ Việt Nam (UTC+7)'
    register_db(app)
    app.register_blueprint(admin_bp); app.register_blueprint(license_bp)
    @app.get('/health')
    def health():
        try: get_db().execute('SELECT 1').fetchone(); return jsonify(ok=True,service='aimld-license-api')
        except Exception: app.logger.exception('Health check failed'); return jsonify(ok=False,code='DB_UNAVAILABLE'),503
    @app.errorhandler(404)
    def not_found(_): return jsonify(ok=False,code='NOT_FOUND',message='Resource not found'),404
    @app.errorhandler(429)
    def rate_limited(_): return jsonify(ok=False,code='RATE_LIMITED',message='Too many requests'),429
    return app

def create_first_admin():
    """One-time CLI helper. Requires AIMLD_ADMIN_USERNAME/PASSWORD and refuses overwrite."""
    from flask.cli import with_appcontext
    import click
    @click.command('create-admin')
    @click.option('--username', envvar='AIMLD_ADMIN_USERNAME', prompt=True)
    @click.option('--password', envvar='AIMLD_ADMIN_PASSWORD', prompt=True, hide_input=True, confirmation_prompt=True)
    @with_appcontext
    def command(username,password):
        if len(password)<14: raise click.ClickException('Password must be at least 14 characters.')
        db=get_db()
        try: db.execute('INSERT INTO admins(username,password_hash) VALUES(?,?)',(username.strip(),generate_password_hash(password)))
        except Exception as e: raise click.ClickException('Could not create admin; username may already exist.') from e
        click.echo('Admin created.')
    return command

app=create_app()
app.cli.add_command(create_first_admin())

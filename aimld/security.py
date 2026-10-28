import hashlib, hmac, secrets, time
from functools import wraps
from flask import current_app, session, redirect, url_for, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash

def hash_license(raw: str) -> str:
    return hmac.new(current_app.config['LICENSE_PEPPER'].encode(), raw.strip().upper().encode(), hashlib.sha256).hexdigest()

def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()

def new_license() -> str:
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    groups = [''.join(secrets.choice(alphabet) for _ in range(5)) for _ in range(4)]
    return 'AIMLD-' + '-'.join(groups)

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get('admin_id'):
            if request.path.startswith('/api/admin/'):
                return jsonify(ok=False, code='AUTH_REQUIRED', message='Admin login required'), 401
            return redirect(url_for('admin.login', next=request.path))
        return fn(*args, **kwargs)
    return wrapped

def csrf_protect(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if request.method in {'POST','PUT','PATCH','DELETE'}:
            sent = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
            expected = session.get('csrf_token','')
            if not sent or not expected or not hmac.compare_digest(sent, expected):
                if request.path.startswith('/api/admin/') or request.is_json:
                    return jsonify(ok=False, code='CSRF_INVALID', message='CSRF token invalid'), 400
                return 'CSRF validation failed', 400
        return fn(*args, **kwargs)
    return wrapped

def csrf_token():
    token = session.get('csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        session['csrf_token'] = token
    return token

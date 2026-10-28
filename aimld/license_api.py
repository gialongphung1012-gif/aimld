import json, secrets, sqlite3
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app
from .db import get_db
from .security import hash_license, hash_token
bp = Blueprint('license_api', __name__, url_prefix='/api/license')

def now_iso(): return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
def parse_time(s):
    if not s: return None
    try: return datetime.fromisoformat(s.replace('Z','+00:00'))
    except ValueError: return None

def fail(code, message, status): return jsonify(ok=False, code=code, message=message), status

def lookup_key(db, raw):
    if not isinstance(raw,str) or not 8 <= len(raw.strip()) <= 100: return None
    return db.execute('SELECT * FROM licenses WHERE key_hash=?', (hash_license(raw),)).fetchone()

def current_activation(db, lic, device_id):
    return db.execute('SELECT * FROM activations WHERE license_id=? AND device_id=? AND deactivated_at IS NULL ORDER BY id DESC LIMIT 1', (lic['id'],device_id)).fetchone()

def record_event(action, target_type, target_id='', detail=None):
    # Never store raw license keys or activation tokens in audit logs.
    db = get_db()
    db.execute(
        'INSERT INTO audit_logs(admin_id,action,target_type,target_id,detail_json,ip_address) VALUES(NULL,?,?,?,?,?)',
        (action, target_type, str(target_id), json.dumps(detail or {}), request.remote_addr or '')
    )

def status_for(lic):
    if lic['status']=='revoked': return ('KEY_REVOKED','Key has been revoked')
    if lic['status']=='blocked': return ('KEY_BLOCKED','Key is blocked')
    exp=parse_time(lic['expires_at'])
    if not exp or exp <= datetime.now(timezone.utc): return ('KEY_EXPIRED','Key has expired')
    return ('KEY_VALID','License is valid')

@bp.post('/activate')
def activate():
    body=request.get_json(silent=True) or {}
    raw=body.get('key'); device_id=body.get('device_id'); label=str(body.get('device_label',''))[:120]
    if not isinstance(device_id,str) or not 8 <= len(device_id) <= 128: return fail('INVALID_DEVICE','device_id must be 8-128 characters',400)
    if not isinstance(raw,str): return fail('KEY_NOT_FOUND','License key not found',404)
    db=get_db(); db.execute('BEGIN IMMEDIATE')
    try:
        lic=lookup_key(db,raw)
        if not lic:
            db.rollback()
            record_event('license_activation_failed','license','',{'reason':'key_not_found'})
            return fail('KEY_NOT_FOUND','License key not found',404)
        code,msg=status_for(lic)
        if code!='KEY_VALID':
            db.rollback()
            record_event('license_activation_failed','license',lic['id'],{'reason':code})
            return fail(code,msg,403)
        activation=current_activation(db,lic,device_id)
        if activation:
            token=secrets.token_urlsafe(32)
            db.execute('UPDATE activations SET token_hash=?, last_seen_at=?, device_label=? WHERE id=?',(hash_token(token),now_iso(),label,activation['id']))
        else:
            count=db.execute('SELECT COUNT(*) n FROM activations WHERE license_id=? AND deactivated_at IS NULL',(lic['id'],)).fetchone()['n']
            if count >= lic['max_devices']:
                db.rollback(); return fail('DEVICE_LIMIT','License has reached its device limit',409)
            token=secrets.token_urlsafe(32)
            db.execute('INSERT INTO activations(license_id,device_id,device_label,token_hash,activated_at,last_seen_at) VALUES(?,?,?,?,?,?)',(lic['id'],device_id,label,hash_token(token),now_iso(),now_iso()))
            db.execute('UPDATE licenses SET activated_at=COALESCE(activated_at,?), updated_at=? WHERE id=?',(now_iso(),now_iso(),lic['id']))
        db.execute('INSERT INTO audit_logs(admin_id,action,target_type,target_id,detail_json,ip_address) VALUES(NULL,?,?,?,?,?)',('license_activated','license',str(lic['id']),json.dumps({'device_id':device_id}),request.remote_addr or ''))
        db.commit()
        return jsonify(ok=True,code='KEY_VALID',message='License activated',activation_token=token,expires_at=lic['expires_at'],max_devices=lic['max_devices'])
    except Exception:
        db.rollback(); current_app.logger.exception('Activation failed'); return fail('SERVER_ERROR','Internal server error',500)

@bp.post('/validate')
def validate():
    body=request.get_json(silent=True) or {}
    device_id=body.get('device_id')
    token=body.get('activation_token')
    if not isinstance(device_id,str) or not 8 <= len(device_id) <= 128:
        return fail('INVALID_DEVICE','Invalid device_id',400)
    if not isinstance(token,str) or not 20 <= len(token) <= 200:
        return fail('INVALID_ACTIVATION','Activation token is required',401)
    db=get_db()
    rows=db.execute(
        "SELECT a.*, l.status, l.expires_at, l.max_devices FROM activations a JOIN licenses l ON l.id=a.license_id "
        "WHERE a.device_id=? AND a.deactivated_at IS NULL ORDER BY a.id DESC",
        (device_id,)
    ).fetchall()
    token_hash=hash_token(token)
    matched=next((r for r in rows if secrets.compare_digest(r['token_hash'],token_hash)),None)
    if not matched:
        record_event('license_validate_failed','device',device_id,{'reason':'activation_not_found'})
        return fail('ACTIVATION_NOT_FOUND','Activation not found',401)
    code,msg=status_for(matched)
    if code!='KEY_VALID':
        record_event('license_validate_failed','license',matched['license_id'],{'reason':code,'device_id':device_id})
        return fail(code,msg,403)
    db.execute('UPDATE activations SET last_seen_at=? WHERE id=?',(now_iso(),matched['id']))
    record_event('license_validate_success','license',matched['license_id'],{'device_id':device_id})
    return jsonify(ok=True,code='KEY_VALID',message='License is valid',
                   expires_at=matched['expires_at'],device_limit=matched['max_devices'])

@bp.post('/deactivate')
def deactivate():
    body=request.get_json(silent=True) or {}
    device_id=body.get('device_id'); token=body.get('activation_token')
    if not isinstance(device_id,str) or not isinstance(token,str):
        return fail('INVALID_REQUEST','device_id and activation_token are required',400)
    db=get_db()
    rows=db.execute(
        'SELECT a.*, l.id AS license_id FROM activations a JOIN licenses l ON l.id=a.license_id '
        'WHERE a.device_id=? AND a.deactivated_at IS NULL ORDER BY a.id DESC',
        (device_id,)
    ).fetchall()
    token_hash=hash_token(token)
    act=next((r for r in rows if secrets.compare_digest(r['token_hash'],token_hash)),None)
    if not act:
        return fail('ACTIVATION_NOT_FOUND','Activation not found',404)
    db.execute('UPDATE activations SET deactivated_at=? WHERE id=?',(now_iso(),act['id']))
    db.execute('INSERT INTO audit_logs(admin_id,action,target_type,target_id,detail_json,ip_address) VALUES(NULL,?,?,?,?,?)',
               ('device_deactivated','license',str(act['license_id']),json.dumps({'device_id':device_id}),request.remote_addr or ''))
    return jsonify(ok=True,code='DEACTIVATED',message='Device deactivated')

@bp.get('/status')
def status():
    device_id=request.args.get('device_id','')
    auth=request.headers.get('Authorization','')
    token=auth[7:].strip() if auth.startswith('Bearer ') else ''
    if not device_id or not token:
        return fail('AUTH_REQUIRED','Bearer activation token and device_id are required',401)
    db=get_db()
    rows=db.execute(
        'SELECT a.*, l.status, l.expires_at, l.max_devices FROM activations a JOIN licenses l ON l.id=a.license_id '
        'WHERE a.device_id=? AND a.deactivated_at IS NULL ORDER BY a.id DESC',
        (device_id,)
    ).fetchall()
    token_hash=hash_token(token)
    matched=next((r for r in rows if secrets.compare_digest(r['token_hash'],token_hash)),None)
    if not matched:
        return fail('ACTIVATION_NOT_FOUND','Activation not found',401)
    code,msg=status_for(matched)
    if code!='KEY_VALID':
        return fail(code,msg,403)
    return jsonify(ok=True,code='KEY_VALID',message=msg,expires_at=matched['expires_at'],max_devices=matched['max_devices'])

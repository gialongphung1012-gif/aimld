import csv, io, json, secrets
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, make_response, current_app
from werkzeug.security import check_password_hash
from .db import get_db
from .security import admin_required, csrf_protect, csrf_token, new_license, hash_license
bp=Blueprint('admin',__name__)

def audit(action, target_type, target_id='', detail=None):
    db=get_db(); db.execute('INSERT INTO audit_logs(admin_id,action,target_type,target_id,detail_json,ip_address) VALUES(?,?,?,?,?,?)',(session.get('admin_id'),action,target_type,str(target_id),json.dumps(detail or {}),request.remote_addr or ''))

def expiry_from(body):
    preset=body.get('duration','30d')
    now=datetime.now(timezone.utc)
    if preset in {'1d','7d','30d','90d'}: return (now+timedelta(days=int(preset[:-1]))).isoformat(timespec='seconds').replace('+00:00','Z')
    if preset=='custom':
        raw=body.get('expires_at','')
        try:
            dt=datetime.fromisoformat(raw.replace('Z','+00:00'))
            if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
            if dt<=now: raise ValueError()
            return dt.astimezone(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
        except ValueError: raise ValueError('Custom expiry must be a future ISO date/time')
    raise ValueError('Invalid duration')

@bp.app_context_processor
def inject_csrf(): return {'csrf_token':csrf_token}

@bp.get('/')
def home(): return redirect(url_for('admin.dashboard'))

@bp.route('/admin/login',methods=['GET','POST'])
@csrf_protect
def login():
    if request.method=='POST':
        db=get_db(); row=db.execute('SELECT * FROM admins WHERE username=?',(request.form.get('username','').strip(),)).fetchone()
        if row and check_password_hash(row['password_hash'],request.form.get('password','')):
            session.clear(); session['admin_id']=row['id']; session['username']=row['username']; session['csrf_token']=secrets.token_urlsafe(32)
            db.execute('UPDATE admins SET last_login_at=? WHERE id=?',(datetime.now(timezone.utc).isoformat(),row['id']))
            return redirect(url_for('admin.dashboard'))
        flash('Sai tài khoản hoặc mật khẩu.','error')
    return render_template('login.html')

@bp.post('/admin/logout')
@csrf_protect
def logout(): session.clear(); return redirect(url_for('admin.login'))

def dashboard_page(new_keys=None):
    db=get_db(); now=datetime.now(timezone.utc).isoformat()
    stats={
      'total':db.execute('SELECT COUNT(*) n FROM licenses').fetchone()['n'],
      'active':db.execute("SELECT COUNT(*) n FROM licenses WHERE status='active' AND expires_at > ?",(now,)).fetchone()['n'],
      'expired':db.execute('SELECT COUNT(*) n FROM licenses WHERE expires_at <= ?',(now,)).fetchone()['n'],
      'revoked':db.execute("SELECT COUNT(*) n FROM licenses WHERE status='revoked'").fetchone()['n'],
      'activations':db.execute('SELECT COUNT(*) n FROM activations WHERE deactivated_at IS NULL').fetchone()['n']}
    q=request.args.get('q','').strip(); status=request.args.get('status','')
    sql="SELECT l.*, (SELECT COUNT(*) FROM activations a WHERE a.license_id=l.id AND a.deactivated_at IS NULL) device_count, (SELECT COUNT(*) FROM activations a WHERE a.license_id=l.id) activation_history_count FROM licenses l WHERE 1=1"; args=[]
    if q: sql+=' AND (l.key_prefix LIKE ? OR l.label LIKE ?)'; args += [f'%{q}%',f'%{q}%']
    if status in {'active','blocked','revoked'}: sql+=' AND l.status=?'; args.append(status)
    elif status == 'unused': sql+=" AND l.activated_at IS NULL AND l.status='active' AND l.expires_at > ?"; args.append(now)
    elif status == 'in_use': sql+=" AND l.activated_at IS NOT NULL AND l.status='active' AND l.expires_at > ? AND EXISTS (SELECT 1 FROM activations a WHERE a.license_id=l.id AND a.deactivated_at IS NULL)"; args.append(now)
    elif status == 'expired': sql+=' AND l.expires_at <= ?'; args.append(now)
    sql+=' ORDER BY l.id DESC'; rows=db.execute(sql,args).fetchall()
    return render_template('dashboard.html',stats=stats,licenses=rows,q=q,status=status,new_keys=new_keys or [],now_iso=now)

@bp.get('/admin')
@admin_required
def dashboard():
    return dashboard_page()


@bp.post('/admin/keys/clear-new')
@admin_required
@csrf_protect
def clear_new_keys():
    return redirect(url_for('admin.dashboard') + '#new-keys')

@bp.post('/admin/keys/create')
@admin_required
@csrf_protect
def create_keys():
    body=request.form
    try:
        count=int(body.get('count','1'))
        max_devices=int(body.get('max_devices','1'))
        if not 1<=count<=100 or not 1<=max_devices<=25: raise ValueError('Số lượng key 1-100, thiết bị 1-25.')
        expires=expiry_from(body); label=body.get('label','')[:120]
    except ValueError as e: flash(str(e),'error'); return redirect(url_for('admin.dashboard'))
    db=get_db(); created=[]
    db.execute('BEGIN IMMEDIATE')
    try:
        for _ in range(count):
            raw=new_license(); db.execute('INSERT INTO licenses(key_hash,key_prefix,label,expires_at,max_devices) VALUES(?,?,?,?,?)',(hash_license(raw),raw[:11],label,expires,max_devices)); created.append(raw)
        audit('keys_created','license',','.join(created[:3]),{'count':count,'max_devices':max_devices})
        db.commit()
    except Exception:
        db.rollback(); current_app.logger.exception('Create keys failed'); flash('Không tạo được key.','error'); return redirect(url_for('admin.dashboard'))
    flash(f'Đã tạo {len(created)} key. Hãy sao chép danh sách ngay; server không lưu key gốc.','success')
    return dashboard_page(created)

@bp.post('/admin/keys/<int:key_id>/action')
@admin_required
@csrf_protect
def key_action(key_id):
    action=request.form.get('action'); db=get_db(); row=db.execute('SELECT * FROM licenses WHERE id=?',(key_id,)).fetchone()
    if not row: flash('Không tìm thấy key.','error'); return redirect(url_for('admin.dashboard'))
    if row['status']=='revoked' and action in {'block','unblock','revoke'}:
        flash('Key đã thu hồi vĩnh viễn; không thể đổi trạng thái.','error'); return redirect(url_for('admin.dashboard'))
    if action in {'block','unblock','revoke','reset_devices','extend'}:
        if action=='block': db.execute("UPDATE licenses SET status='blocked',updated_at=? WHERE id=?",(datetime.now(timezone.utc).isoformat(),key_id))
        elif action=='unblock': db.execute("UPDATE licenses SET status='active',updated_at=? WHERE id=? AND status!='revoked'",(datetime.now(timezone.utc).isoformat(),key_id))
        elif action=='revoke': db.execute("UPDATE licenses SET status='revoked',updated_at=? WHERE id=?",(datetime.now(timezone.utc).isoformat(),key_id))
        elif action=='reset_devices': db.execute('UPDATE activations SET deactivated_at=? WHERE license_id=? AND deactivated_at IS NULL',(datetime.now(timezone.utc).isoformat(),key_id))
        elif action=='extend':
            try:
                days=int(request.form.get('days','30'))
                if not 1<=days<=3650: raise ValueError()
                base=datetime.fromisoformat(row['expires_at'].replace('Z','+00:00'))
                if base<datetime.now(timezone.utc): base=datetime.now(timezone.utc)
                expiry=(base+timedelta(days=days)).isoformat(timespec='seconds').replace('+00:00','Z')
                db.execute('UPDATE licenses SET expires_at=?,updated_at=? WHERE id=?',(expiry,datetime.now(timezone.utc).isoformat(),key_id))
            except ValueError: flash('Số ngày gia hạn không hợp lệ.','error'); return redirect(url_for('admin.dashboard'))
        audit(action,'license',key_id,{'action':action}); flash('Đã cập nhật key.','success')
    else: flash('Thao tác không hợp lệ.','error')
    return redirect(url_for('admin.dashboard'))

@bp.get('/admin/keys/<int:key_id>/devices')
@admin_required
def devices(key_id):
    db=get_db(); lic=db.execute('SELECT id,key_prefix,label,max_devices,status,expires_at FROM licenses WHERE id=?',(key_id,)).fetchone()
    if not lic: return 'Not found',404
    rows=db.execute('SELECT device_id,device_label,activated_at,last_seen_at,deactivated_at FROM activations WHERE license_id=? ORDER BY id DESC',(key_id,)).fetchall()
    return render_template('devices.html',license=lic,devices=rows)

@bp.get('/admin/export.csv')
@admin_required
def export_csv():
    db=get_db(); rows=db.execute('SELECT id,key_prefix,label,status,created_at,expires_at,max_devices,activated_at FROM licenses ORDER BY id DESC').fetchall()
    out=io.StringIO(); w=csv.writer(out); w.writerow(['id','key_prefix','label','status','created_at_vn','expires_at_vn','max_devices','activated_at_vn'])
    def vn_csv(value):
        if not value: return ''
        try:
            dt=datetime.fromisoformat(str(value).replace('Z','+00:00'))
            if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(__import__('zoneinfo').ZoneInfo('Asia/Ho_Chi_Minh')).strftime('%d/%m/%Y %H:%M:%S')
        except (ValueError,TypeError): return str(value)
    for r in rows:
        vals=list(r); vals[4]=vn_csv(vals[4]); vals[5]=vn_csv(vals[5]); vals[7]=vn_csv(vals[7]); w.writerow(vals)
    resp=make_response('\ufeff'+out.getvalue()); resp.headers['Content-Type']='text/csv; charset=utf-8'; resp.headers['Content-Disposition']='attachment; filename=aimld-licenses.csv'; return resp

@bp.get('/api/admin/overview')
@admin_required
def overview():
    db=get_db(); return jsonify(ok=True,stats={'licenses':db.execute('SELECT COUNT(*) n FROM licenses').fetchone()['n'],'activations':db.execute('SELECT COUNT(*) n FROM activations WHERE deactivated_at IS NULL').fetchone()['n']})


@bp.get('/admin/history')
@admin_required
def history():
    db = get_db()
    action = request.args.get('action', '').strip()
    sql = ('SELECT a.*, u.username FROM audit_logs a LEFT JOIN admins u ON u.id=a.admin_id WHERE 1=1')
    args = []
    if action:
        sql += ' AND a.action LIKE ?'; args.append('%' + action[:80] + '%')
    sql += ' ORDER BY a.id DESC LIMIT 300'
    rows = db.execute(sql, args).fetchall()
    return render_template('history.html', events=rows, action=action)

import os, tempfile, unittest
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash
os.environ.setdefault('AIMLD_SESSION_SECRET','test-session-secret-'+'x'*40)
os.environ.setdefault('AIMLD_LICENSE_PEPPER','test-license-pepper-'+'y'*40)
from aimld.app import create_app
from aimld.db import get_db
from aimld.security import hash_license

class LicenseAPITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.NamedTemporaryFile(suffix='.sqlite3',delete=False); self.tmp.close()
        self.app=create_app({'TESTING':True,'SECRET_KEY':'s'*48,'LICENSE_PEPPER':'p'*48,'DATABASE_PATH':self.tmp.name,'SESSION_COOKIE_SECURE':False,'RATELIMIT_ENABLED':False})
        self.client=self.app.test_client()
        with self.app.app_context():
            db=get_db(); expiry=(datetime.now(timezone.utc)+timedelta(days=7)).isoformat().replace('+00:00','Z')
            db.execute('INSERT INTO licenses(key_hash,key_prefix,label,expires_at,max_devices) VALUES(?,?,?,?,?)',(hash_license('AIMLD-VALID-KEY-1234'),'AIMLD-VALI','test',expiry,1))
            db.execute('INSERT INTO licenses(key_hash,key_prefix,label,expires_at,max_devices) VALUES(?,?,?,?,?)',(hash_license('AIMLD-EXPIRED-KEY'),'AIMLD-EXPI','expired',(datetime.now(timezone.utc)-timedelta(days=1)).isoformat().replace('+00:00','Z'),1))
            db.execute('INSERT INTO licenses(key_hash,key_prefix,label,status,expires_at,max_devices) VALUES(?,?,?,?,?,?)',(hash_license('AIMLD-REVOKED-KEY'),'AIMLD-REVO','revoked','revoked',expiry,1))
    def tearDown(self):
        try: os.unlink(self.tmp.name)
        except FileNotFoundError: pass
    def test_activate_and_validate(self):
        r=self.client.post('/api/license/activate',json={'key':'AIMLD-VALID-KEY-1234','device_id':'device-123456','device_label':'iPhone'})
        self.assertEqual(r.status_code,200); self.assertEqual(r.json['code'],'KEY_VALID')
        token=r.json['activation_token']
        r=self.client.post('/api/license/validate',json={'activation_token':token,'device_id':'device-123456'})
        self.assertEqual(r.status_code,200)
    def test_validate_requires_activation_token(self):
        r=self.client.post('/api/license/validate',json={'device_id':'device-123456'})
        self.assertEqual(r.status_code,401)
        self.assertEqual(r.json['code'],'INVALID_ACTIVATION')

    def test_device_limit(self):
        self.client.post('/api/license/activate',json={'key':'AIMLD-VALID-KEY-1234','device_id':'device-123456'})
        r=self.client.post('/api/license/activate',json={'key':'AIMLD-VALID-KEY-1234','device_id':'device-654321'})
        self.assertEqual(r.status_code,409); self.assertEqual(r.json['code'],'DEVICE_LIMIT')
    def test_expired_and_revoked(self):
        r=self.client.post('/api/license/activate',json={'key':'AIMLD-EXPIRED-KEY','device_id':'device-123456'})
        self.assertEqual(r.json['code'],'KEY_EXPIRED')
        r=self.client.post('/api/license/activate',json={'key':'AIMLD-REVOKED-KEY','device_id':'device-123456'})
        self.assertEqual(r.json['code'],'KEY_REVOKED')
    def test_unknown_key(self):
        r=self.client.post('/api/license/activate',json={'key':'not-a-key','device_id':'device-123456'})
        self.assertEqual(r.status_code,404); self.assertEqual(r.json['code'],'KEY_NOT_FOUND')

if __name__=='__main__': unittest.main()

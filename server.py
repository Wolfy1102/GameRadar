"""GameRadar backend: SuperDuperBundle search + persistent accounts.
Set DATABASE_PATH to a persistent Render disk path (for example /var/data/gameradar.sqlite3).
Set OWNER_EMAIL to the exact email used for the owner account.
Set SUPERDUPERBUNDLE_API_KEY to the partner key (optional but recommended).
"""
import hashlib, hmac, json, os, secrets, sqlite3, threading, time, urllib.error, urllib.parse, urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

API_BASE = "https://superduperbundle.com/api/v1/lookup/"
API_KEY = os.environ.get("SUPERDUPERBUNDLE_API_KEY", "").strip()
OWNER_EMAIL = os.environ.get("OWNER_EMAIL", "").strip().lower()
DB_PATH = os.environ.get("DATABASE_PATH", "./data/gameradar.sqlite3")
CLIENT_NAME = "steam-deal-radar-2-0"
CACHE_TTL = 900
CACHE, CACHE_LOCK = {}, threading.Lock()
PBKDF2_ROUNDS = 310_000
SESSION_DAYS = 30

def db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL UNIQUE,
          username TEXT NOT NULL, password_hash TEXT NOT NULL,
          role TEXT NOT NULL DEFAULT 'user', tier TEXT NOT NULL DEFAULT 'free',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS sessions (
          token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          expires_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS favorites (
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          game_name TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY(user_id, game_name)
        );
        CREATE TABLE IF NOT EXISTS search_history (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          term TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """)
        if OWNER_EMAIL:
            c.execute("UPDATE users SET role='owner', tier='ultimate' WHERE lower(email)=?", (OWNER_EMAIL,))

def password_hash(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}"

def verify_password(password, encoded):
    try:
        _, rounds, salt_hex, digest_hex = encoded.split('$')
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt_hex), int(rounds)).hex()
        return hmac.compare_digest(actual, digest_hex)
    except Exception:
        return False

def json_bytes(payload): return json.dumps(payload, ensure_ascii=False).encode('utf-8')
def cache_get(key):
    with CACHE_LOCK:
        item = CACHE.get(key)
        if item and item[0] > time.time(): return item[1]
        CACHE.pop(key, None)
    return None
def cache_set(key, value):
    with CACHE_LOCK:
        CACHE[key] = (time.time()+CACHE_TTL, value)
        if len(CACHE) > 500: CACHE.pop(next(iter(CACHE)))

def fetch_sdb(term, limit=5):
    params = urllib.parse.urlencode({'q': term, 'limit': str(max(1,min(limit,5))), 'client': CLIENT_NAME})
    headers = {'User-Agent': 'GameRadar/2.0 (+https://steam-deal-radar-2-0.onrender.com)', 'Accept':'application/json'}
    if API_KEY: headers['X-API-Key'] = API_KEY
    req = urllib.request.Request(API_BASE+'?'+params, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode()), r.headers.get('X-RateLimit-Remaining')
    except urllib.error.HTTPError as e:
        body=e.read().decode('utf-8','replace')
        if e.code == 429: raise RuntimeError('SuperDuperBundle API-Limit erreicht. Bitte später erneut versuchen.')
        if e.code in (401,403): raise RuntimeError('API-Schlüssel ungültig oder Zugriff nicht erlaubt. Prüfe SUPERDUPERBUNDLE_API_KEY in Render.')
        raise RuntimeError(f'SuperDuperBundle HTTP {e.code}: {body[:300]}')
    except (urllib.error.URLError, TimeoutError): raise RuntimeError('SuperDuperBundle ist momentan nicht erreichbar.')

def normalise(payload):
    out=[]
    for g in payload.get('results',[]) if isinstance(payload,dict) else []:
        if not isinstance(g,dict): continue
        low=g.get('lowest') or {}
        out.append({'name':g.get('name') or 'Unbekanntes Spiel','image':g.get('image') or '',
          'price':low.get('price'),'base':g.get('list_price'),'currency':g.get('currency') or 'USD',
          'discount':low.get('discount_pct'),'provider':low.get('store') or '',
          'provider_name':low.get('store_name') or low.get('store') or 'Store',
          'url':g.get('url') or '', 'region':low.get('region') or '', 'drm':low.get('drm') or '',
          'store_type':low.get('store_type') or '', 'checked_at':low.get('checked_at') or '',
          'store_count':g.get('store_count',0),'offer_count':g.get('offer_count',0),
          'offers':g.get('offers') or [], 'state':g.get('state') or ''})
    return out

class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args): print('%s - %s' % (self.address_string(), fmt%args))
    def send_json(self,status,payload,headers=None):
        body=json_bytes(payload); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(body))); self.send_header('Cache-Control','no-store')
        for k,v in (headers or {}).items(): self.send_header(k,str(v))
        self.end_headers(); self.wfile.write(body)
    def body(self):
        try: return json.loads(self.rfile.read(int(self.headers.get('Content-Length','0')) or 0) or b'{}')
        except Exception: return {}
    def current_user(self):
        cookie=self.headers.get('Cookie','')
        token=''
        for part in cookie.split(';'):
            k,_,v=part.strip().partition('=')
            if k=='gameradar_session': token=v
        if not token: return None
        th=hashlib.sha256(token.encode()).hexdigest()
        with db() as c:
            row=c.execute('SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?',(th,int(time.time()))).fetchone()
            if row and OWNER_EMAIL and row['email'].lower()==OWNER_EMAIL and (row['role']!='owner' or row['tier']!='ultimate'):
                c.execute("UPDATE users SET role='owner',tier='ultimate' WHERE id=?",(row['id'],))
                row=c.execute('SELECT * FROM users WHERE id=?',(row['id'],)).fetchone()
        return dict(row) if row else None
    def user_json(self,u): return {k:u[k] for k in ('id','email','username','role','tier','created_at')}
    def do_POST(self):
        path=urllib.parse.urlparse(self.path).path; data=self.body()
        if path=='/api/register':
            email=str(data.get('email','')).strip().lower(); username=str(data.get('username','')).strip()[:32]; pw=str(data.get('password',''))
            if len(email)>254 or '@' not in email or not username or len(pw)<10 or len(pw)>200:
                return self.send_json(400,{'message':'Bitte gültige E-Mail, Benutzernamen und ein Passwort mit mindestens 10 Zeichen angeben.'})
            role='owner' if OWNER_EMAIL and email==OWNER_EMAIL else 'user'; tier='ultimate' if role=='owner' else 'free'
            try:
                with db() as c:
                    cur=c.execute('INSERT INTO users(email,username,password_hash,role,tier) VALUES(?,?,?,?,?)',(email,username,password_hash(pw),role,tier)); uid=cur.lastrowid
                return self.create_session(uid)
            except sqlite3.IntegrityError: return self.send_json(409,{'message':'Für diese E-Mail-Adresse existiert bereits ein Konto. Bitte einloggen.'})
        if path=='/api/login':
            email=str(data.get('email','')).strip().lower(); pw=str(data.get('password',''))
            with db() as c: u=c.execute('SELECT * FROM users WHERE lower(email)=?',(email,)).fetchone()
            if not u or not verify_password(pw,u['password_hash']): return self.send_json(401,{'message':'E-Mail oder Passwort ist falsch.'})
            return self.create_session(u['id'])
        if path=='/api/logout':
            u=self.current_user(); cookie=self.headers.get('Cookie',''); token=''
            for part in cookie.split(';'):
                k,_,v=part.strip().partition('=')
                if k=='gameradar_session': token=v
            if token:
                with db() as c: c.execute('DELETE FROM sessions WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),))
            return self.send_json(200,{'ok':True}, {'Set-Cookie':'gameradar_session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0; Secure'})
        if path.startswith('/api/favorites'):
            u=self.current_user()
            if not u: return self.send_json(401,{'message':'Bitte zuerst einloggen.'})
            name=str(data.get('name','')).strip()[:160]
            if not name: return self.send_json(400,{'message':'Spielname fehlt.'})
            with db() as c:
                if data.get('remove'): c.execute('DELETE FROM favorites WHERE user_id=? AND game_name=?',(u['id'],name))
                else: c.execute('INSERT OR IGNORE INTO favorites(user_id,game_name) VALUES(?,?)',(u['id'],name))
            return self.send_json(200,{'ok':True})
        return self.send_json(404,{'message':'Nicht gefunden.'})
    def create_session(self,uid):
        token=secrets.token_urlsafe(32); th=hashlib.sha256(token.encode()).hexdigest(); expiry=int(time.time())+SESSION_DAYS*86400
        with db() as c: c.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',(th,uid,expiry)); u=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
        secure='; Secure' if self.headers.get('X-Forwarded-Proto','https')=='https' else ''
        return self.send_json(200,{'ok':True,'user':self.user_json(dict(u))},{'Set-Cookie':f'gameradar_session={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={SESSION_DAYS*86400}{secure}'})
    def do_GET(self):
        parsed=urllib.parse.urlparse(self.path); params=urllib.parse.parse_qs(parsed.query)
        if parsed.path=='/api/me':
            u=self.current_user(); return self.send_json(200,{'user':self.user_json(u) if u else None})
        if parsed.path=='/api/favorites':
            u=self.current_user()
            if not u: return self.send_json(401,{'message':'Bitte zuerst einloggen.'})
            with db() as c: rows=c.execute('SELECT game_name,created_at FROM favorites WHERE user_id=? ORDER BY created_at DESC',(u['id'],)).fetchall()
            return self.send_json(200,{'items':[dict(x) for x in rows]})
        if parsed.path=='/api/search':
            term=(params.get('term') or [''])[0].strip()
            if not term: return self.send_json(400,{'message':'Bitte gib einen Spieletitel ein.'})
            if len(term)>120: return self.send_json(400,{'message':'Suchbegriff zu lang.'})
            try: limit=max(1,min(int((params.get('limit') or ['5'])[0]),5))
            except ValueError: limit=5
            key=(term.casefold(),limit); data=cache_get(key)
            try:
                if data is None:
                    payload,remaining=fetch_sdb(term,limit); items=normalise(payload)
                    data={'items':items,'count':len(items),'attribution':payload.get('attribution') or {'text':'Prices by SuperDuperBundle','url':'https://superduperbundle.com/'},'cached_for_seconds':CACHE_TTL,'rate_limit_remaining':remaining}
                    cache_set(key,data)
                u=self.current_user()
                if u:
                    with db() as c: c.execute('INSERT INTO search_history(user_id,term) VALUES(?,?)',(u['id'],term[:120]))
                return self.send_json(200,data)
            except Exception as e: return self.send_json(502,{'message':str(e)})
        if parsed.path=='/api/health':
            return self.send_json(200,{'ok':True,'provider':'SuperDuperBundle','api_key_configured':bool(API_KEY),'database':'sqlite','database_path':DB_PATH,'persistent_disk_required':True})
        return super().do_GET()

init_db()
if __name__=='__main__':
    port=int(os.environ.get('PORT','8000')); server=ThreadingHTTPServer(('0.0.0.0',port),Handler)
    print(f'GameRadar listening on {port}; database={DB_PATH}; SDB key configured={bool(API_KEY)}')
    server.serve_forever()

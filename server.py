"""Steam Deal Radar 2.0 - small production-minded starter server.
Uses only Python's standard library. Configure secrets via environment variables.
"""
import hashlib, hmac, json, os, re, secrets, sqlite3, time, urllib.parse, urllib.request, urllib.error
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = os.environ.get('DATABASE_PATH', str(ROOT / 'data' / 'gameradar.sqlite3'))
API_BASE = 'https://gameprices.now/api/v1'
API_KEY = os.environ.get('GAMEPRICES_API_KEY', '').strip()
OWNER_EMAIL = os.environ.get('OWNER_EMAIL', '').strip().lower()
SESSION_DAYS = int(os.environ.get('SESSION_DAYS', '14'))
PBKDF2_ROUNDS = 310_000
TIERS = {'free': 0, 'radar': 1, 'pro': 2, 'ultimate': 3}
TIER_NAMES = {'free': 'Free', 'radar': 'Radar', 'pro': 'Pro', 'ultimate': 'Ultimate'}
RATE = {}


def db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=20)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    return con


def init_db():
    with db() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL UNIQUE,
          display_name TEXT NOT NULL, password_hash TEXT NOT NULL,
          password_salt TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user',
          tier TEXT NOT NULL DEFAULT 'free', created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
          token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          csrf TEXT NOT NULL, expires_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires_at);
        ''')
        if OWNER_EMAIL:
            con.execute("UPDATE users SET role='user', tier='free' WHERE role='owner' AND email!=?", (OWNER_EMAIL,))
            con.execute("UPDATE users SET role='owner', tier='ultimate' WHERE email=?", (OWNER_EMAIL,))


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    value = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), PBKDF2_ROUNDS).hex()
    return salt, value


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def user_payload(row):
    is_owner = row['role'] == 'owner'
    tier = 'ultimate' if is_owner else row['tier']
    return {'id': row['id'], 'email': row['email'], 'name': row['display_name'],
            'role': row['role'], 'tier': tier, 'tier_name': TIER_NAMES.get(tier, 'Free'),
            'features': {'prices': True, 'compare': is_owner or TIERS.get(tier, 0) >= 2,
                         'multitool': is_owner or TIERS.get(tier, 0) >= 2,
                         'assistant_preview': is_owner or TIERS.get(tier, 0) >= 3,
                         'all_stores': is_owner or TIERS.get(tier, 0) >= 2}}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        print('[%s] %s' % (self.log_date_time_string(), fmt % args))

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        if os.environ.get('RENDER') or os.environ.get('FORCE_HTTPS') == '1':
            self.send_header('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        super().end_headers()

    def send_json(self, status, payload, headers=None):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        if headers:
            for key, value in headers.items(): self.send_header(key, value)
        self.end_headers(); self.wfile.write(body)

    def read_json(self):
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length > 16_384: raise ValueError('Anfrage ist zu groß.')
            return json.loads(self.rfile.read(length) or b'{}')
        except (ValueError, json.JSONDecodeError):
            raise ValueError('Ungültige Anfrage.')

    def rate_limit(self, bucket, limit=12, window=300):
        now = time.time(); key = (bucket, self.client_address[0])
        recent = [stamp for stamp in RATE.get(key, []) if now - stamp < window]
        if len(recent) >= limit:
            RATE[key] = recent
            self.send_json(429, {'error': 'rate_limited', 'message': 'Zu viele Versuche. Bitte später erneut probieren.'})
            return False
        recent.append(now); RATE[key] = recent
        return True

    def get_session(self):
        cookie = SimpleCookie(self.headers.get('Cookie', ''))
        morsel = cookie.get('sdr_session')
        if not morsel: return None
        with db() as con:
            row = con.execute('''SELECT users.*, sessions.csrf, sessions.expires_at
                FROM sessions JOIN users ON users.id=sessions.user_id
                WHERE sessions.token_hash=? AND sessions.expires_at>?''',
                (token_hash(morsel.value), int(time.time()))).fetchone()
        return row

    def require_csrf(self, session):
        supplied = self.headers.get('X-CSRF-Token', '')
        if not session or not hmac.compare_digest(supplied, session['csrf']):
            self.send_json(403, {'error': 'csrf', 'message': 'Sicherheitsprüfung fehlgeschlagen. Seite neu laden.'})
            return False
        return True

    def create_session(self, user_id):
        token = secrets.token_urlsafe(40); csrf = secrets.token_urlsafe(24)
        expires = int(time.time()) + SESSION_DAYS * 86400
        with db() as con:
            con.execute('INSERT INTO sessions(token_hash,user_id,csrf,expires_at) VALUES(?,?,?,?)',
                        (token_hash(token), user_id, csrf, expires))
            con.execute('DELETE FROM sessions WHERE expires_at < ?', (int(time.time()),))
        secure = '; Secure' if (self.headers.get('X-Forwarded-Proto') == 'https' or os.environ.get('RENDER')) else ''
        return csrf, {'Set-Cookie': f'sdr_session={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={SESSION_DAYS*86400}{secure}'}

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        try: data = self.read_json()
        except ValueError as e: return self.send_json(400, {'error':'bad_request','message':str(e)})
        if path == '/api/register':
            if not self.rate_limit('register', 5): return
            email = str(data.get('email','')).strip().lower(); name = str(data.get('name','')).strip(); password = str(data.get('password',''))
            if len(email) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email): return self.send_json(400, {'message':'Bitte eine gültige E-Mail-Adresse eingeben.'})
            if not name or len(name) > 48: return self.send_json(400, {'message':'Name muss zwischen 1 und 48 Zeichen lang sein.'})
            if len(password) < 12 or len(password) > 200: return self.send_json(400, {'message':'Das Passwort muss mindestens 12 Zeichen haben.'})
            salt, hashed = password_hash(password)
            role = 'owner' if OWNER_EMAIL and email == OWNER_EMAIL else 'user'
            tier = 'ultimate' if role == 'owner' else 'free'
            try:
                with db() as con:
                    cur = con.execute('INSERT INTO users(email,display_name,password_hash,password_salt,role,tier,created_at) VALUES(?,?,?,?,?,?,?)',
                                      (email,name,hashed,salt,role,tier,int(time.time())))
                    uid = cur.lastrowid
            except sqlite3.IntegrityError: return self.send_json(409, {'message':'Für diese E-Mail-Adresse gibt es bereits ein Konto.'})
            csrf, headers = self.create_session(uid)
            with db() as con: row = con.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
            return self.send_json(201, {'user':user_payload(row),'csrf':csrf}, headers)
        if path == '/api/login':
            if not self.rate_limit('login', 10): return
            email = str(data.get('email','')).strip().lower(); password = str(data.get('password',''))
            with db() as con: row = con.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
            if not row:
                # Similar work factor for unknown accounts.
                password_hash(password or 'invalid-password', '00112233445566778899aabbccddeeff')
                return self.send_json(401, {'message':'E-Mail oder Passwort ist falsch.'})
            _, candidate = password_hash(password, row['password_salt'])
            if not hmac.compare_digest(candidate, row['password_hash']): return self.send_json(401, {'message':'E-Mail oder Passwort ist falsch.'})
            csrf, headers = self.create_session(row['id'])
            return self.send_json(200, {'user':user_payload(row),'csrf':csrf}, headers)
        if path == '/api/logout':
            session = self.get_session()
            if not self.require_csrf(session): return
            cookie = SimpleCookie(self.headers.get('Cookie','')); morsel = cookie.get('sdr_session')
            if morsel:
                with db() as con: con.execute('DELETE FROM sessions WHERE token_hash=?',(token_hash(morsel.value),))
            return self.send_json(200, {'ok':True}, {'Set-Cookie':'sdr_session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0'})
        if path == '/api/admin/tier':
            session = self.get_session()
            if not session or session['role'] != 'owner': return self.send_json(403, {'message':'Nur das Owner-Konto darf das.'})
            if not self.require_csrf(session): return
            email = str(data.get('email','')).strip().lower(); tier = str(data.get('tier',''))
            if tier not in TIERS: return self.send_json(400, {'message':'Unbekannte Abo-Stufe.'})
            with db() as con:
                cur = con.execute("UPDATE users SET tier=? WHERE email=? AND role!='owner'",(tier,email))
                if not cur.rowcount: return self.send_json(404, {'message':'Nutzer nicht gefunden oder Owner-Konto.'})
            return self.send_json(200, {'ok':True,'message':f'Abo für {email} auf {TIER_NAMES[tier]} gesetzt.'})
        return self.send_json(404, {'message':'API-Endpunkt nicht gefunden.'})

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path); path = parsed.path
        if path == '/api/me':
            row = self.get_session()
            if not row: return self.send_json(200, {'user':None})
            return self.send_json(200, {'user':user_payload(row),'csrf':row['csrf']})
        if path == '/api/health':
            return self.send_json(200, {'ok':True,'api_key_configured':bool(API_KEY),'database':'sqlite'})
        if path == '/api/search':
            row = self.get_session()
            if not row: return self.send_json(401, {'message':'Bitte zuerst anmelden.'})
            if not API_KEY: return self.send_json(503, {'error':'missing_key','message':'Der GamePrices-API-Schlüssel fehlt. Bitte GAMEPRICES_API_KEY in Render einrichten.'})
            params = urllib.parse.parse_qs(parsed.query); term=(params.get('term') or [''])[0].strip(); country=(params.get('country') or ['DE'])[0].upper()
            provider=(params.get('provider') or [''])[0].strip().lower()
            if not term or len(term)>100: return self.send_json(400, {'message':'Bitte einen Spieletitel (max. 100 Zeichen) eingeben.'})
            if not re.fullmatch(r'[A-Z]{2}', country): return self.send_json(400, {'message':'Ungültige Länderkennung.'})
            features=user_payload(row)['features']
            if provider and provider != 'all' and not features['all_stores']:
                return self.send_json(403, {'message':'Store-Filter sind ab Pro verfügbar.'})
            try:
                query={'q':term,'country':country,'limit':'30'}
                if provider and provider!='all': query['provider']=provider
                elif not features['all_stores']: query['provider']='steam'
                url=API_BASE+'/best?'+urllib.parse.urlencode(query)
                req=urllib.request.Request(url,headers={'X-API-Key':API_KEY,'User-Agent':'SteamDealRadar/2.0','Accept':'application/json'})
                with urllib.request.urlopen(req,timeout=25) as response: data=json.loads(response.read().decode())
                items=data.get('items',[]) if isinstance(data,dict) else []
                results=[]
                for item in items:
                    price=item.get('price') or {}
                    results.append({'name':item.get('name') or item.get('game_name') or 'Unbekanntes Spiel','image':item.get('image_url') or '',
                      'price':price.get('current'),'base':price.get('base'),'currency':price.get('currency') or 'EUR',
                      'discount':price.get('discount_percent'),'provider':item.get('provider') or '', 'url':item.get('url') or '',
                      'region':price.get('region') or '', 'subscription_only':price.get('subscription_only',False)})
                if row['tier'] == 'free' and row['role'] != 'owner': results=results[:3]
                elif row['tier'] == 'radar' and row['role'] != 'owner': results=results[:10]
                if features['compare']:
                    results.sort(key=lambda x: (x['price'] is None, float(x['price']) if x['price'] is not None and str(x['price']).replace('.','',1).isdigit() else 1e15))
                else: results=results[:10]
                return self.send_json(200, {'items':results,'features':features})
            except urllib.error.HTTPError as e:
                return self.send_json(502, {'error':'provider_error','message':f'Der Preisdienst meldet HTTP {e.code}. Prüfe API-Key und Tarif.'})
            except Exception as e:
                print('GamePrices error:',repr(e))
                return self.send_json(502, {'error':'provider_error','message':'Der Preisdienst ist gerade nicht erreichbar. Bitte später erneut versuchen.'})
        if path.startswith('/api/'): return self.send_json(404, {'message':'API-Endpunkt nicht gefunden.'})
        if path == '/': self.path = '/index.html'
        return super().do_GET()

if __name__ == '__main__':
    init_db()
    port=int(os.environ.get('PORT','8000'))
    print(f'Steam Deal Radar 2.0 listening on {port}; GamePrices key configured: {bool(API_KEY)}; owner configured: {bool(OWNER_EMAIL)}')
    ThreadingHTTPServer(('0.0.0.0',port),Handler).serve_forever()

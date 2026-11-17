"""GameRadar backend: SuperDuperBundle search + persistent accounts.
Set DATABASE_PATH to a persistent Render disk path (for example /var/data/gameradar.sqlite3).
Set OWNER_EMAIL to the exact email used for the owner account.
Set SUPERDUPERBUNDLE_API_KEY to the partner key (optional but recommended).
Instant Gaming and G2A adapters are prepared but require approved provider API access.
"""
import hashlib, hmac, html, json, os, re, secrets, sqlite3, threading, time, urllib.error, urllib.parse, urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

API_BASE = "https://superduperbundle.com/api/v1/lookup/"
API_KEY = os.environ.get("SUPERDUPERBUNDLE_API_KEY", "").strip()
# Credentials are intentionally optional. No provider endpoint is guessed or hard-coded.
INSTANT_GAMING_RAPIDAPI_KEY = os.environ.get("INSTANT_GAMING_RAPIDAPI_KEY", "").strip()
INSTANT_GAMING_RAPIDAPI_HOST = os.environ.get("INSTANT_GAMING_RAPIDAPI_HOST", "").strip()
G2A_CLIENT_ID = os.environ.get("G2A_CLIENT_ID", "").strip()
G2A_CLIENT_SECRET = os.environ.get("G2A_CLIENT_SECRET", "").strip()
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

def fetch_json_url(url, timeout=18):
    req=urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 (compatible; GameRadar/2.0)','Accept':'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8','replace'))

def steam_search(term, country='de', limit=10):
    query=urllib.parse.urlencode({'term':term,'l':'german','cc':country})
    payload=fetch_json_url('https://store.steampowered.com/api/storesearch/?'+query)
    out=[]
    for game in (payload.get('items') or [])[:max(1,min(limit,10))]:
        if not isinstance(game,dict) or not game.get('id'): continue
        price_data=game.get('price') or {}
        final=price_data.get('final')
        out.append({'name':game.get('name') or 'Unbekanntes Spiel','appid':game.get('id'),
          'image':game.get('tiny_image') or f"https://cdn.akamai.steamstatic.com/steam/apps/{game.get('id')}/header.jpg",
          'price':(float(final)/100 if final is not None else None),'base':(float(price_data.get('initial'))/100 if price_data.get('initial') is not None else None),
          'currency':price_data.get('currency') or 'EUR','discount':price_data.get('discount_percent') or 0,
          'provider':'steam','provider_name':'Steam Store','url':f"https://store.steampowered.com/app/{game.get('id')}/",
          'offers':[],'store_count':1,'offer_count':1 if final is not None else 0,'source':'Steam Store'})
    return out

def steam_app_details(appid, country='de'):
    query=urllib.parse.urlencode({'appids':str(int(appid)),'l':'german','cc':country})
    payload=fetch_json_url('https://store.steampowered.com/api/appdetails?'+query)
    entry=payload.get(str(int(appid))) or {}
    if not entry.get('success') or not isinstance(entry.get('data'),dict): return None
    d=entry['data']
    def clean_text(value):
        value=html.unescape(re.sub(r'<[^>]*>', ' ', str(value or '')))
        return re.sub(r'\s+',' ',value).strip()
    po=d.get('price_overview') or {}
    screenshots=[{'thumb':x.get('path_thumbnail'),'full':x.get('path_full')} for x in (d.get('screenshots') or []) if isinstance(x,dict)]
    movies=[]
    for m in (d.get('movies') or []):
        if not isinstance(m,dict): continue
        movies.append({'name':m.get('name') or 'Gameplay / Trailer','thumbnail':m.get('thumbnail') or '',
          'mp4':(m.get('mp4') or {}).get('480') or (m.get('mp4') or {}).get('max') or '',
          'webm':(m.get('webm') or {}).get('480') or (m.get('webm') or {}).get('max') or ''})
    release=d.get('release_date') or {}
    return {'appid':int(appid),'name':d.get('name') or 'Unbekanntes Spiel','type':d.get('type') or '',
      'short_description':clean_text(d.get('short_description')),'description':clean_text(d.get('about_the_game') or d.get('detailed_description')),
      'header_image':d.get('header_image') or '', 'background':d.get('background') or '',
      'developers':d.get('developers') or [],'publishers':d.get('publishers') or [],
      'genres':[x.get('description') for x in (d.get('genres') or []) if isinstance(x,dict)],
      'release_date':release.get('date') or '', 'coming_soon':bool(release.get('coming_soon')),
      'platforms':d.get('platforms') or {},'screenshots':screenshots,'movies':movies,
      'price':(float(po.get('final',0))/100 if po else None),'base':(float(po.get('initial',0))/100 if po else None),
      'discount':po.get('discount_percent',0),'currency':po.get('currency') or 'EUR',
      'steam_url':f'https://store.steampowered.com/app/{int(appid)}/'}

def steam_suggestions(country='de'):
    query=urllib.parse.urlencode({'cc':country,'l':'german'})
    payload=fetch_json_url('https://store.steampowered.com/api/featuredcategories/?'+query)
    out=[]; seen=set()
    for category in ('top_sellers','specials','new_releases','coming_soon'):
        section=payload.get(category) or {}
        for game in (section.get('items') or []):
            appid=game.get('id')
            if not appid or appid in seen: continue
            seen.add(appid); price_data=game.get('final_price')
            out.append({'name':game.get('name') or 'Unbekanntes Spiel','appid':appid,
              'image':game.get('header_image') or f'https://cdn.akamai.steamstatic.com/steam/apps/{appid}/header.jpg',
              'price':(float(price_data)/100 if price_data is not None else None),
              'currency':'EUR','discount':game.get('discount_percent') or 0,'provider':'steam',
              'provider_name':'Steam Store','url':f'https://store.steampowered.com/app/{appid}/',
              'category':category,'source':'Steam Store'})
            if len(out)>=16: return out
    return out

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
        if path=='/api/profile':
            u=self.current_user()
            if not u: return self.send_json(401,{'message':'Bitte zuerst einloggen.'})
            username=str(data.get('username','')).strip()[:32]
            if len(username)<2: return self.send_json(400,{'message':'Der Benutzername muss mindestens 2 Zeichen lang sein.'})
            with db() as c:
                c.execute('UPDATE users SET username=? WHERE id=?',(username,u['id']))
                updated=c.execute('SELECT * FROM users WHERE id=?',(u['id'],)).fetchone()
            return self.send_json(200,{'ok':True,'user':self.user_json(dict(updated))})
        if path=='/api/admin/user':
            admin=self.current_user()
            if not admin or admin.get('role')!='owner': return self.send_json(403,{'message':'Owner-Berechtigung erforderlich.'})
            try: target_id=int(data.get('id'))
            except (TypeError,ValueError): return self.send_json(400,{'message':'Ungültige Benutzer-ID.'})
            tier=str(data.get('tier','free')).lower()
            role=str(data.get('role','user')).lower()
            if tier not in ('free','radar','radar_plus','ultimate') or role not in ('user','owner'):
                return self.send_json(400,{'message':'Ungültige Rolle oder Tarifstufe.'})
            with db() as c:
                target=c.execute('SELECT id,email FROM users WHERE id=?',(target_id,)).fetchone()
                if not target: return self.send_json(404,{'message':'Benutzer nicht gefunden.'})
                if OWNER_EMAIL and target['email'].lower()==OWNER_EMAIL:
                    return self.send_json(400,{'message':'Das fest konfigurierte Betreiber-Konto kann hier nicht geändert werden.'})
                c.execute('UPDATE users SET tier=?,role=? WHERE id=?',(tier,role,target_id))
            return self.send_json(200,{'ok':True,'message':'Benutzerkonto aktualisiert.'})
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
        if parsed.path=='/api/history':
            u=self.current_user()
            if not u: return self.send_json(401,{'message':'Bitte zuerst einloggen.'})
            with db() as c: rows=c.execute('SELECT term,created_at FROM search_history WHERE user_id=? ORDER BY id DESC LIMIT 100',(u['id'],)).fetchall()
            return self.send_json(200,{'items':[dict(x) for x in rows]})
        if parsed.path=='/api/admin/users':
            u=self.current_user()
            if not u or u.get('role')!='owner': return self.send_json(403,{'message':'Owner-Berechtigung erforderlich.'})
            with db() as c: rows=c.execute('SELECT id,email,username,role,tier,created_at FROM users ORDER BY created_at DESC').fetchall()
            return self.send_json(200,{'items':[dict(x) for x in rows]})
        if parsed.path=='/api/suggestions':
            country=(params.get('country') or ['de'])[0].lower()
            if country not in ('de','us','gb','fr','es','it','pl','nl'): country='de'
            cached=cache_get(('steam_suggestions',country))
            try:
                items=cached if cached is not None else steam_suggestions(country)
                if cached is None: cache_set(('steam_suggestions',country),items)
                return self.send_json(200,{'items':items,'source':'Steam Store','cached_for_seconds':CACHE_TTL})
            except Exception as e:
                return self.send_json(502,{'items':[],'message':f'Spielvorschläge konnten gerade nicht geladen werden: {str(e)}'})
        if parsed.path=='/api/steam/details':
            appid=(params.get('appid') or [''])[0]
            try:
                if not appid.isdigit(): return self.send_json(400,{'message':'Ungültige Steam-App-ID.'})
                country=(params.get('country') or ['de'])[0].lower()
                details=steam_app_details(appid,country)
                if not details: return self.send_json(404,{'message':'Keine Steam-Spielinformationen gefunden.'})
                return self.send_json(200,{'game':details,'source':'Steam Store'})
            except Exception as e: return self.send_json(502,{'message':f'Steam-Spielinformationen nicht erreichbar: {str(e)}'})
        if parsed.path=='/api/game':
            name=(params.get('name') or [''])[0].strip()
            appid=(params.get('appid') or [''])[0].strip()
            country=(params.get('country') or ['de'])[0].lower()
            if not name and not appid: return self.send_json(400,{'message':'Spielname fehlt.'})
            steam=None
            try:
                if appid.isdigit(): steam=steam_app_details(appid,country)
                elif name:
                    found=steam_search(name,country,10)
                    match=next((x for x in found if x.get('name','').casefold()==name.casefold()),None)
                    candidate=match or (found[0] if found else None)
                    if candidate: steam=steam_app_details(candidate['appid'],country)
            except Exception: steam=None
            sdb_game=None; attribution={'text':'Prices by SuperDuperBundle','url':'https://superduperbundle.com/'}
            if name:
                try:
                    payload,remaining=fetch_sdb(name,5); items=normalise(payload)
                    sdb_game=next((x for x in items if x.get('name','').casefold()==name.casefold()),None) or (items[0] if items else None)
                    attribution=payload.get('attribution') or attribution
                except Exception: pass
            if not steam and not sdb_game: return self.send_json(502,{'message':'Spielinformationen sind gerade nicht erreichbar. Bitte später erneut versuchen.'})
            game={'name':(steam or {}).get('name') or (sdb_game or {}).get('name'),
                  'image':(steam or {}).get('header_image') or (sdb_game or {}).get('image') or '',
                  'price':(steam or {}).get('price') if steam else (sdb_game or {}).get('price'),
                  'currency':(steam or {}).get('currency') if steam else (sdb_game or {}).get('currency','EUR'),
                  'offers':(sdb_game or {}).get('offers') or [],'store_count':(sdb_game or {}).get('store_count',0),
                  'offer_count':(sdb_game or {}).get('offer_count',0),'url':(sdb_game or {}).get('url') or (steam or {}).get('steam_url',''),
                  'steam':steam,'source':'Steam Store + SuperDuperBundle' if steam and sdb_game else ('Steam Store' if steam else 'SuperDuperBundle')}
            return self.send_json(200,{'game':game,'attribution':attribution})
        if parsed.path=='/api/favorites':
            u=self.current_user()
            if not u: return self.send_json(401,{'message':'Bitte zuerst einloggen.'})
            with db() as c: rows=c.execute('SELECT game_name,created_at FROM favorites WHERE user_id=? ORDER BY created_at DESC',(u['id'],)).fetchall()
            return self.send_json(200,{'items':[dict(x) for x in rows]})
        if parsed.path=='/api/search':
            platform=(params.get('platform') or ['steam'])[0].strip().lower()
            if platform == 'instantgaming':
                if not (INSTANT_GAMING_RAPIDAPI_KEY and INSTANT_GAMING_RAPIDAPI_HOST):
                    return self.send_json(503, {'message':'Instant Gaming ist vorbereitet, aber noch nicht live: Es fehlen ein gültiger RapidAPI-Key und der Host der ausgewählten Instant-Gaming-Scraper-API. Die offizielle Instant-Gaming-Dokumentation bietet keine frei nutzbare Produktsuch-API. Erst nach Auswahl und Freigabe eines konkreten API-Anbieters kann die Suche aktiviert werden.'})
                return self.send_json(501, {'message':'RapidAPI-Zugangsdaten sind vorhanden. Für die Aktivierung fehlt noch die konkrete API-Spezifikation (Such-Endpunkt und Antwortformat) des ausgewählten Instant-Gaming-Scrapers. Es wird absichtlich kein unbekannter Endpunkt geraten.'})
            if platform == 'g2a':
                if not (G2A_CLIENT_ID and G2A_CLIENT_SECRET):
                    return self.send_json(503, {'message':'G2A ist vorbereitet, aber noch nicht live: Es fehlen G2A-API-Zugangsdaten. Die offizielle Export API ist auf Seller-Store-/Partner-Integrationen ausgelegt und nicht automatisch ein frei nutzbarer Preisvergleichs-Feed. Vor einer Aktivierung muss G2A den passenden Nutzungsumfang freigeben.'})
                return self.send_json(501, {'message':'G2A-Zugangsdaten sind konfiguriert. Die offizielle Export API ist kein allgemeiner Preisvergleichs-Feed. Vor der technischen Aktivierung müssen der von G2A genehmigte API-Umfang und die konkrete Dokumentation für diesen Anwendungsfall bestätigt werden.'})
            if platform == 'xbox':
                return self.send_json(503, {'message':'Xbox bleibt in GameRadar enthalten. Die Anfrage für den API-Zugang wurde gestellt; die schriftliche Freigabe für den kommerziellen Preisvergleich steht noch aus. Deshalb ist die Xbox-Suche vorerst noch nicht live.'})
            if platform == 'psn':
                return self.send_json(503, {'message':'PlayStation bleibt in GameRadar enthalten. Die Anfrage für den API-Zugang wurde gestellt; die schriftliche Freigabe für den kommerziellen Preisvergleich steht noch aus. Deshalb ist die PlayStation-Suche vorerst noch nicht live.'})
            if platform not in ('steam','epic','gog'):
                return self.send_json(400,{'message':'Unbekannte Plattform.'})
            term=(params.get('term') or [''])[0].strip()
            if not term: return self.send_json(400,{'message':'Bitte gib einen Spieletitel ein.'})
            if len(term)>120: return self.send_json(400,{'message':'Suchbegriff zu lang.'})
            try: limit=max(1,min(int((params.get('limit') or ['5'])[0]),5))
            except ValueError: limit=5
            key=(term.casefold(),limit); data=cache_get(key)
            try:
                sdb_error=None
                if data is None:
                    try:
                        payload,remaining=fetch_sdb(term,limit); items=normalise(payload)
                        data={'items':items,'count':len(items),'attribution':payload.get('attribution') or {'text':'Prices by SuperDuperBundle','url':'https://superduperbundle.com/'},'cached_for_seconds':CACHE_TTL,'rate_limit_remaining':remaining}
                        cache_set(key,data)
                    except Exception as e:
                        sdb_error=e; data={'items':[],'count':0,'attribution':{'text':'Prices by SuperDuperBundle','url':'https://superduperbundle.com/'}}
                if platform in ('steam','epic','gog'):
                    def matches_platform(item):
                        offers=item.get('offers') or []
                        candidates=offers if offers else [item]
                        for offer in candidates:
                            drm=str(offer.get('drm') or '').lower()
                            store=str(offer.get('store') or offer.get('provider') or '').lower()
                            store_name=str(offer.get('store_name') or offer.get('provider_name') or '').lower()
                            hay=' '.join((drm,store,store_name))
                            if platform=='steam' and 'steam' in hay: return True
                            if platform=='epic' and 'epic' in hay: return True
                            if platform=='gog' and 'gog' in hay: return True
                        return False
                    data=dict(data)
                    data['items']=[item for item in data.get('items',[]) if matches_platform(item)]
                    data['count']=len(data['items'])
                    if platform=='steam' and not data['items']:
                        try:
                            country=(params.get('country') or ['de'])[0].lower()
                            steam_items=steam_search(term,country,limit)
                            data={'items':steam_items,'count':len(steam_items),
                                  'attribution':{'text':'Steam Store','url':'https://store.steampowered.com/'},'source':'Steam Store'}
                        except Exception as steam_error:
                            if sdb_error: raise RuntimeError(f'Suche derzeit nicht verfügbar. SuperDuperBundle: {sdb_error} Steam: {steam_error}')
                            raise RuntimeError(f'Keine Steam-Treffer gefunden; Steam Store nicht erreichbar: {steam_error}')
                if not data.get('items') and sdb_error and platform!='steam': raise sdb_error
                u=self.current_user()
                if u:
                    with db() as c: c.execute('INSERT INTO search_history(user_id,term) VALUES(?,?)',(u['id'],term[:120]))
                return self.send_json(200,data)
            except Exception as e: return self.send_json(502,{'message':str(e)})
        if parsed.path=='/api/health':
            return self.send_json(200,{'ok':True,'provider':'SuperDuperBundle','api_key_configured':bool(API_KEY),'database':'sqlite','database_path':DB_PATH,'persistent_disk_required':True,'platform_search':['steam','epic','gog'],'coming_soon_platforms':['instantgaming','g2a','xbox','psn'],'instant_gaming_ui':True,'instant_gaming_api_configured':bool(INSTANT_GAMING_RAPIDAPI_KEY and INSTANT_GAMING_RAPIDAPI_HOST),'g2a_ui':True,'g2a_credentials_configured':bool(G2A_CLIENT_ID and G2A_CLIENT_SECRET),'subscriptions_ui':True,'profile_ui':True,'game_detail_ui':True,'owner_dashboard':True,'payments_enabled':False})
        return super().do_GET()

init_db()
if __name__=='__main__':
    port=int(os.environ.get('PORT','8000')); server=ThreadingHTTPServer(('0.0.0.0',port),Handler)
    print(f'GameRadar listening on {port}; database={DB_PATH}; SDB key configured={bool(API_KEY)}; IG configured={bool(INSTANT_GAMING_RAPIDAPI_KEY and INSTANT_GAMING_RAPIDAPI_HOST)}; G2A credentials configured={bool(G2A_CLIENT_ID and G2A_CLIENT_SECRET)}')
    server.serve_forever()

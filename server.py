"""Steam Deal Radar 2.0 - SuperDuperBundle API backend.

The API key is optional. Without one, the API's public limit applies.
Set SUPERDUPERBUNDLE_API_KEY in Render to use the verified partner limit.
Never put the key in HTML, JavaScript, or a public repository.
"""

import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

API_BASE = "https://superduperbundle.com/api/v1/lookup/"
API_KEY = (
    os.environ.get("SUPERDUPERBUNDLE_API_KEY", "").strip()
    or os.environ.get("SDB_API_KEY", "").strip()
)
CLIENT_NAME = "steam-deal-radar-2-0"
USER_AGENT = "SteamDealRadar/2.0 (+https://steam-deal-radar-2-0.onrender.com)"
CACHE_TTL_SECONDS = 15 * 60
CACHE = {}
CACHE_LOCK = threading.Lock()


def json_bytes(payload):
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def cached_get(key):
    now = time.time()
    with CACHE_LOCK:
        entry = CACHE.get(key)
        if not entry:
            return None
        expires_at, value = entry
        if expires_at <= now:
            CACHE.pop(key, None)
            return None
        return value


def cached_set(key, value):
    with CACHE_LOCK:
        CACHE[key] = (time.time() + CACHE_TTL_SECONDS, value)
        # Keep the in-memory cache bounded.
        if len(CACHE) > 500:
            now = time.time()
            expired = [k for k, (expires, _) in CACHE.items() if expires <= now]
            for old_key in expired:
                CACHE.pop(old_key, None)
            while len(CACHE) > 500:
                CACHE.pop(next(iter(CACHE)))


def fetch_superduperbundle(term, limit=5):
    params = {
        "q": term,
        "limit": str(max(1, min(int(limit), 5))),
        "client": CLIENT_NAME,
    }
    url = API_BASE + "?" + urllib.parse.urlencode(params)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    if API_KEY:
        headers["X-API-Key"] = API_KEY

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
            remaining = response.headers.get("X-RateLimit-Remaining")
            return payload, remaining
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(body)
            message = detail.get("message") or detail.get("error") or body
        except (json.JSONDecodeError, AttributeError):
            message = body or "Unbekannter API-Fehler"
        if error.code == 429:
            retry_after = error.headers.get("Retry-After", "")
            raise RuntimeError(
                "API-Limit erreicht. "
                + (f"Bitte in {retry_after} Sekunden erneut versuchen." if retry_after else "Bitte später erneut versuchen.")
            ) from error
        raise RuntimeError(f"SuperDuperBundle antwortet mit HTTP {error.code}: {message}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError("SuperDuperBundle ist momentan nicht erreichbar. Bitte später erneut versuchen.") from error
    except json.JSONDecodeError as error:
        raise RuntimeError("SuperDuperBundle hat keine gültige JSON-Antwort geliefert.") from error


def normalise_results(payload):
    results = payload.get("results", []) if isinstance(payload, dict) else []
    items = []
    for game in results:
        if not isinstance(game, dict):
            continue
        lowest = game.get("lowest") or {}
        if not isinstance(lowest, dict):
            lowest = {}
        # The API's prices are listed in USD. It does not offer a country selector.
        price = lowest.get("price")
        currency = game.get("currency") or "USD"
        items.append({
            "name": game.get("name") or "Unbekanntes Spiel",
            "game_name": game.get("name") or "",
            "image": game.get("image") or "",
            "price": price,
            "base": game.get("list_price"),
            "currency": currency,
            "discount": lowest.get("discount_pct"),
            "provider": lowest.get("store") or "",
            "provider_name": lowest.get("store_name") or lowest.get("store") or "Store",
            "url": game.get("url") or "",
            "region": lowest.get("region") or "",
            "drm": lowest.get("drm") or "",
            "store_type": lowest.get("store_type") or "",
            "checked_at": lowest.get("checked_at") or "",
            "store_count": game.get("store_count", 0),
            "offer_count": game.get("offer_count", 0),
            "offers": game.get("offers") or [],
            "state": game.get("state") or "",
            "subscription_only": False,
        })
    return items


class Handler(SimpleHTTPRequestHandler):
    def send_json(self, status, payload, extra_headers=None):
        body = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for name, value in (extra_headers or {}).items():
            self.send_header(name, str(value))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/search":
            params = urllib.parse.parse_qs(parsed.query)
            term = (params.get("term") or [""])[0].strip()
            if not term:
                return self.send_json(400, {
                    "error": "missing_term",
                    "message": "Bitte gib einen Spieletitel ein.",
                })
            if len(term) > 120:
                return self.send_json(400, {
                    "error": "term_too_long",
                    "message": "Der Suchbegriff darf höchstens 120 Zeichen lang sein.",
                })

            # SuperDuperBundle currently returns listed PC-game key prices in USD.
            # The old country/provider query parameters are intentionally not forwarded:
            # this API does not document country or store filters for this endpoint.
            try:
                limit = int((params.get("limit") or ["5"])[0])
                limit = max(1, min(limit, 5))
            except ValueError:
                limit = 5

            cache_key = (term.casefold(), limit)
            cached = cached_get(cache_key)
            try:
                if cached is None:
                    payload, remaining = fetch_superduperbundle(term, limit)
                    items = normalise_results(payload)
                    cached = {
                        "items": items,
                        "count": len(items),
                        "attribution": payload.get("attribution") or {
                            "text": "Prices by SuperDuperBundle",
                            "url": "https://superduperbundle.com/",
                        },
                        "cached_for_seconds": CACHE_TTL_SECONDS,
                        "rate_limit_remaining": remaining,
                    }
                    cached_set(cache_key, cached)
                return self.send_json(200, cached)
            except Exception as error:
                return self.send_json(502, {
                    "error": "provider_error",
                    "message": str(error),
                })

        if parsed.path == "/api/health":
            return self.send_json(200, {
                "ok": True,
                "provider": "SuperDuperBundle",
                "api_key_configured": bool(API_KEY),
                "api_key_optional": True,
                "partner_key_header": "X-API-Key",
                "cache_ttl_seconds": CACHE_TTL_SECONDS,
            })

        return super().do_GET()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(
        f"Steam Deal Radar listening on {port}; "
        f"SuperDuperBundle partner key configured: {bool(API_KEY)}"
    )
    server.serve_forever()

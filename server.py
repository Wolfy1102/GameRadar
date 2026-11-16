import json
import os
import urllib.parse
import urllib.request
import urllib.error
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

API_BASE = "https://gameprices.now/api/v1"
API_KEY = os.environ.get("GAMEPRICES_API_KEY", "").strip()
USER_AGENT = "GameRadar/1.0 (https://steam-deal-radar-2-0.onrender.com)"

class Handler(SimpleHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def api_get(self, path, params=None):
        query = urllib.parse.urlencode(params or {})
        url = f"{API_BASE}/{path}" + (f"?{query}" if query else "")
        request = urllib.request.Request(url, headers={
            "X-API-Key": API_KEY,
            "User-Agent": USER_AGENT,
            "Accept": "application/json"
        })
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            try:
                detail = json.loads(error.read().decode("utf-8"))
            except Exception:
                detail = {"message": "Der Datendienst hat eine Fehlermeldung zurückgegeben."}
            raise RuntimeError(detail.get("message") or detail.get("error") or f"API-Fehler {error.code}") from error

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/search":
            if not API_KEY:
                return self.send_json(503, {"error": "missing_key", "message": "Der API-Schlüssel fehlt noch. Bitte GAMEPRICES_API_KEY in Render einrichten."})
            params = urllib.parse.parse_qs(parsed.query)
            term = (params.get("term") or [""])[0].strip()
            country = (params.get("country") or ["DE"])[0].upper()
            provider = (params.get("provider") or [""])[0].strip().lower()
            if not term:
                return self.send_json(400, {"error": "missing_term", "message": "Bitte gib einen Spieletitel ein."})
            try:
                query = {"q": term, "country": country, "limit": "20"}
                if provider and provider != "all":
                    query["provider"] = provider
                data = self.api_get("best", query)
                items = data.get("items", []) if isinstance(data, dict) else []
                results = []
                for item in items:
                    price = item.get("price") or {}
                    results.append({
                        "name": item.get("name") or item.get("game_name") or "Unbekanntes Spiel",
                        "game_name": item.get("game_name") or item.get("name") or "",
                        "image": item.get("image_url") or "",
                        "price": price.get("current"),
                        "base": price.get("base"),
                        "currency": price.get("currency") or "",
                        "discount": price.get("discount_percent"),
                        "provider": item.get("provider") or "",
                        "url": item.get("url") or "",
                        "region": price.get("region") or "",
                        "subscription_only": price.get("subscription_only", False)
                    })
                return self.send_json(200, {"items": results})
            except Exception as error:
                return self.send_json(502, {"error": "provider_error", "message": str(error)})

        if parsed.path == "/api/health":
            return self.send_json(200, {"ok": True, "api_key_configured": bool(API_KEY)})

        return super().do_GET()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"GameRadar listening on {port}; GamePrices key configured: {bool(API_KEY)}")
    server.serve_forever()

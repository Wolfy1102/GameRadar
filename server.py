from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, urlencode
from urllib.request import Request, urlopen
import json
import os

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/search":
            params = parse_qs(parsed.query)
            term = params.get("term", [""])[0]
            country = params.get("cc", ["de"])[0]

            if not term.strip():
                self.send_json({"items": []})
                return

            query = urlencode({
                "term": term,
                "l": "german",
                "cc": country
            })

            url = "https://store.steampowered.com/api/storesearch/?" + query

            try:
                request = Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0"}
                )

                with urlopen(request, timeout=15) as response:
                    data = json.loads(response.read().decode("utf-8"))

                self.send_json(data)

            except Exception as error:
                print("Steam-Fehler:", error)
                self.send_json({
                    "error": "Steam konnte nicht erreicht werden."
                }, 502)

            return

        super().do_GET()

    def send_json(self, data, status=200):
        content = json.dumps(data).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

PORT = int(os.environ.get("PORT", 8000))

server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)

print(f"Steam Deal Radar läuft auf Port {PORT}")

server.serve_forever()

print("Steam Deal Radar läuft!")
print("Öffne http://127.0.0.1:8000")

server.serve_forever()

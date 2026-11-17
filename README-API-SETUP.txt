GAMERADAR – GAMEPRICES.NOW API EINRICHTEN

Diese Aktualisierung verbindet GameRadar serverseitig mit gameprices.now.
Der API-Schlüssel wird NICHT in HTML oder JavaScript gespeichert.

1) Account und API-Key
- Öffne https://gameprices.now/en/pricing
- Wähle einen passenden kostenpflichtigen Tarif.
- Erstelle/öffne deinen Account unter https://gameprices.now/en/account
- Erzeuge einen API-Key und kopiere ihn sicher. Er wird laut Anbieter nur einmal angezeigt.
- Teile den Key niemals im Chat oder in GitHub.

2) Render – Environment Variable
- Öffne https://dashboard.render.com/
- Wähle deinen GameRadar Web Service.
- Öffne Environment (oder Environment Variables).
- Add Environment Variable:
  Key: GAMEPRICES_API_KEY
  Value: DEIN_ECHTER_API_KEY
- Speichern und anschließend einen neuen Deploy starten.

3) Dateien in GitHub ersetzen
- Ersetze server.py mit dieser Version.
- Ersetze script.js mit dieser Version.
- Lass index.html und style.css aus dem aktuellen GameRadar-Design bestehen.
- In index.html muss das Regionsfeld weiterhin id="region" haben und den Wert "de" für Deutschland liefern.
- Render deployt nach dem Commit automatisch.

4) Test
- Öffne deine GameRadar-Seite.
- Suche nach einem bekannten Spiel, z. B. Elden Ring.
- Wenn Render keine API-Verbindung hat, prüfe /api/health:
  https://DEINE-RENDER-URL/api/health
  api_key_configured muss true anzeigen.

HINWEISE
- Die API deckt laut Dokumentation neun Stores ab: PlayStation, Xbox, Nintendo,
  Steam, Epic, EA, Ubisoft, Battle.net und GOG.
- Die API ist kostenpflichtig. Preise und Limits hängen vom Tarif ab.
- Der Schlüssel bleibt ausschließlich auf dem Render-Server.
- Aktuell liefert diese erste Integration Suchtreffer über /v1/best.
- Die Länderwahl nutzt ISO-Ländercodes; Deutschland ist DE.
- API-Dokumentation: https://gameprices.now/en/docs

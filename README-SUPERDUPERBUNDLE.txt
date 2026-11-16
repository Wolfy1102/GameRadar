STEAM DEAL RADAR 2.0 – SUPERDUPERBUNDLE API

Diese Version ersetzt die bisherige GamePrices-Anbindung in server.py.

RENDER EINRICHTEN
1. Öffne deinen Web Service in Render.
2. Environment öffnen.
3. Optional für dein verifiziertes Partnerlimit hinzufügen:
   Key: SUPERDUPERBUNDLE_API_KEY
   Value: DEIN_SUPERDUPERBUNDLE_API_KEY
4. Speichern und neu deployen.

Ohne API-Key funktioniert die API ebenfalls mit dem öffentlichen Limit.
Der Partner-Key wird serverseitig per X-API-Key-Header gesendet.
Niemals den Key in index.html, script.js oder GitHub-Code eintragen.

API-ROUTEN
GET /api/search?term=elden%20ring
GET /api/health

Die Suche liefert maximal fünf Treffer und cached Antworten lokal 15 Minuten.
Das Frontend kann weiter /api/search verwenden. Die vorhandenen Felder name,
image, price, currency, discount, provider und url bleiben erhalten; zusätzliche
Informationen wie offers, checked_at, DRM und Store-Anzahl kommen hinzu.

WICHTIGE EINSCHRÄNKUNGEN
- Diese API vergleicht PC-Spiel-Key-Preise und liefert Angebote von den in
  SuperDuperBundle verglichenen Quellen. Sie ist keine universelle Preis-API
  für native Xbox-, PlayStation- und Nintendo-Store-Spiele.
- Die API-Preise sind laut Dokumentation in USD. Der Endpunkt dokumentiert
  keinen Länderfilter; die bisherige DE-Auswahl ändert diese Preise nicht.
- Bei jeder angezeigten Preisangabe muss sichtbar „Prices by SuperDuperBundle“
  stehen und der Preis muss auf die jeweilige SuperDuperBundle-Vergleichsseite
  (Feld url) verlinken. checked_at anzeigen oder mindestens täglich aktualisieren.
- Daten nicht weiterverkaufen, nicht als eigene Datenbank spiegeln und nicht
  als eigene Preise ausgeben. Vor kostenpflichtigen Preiszugängen schriftlich
  mit SuperDuperBundle klären, ob das konkrete Abo-Modell zulässig ist.

DOKUMENTATION
https://superduperbundle.com/tools/api/

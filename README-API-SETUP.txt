GAMERADAR 2.0 – API- UND PLATTFORMSTATUS

BESTEHENDER DATENZUGANG
-----------------------
Die vorhandene Suche verwendet den SuperDuperBundle-Lookup-Endpunkt. Der
optionale Schlüssel wird serverseitig über SUPERDUPERBUNDLE_API_KEY gesetzt.
Der Schlüssel gehört ausschließlich in die Environment Variables von Render,
nicht in HTML, JavaScript oder GitHub.

Render:
1. Web Service öffnen.
2. Environment öffnen.
3. SUPERDUPERBUNDLE_API_KEY als Key und den eigenen Schlüssel als Value setzen,
   sofern der Anbieter für den Account einen Schlüssel verlangt.
4. Speichern und neu deployen.
5. /api/health öffnen und den Status prüfen.

PLATTFORMEN
-----------
Steam ist über den bestehenden Datenpartner suchbar. Epic Games und GOG können
über Store-/DRM-Angaben in dessen Suchantwort gefiltert werden. Das ist keine
direkte offizielle API-Anbindung an Epic oder GOG. Die Anfragen für eine
offizielle Nutzung sind gestellt; eine Freigabe ist noch offen.

Instant Gaming:
- Die Integration ist vorbereitet, aber nicht live.
- Noch fehlen schriftliche Freigabe für den konkreten Preisvergleich sowie eine
  konkrete, dokumentierte API mit Such-Endpunkt und Antwortformat.
- Vorgesehene Render-Variablen: INSTANT_GAMING_RAPIDAPI_KEY und
  INSTANT_GAMING_RAPIDAPI_HOST. Diese Werte allein aktivieren keine Integration.

G2A:
- Die Integration ist vorbereitet, aber nicht live.
- Die Export API ist nicht automatisch eine allgemeine Preisvergleichs-API.
  Der geplante Einsatzzweck muss von G2A freigegeben und technisch dokumentiert
  werden.
- Vorgesehene Render-Variablen: G2A_CLIENT_ID und G2A_CLIENT_SECRET.

Xbox und PlayStation bleiben enthalten. Die API-Anfragen wurden gestellt; die schriftliche Freigabe und die passenden technischen Angaben stehen noch aus. Beide Konsolen-Suchen bleiben bis dahin als Coming Soon sichtbar. Nintendo ist nicht enthalten.

WICHTIG
-------
Keine unbekannten Endpunkte erraten, keine nicht freigegebenen Quellen abfragen
und keine Preise simulieren. API-Integration erst nach passender Freigabe und
Dokumentation aktivieren. Vor einem kommerziellen Abo-Start muss auch die
Datennutzung durch den bestehenden Datenpartner für diesen Zweck geklärt sein.
Zahlungen sind in dieser Version deaktiviert.

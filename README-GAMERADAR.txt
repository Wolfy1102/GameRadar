GAMERADAR – UPDATE

Enthaltene Dateien:
- index.html
- style.css
- script.js
- manifest.webmanifest
- service-worker.js
- icon.svg

So verwendest du das Update:
1. Ersetze die gleichnamigen Dateien im GitHub-Repository.
2. Lass server.py und requirements.txt unverändert.
3. Behalte icon-180.png, icon-192.png und icon-512.png im Projekt.
4. Committe die Änderungen auf dem Branch main.
5. Render sollte anschließend automatisch neu deployen.

WICHTIG:
Aktuell ist nur die Steam-Suche technisch angebunden. Epic Games und GOG sind über die bestehende Datenquelle suchbar. Xbox und PlayStation bleiben als kommende Plattformen enthalten; die angefragten API-Freigaben stehen noch aus. Nintendo ist nicht enthalten.
Die Suche benötigt eine Internetverbindung; die App-Oberfläche wird offline
zwischengespeichert.

Plattformen: Steam, Epic Games, GOG, Instant Gaming und G2A. Instant Gaming und G2A benötigen noch freigegebene API-Zugänge und konkrete API-Spezifikationen; bis dahin sind sie als vorbereitete Auswahl sichtbar, aber nicht live.

NEUE PROFIL- UND DETAILFUNKTIONEN
- /profile.html: persönliches Profil mit Übersicht, Favoriten, Suchverlauf und Kontoeinstellungen.
- /game.html?name=SPIEL: Detailseite mit verfügbaren Spieldaten und Angebotsübersicht aus der Datenquelle.
- Favoriten können aus Suchergebnissen oder der Spielseite gespeichert werden.
- Owner sehen im Profil zusätzlich das Owner-Dashboard und können Benutzerrollen sowie Tarifstufen verwalten.
- Owner-API: GET /api/admin/users und POST /api/admin/user (nur Rolle owner).
- Tarifstufen: free, radar, radar_plus, ultimate. Zahlungsabwicklung ist weiterhin nicht aktiviert.
- Benutzer können ihren Benutzernamen in den Profileinstellungen ändern.

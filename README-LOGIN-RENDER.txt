GAMERADAR 2.0 – LOGIN & PERSISTENTE DATEN

1) Render -> dein Web Service -> Disks: Persistent Disk anlegen, Mount Path /var/data.
2) Environment Variables setzen:
   DATABASE_PATH=/var/data/gameradar.sqlite3
   OWNER_EMAIL=deine-eigene-e-mail@example.com
   SUPERDUPERBUNDLE_API_KEY=dein_partner_api_key
3) Deploy ausführen.
4) Auf der Website LOGIN / REGISTER anklicken und ein Konto mit exakt der OWNER_EMAIL erstellen.
   Dieses Konto erhält serverseitig role=owner und tier=ultimate. Bereits bestehende Konten
   mit dieser E-Mail werden beim nächsten Login/Serverstart hochgestuft.

Konten, Passwort-Hashes (PBKDF2), Sitzungen, Favoriten und Suchverlauf liegen in SQLite
auf dem Persistent Disk. Passwörter werden nicht im Klartext gespeichert.
Ohne Persistent Disk kann Render-Dateisystem bei Redeploy/Neustart verloren gehen.

API-Routen: POST /api/register, POST /api/login, POST /api/logout, GET /api/me,
GET/POST /api/favorites, GET /api/search, GET /api/health.

PLATTFORMEN: SuperDuperBundle-API v1 lookup dokumentiert die niedrigsten PC-Spiel-Key-Preise
und Angebote, nicht native Store-Preise für Xbox, PlayStation oder Nintendo. DRM-Felder
zeigen Aktivierungsplattform (z.B. Steam oder GOG), nicht den Store selbst. Deshalb wurden
Konsolen nicht fälschlich als live aktiviert. Epic/GOG werden nicht als eigener Preisfeed
garantiert; tatsächliche Treffer und offers kommen aus der SDB-Antwort.

SDB-Regeln: sichtbarer Link „Prices by SuperDuperBundle“, jeden Preis zur game url verlinken,
checked_at zeigen oder mindestens täglich aktualisieren; Daten nicht weiterverkaufen/spiegeln.
Vor einem kostenpflichtigen Abo-Modell schriftliche Freigabe einholen.

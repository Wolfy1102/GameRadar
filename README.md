# GameRadar 2.0

Diese ZIP baut auf der vorhandenen GameRadar-Version auf. Bestehendes Design, Login/Registrierung, serverseitige Sitzungen, SQLite-Datenbank, Owner-Rolle, Favoriten, Suchverlauf und Abo-Anzeige bleiben erhalten.

## Plattformstatus

- **Steam:** über den bestehenden SuperDuperBundle-Datenzugang suchbar.
- **Epic Games und GOG:** über die Store-/DRM-Angaben des bestehenden Datenpartners filterbar. Das sind keine direkten offiziellen Epic-/GOG-Feeds. Separate Anfragen zur offiziellen Datennutzung sind gestellt; eine Freigabe liegt noch nicht vor.
- **Instant Gaming und G2A:** Oberfläche und sichere Integrationsvorbereitung sind enthalten. Sie bleiben Coming Soon, bis der jeweilige Anbieter den konkreten Preisvergleichs-Einsatz schriftlich freigibt und die API-Spezifikation/Zugangsdaten vorliegen.
- **Xbox und PlayStation:** bleiben in der Plattformauswahl enthalten und sind Coming Soon, bis die angefragten API-Freigaben und technischen Angaben vorliegen.
- **Nintendo:** nicht enthalten (wie besprochen).

Es werden keine unbekannten API-Endpunkte geraten und keine Preise erfunden. API-Schlüssel werden ausschließlich serverseitig als Environment Variables gespeichert.

## Funktionen, die erhalten bleiben

- Registrierung und Login mit PBKDF2-HMAC-SHA256-Passwort-Hashing
- Serverseitige Sitzungen
- SQLite-Konten, Favoriten und Suchverlauf
- Owner-Konto über `OWNER_EMAIL` mit Ultimate-Rechten
- Owner Console zur manuellen Vergabe von Test-Abostufen
- Abo-Vorschau mit Free (0 €), Gamer (3,99 €/Monat oder 39,99 €/Jahr), Plus (8,99 €/Monat oder 89,99 €/Jahr) und Ultimate (16,99 €/Monat oder 169,99 €/Jahr)
- Responsive Oberfläche, PWA-Dateien und Service Worker
- Serverseitige Store-Suche über SuperDuperBundle

## Noch nicht aktiv

- Instant-Gaming- und G2A-Preisabfragen benötigen Freigabe, API-Dokumentation und Zugangsdaten.
- Für Epic Games und GOG werden derzeit nur die im bestehenden Datenpartner-Ergebnis enthaltenen Store-/DRM-Angaben gefiltert. Die direkte Nutzung offizieller Anbieter-Feeds ist nicht aktiviert.
- Zahlungen/Checkout sind deaktiviert. Die geplanten Abo-Preise sind eine Vorschau; Gamer, Plus und Ultimate sind Coming Soon und es werden keine Zahlungen ausgelöst.
- Die KI-Funktionen sind noch nicht angebunden.

## Lokal starten

Voraussetzung: Python 3.10 oder neuer.

```bash
python server.py
```

Danach `http://localhost:8000` öffnen.

## Render-Einstellungen

Environment Variables:

- `SUPERDUPERBUNDLE_API_KEY`: API-Key des bestehenden Datenpartners (falls für den Account erforderlich)
- `OWNER_EMAIL`: E-Mail-Adresse für das Owner-Konto
- `DATABASE_PATH=/var/data/gameradar.sqlite3`: Datenbankpfad auf einer persistenten Render Disk
- `INSTANT_GAMING_RAPIDAPI_KEY` und `INSTANT_GAMING_RAPIDAPI_HOST`: erst nach Auswahl und Freigabe einer konkreten API
- `G2A_CLIENT_ID` und `G2A_CLIENT_SECRET`: nur nach schriftlicher Freigabe und passender API-Dokumentation

Start Command: `python server.py`. Eine persistente Render Disk mit Mount Path `/var/data` ist erforderlich, damit Konten und Daten Deployments überstehen.

## Sicherheit und Hinweise

- API-Keys, `.env`-Dateien, Datenbankdateien und Passwörter nicht in GitHub veröffentlichen.
- Vor einem kommerziellen Start müssen die Nutzungsrechte der Datenquelle für den konkreten Preisvergleich und das geplante Abo-Modell schriftlich geklärt sein.
- Die Anwendung ist eine Beta-Grundlage. E-Mail-Verifizierung, Passwort-Reset, vollständige Rechtstexte, Zahlungsabwicklung und automatisierte Abo-Verwaltung sind nicht enthalten.

## Profile, game details and owner tools
- Open `/profile.html` after signing in for the account overview, favourites, search history and username settings.
- Search result cards link to `/game.html?name=...` for the available game and offer details returned by the data provider.
- Signed-in users can save games to favourites from result cards or the detail page.
- Owner accounts get an Owner Dashboard inside the profile. It lists accounts and lets the owner change user roles and tier labels (`free`, `radar`, `radar_plus`, `ultimate`).
- These tier changes are account metadata only. Checkout, recurring billing and automatic subscription enforcement are not enabled.


## Spielvorschläge, Screenshots und Gameplay

- Die Startseite lädt Steam-Store-Kategorien (Bestseller, Angebote, Neuerscheinungen und kommende Spiele) über `GET /api/suggestions?country=de`.
- Die Steam-Suche nutzt weiterhin zuerst den vorhandenen SuperDuperBundle-Preisvergleich. Wenn dort keine Steam-Treffer vorliegen oder der Anbieter nicht erreichbar ist, wird als Such-Fallback die Steam-Store-Suche verwendet.
- Spielseiten laden über `GET /api/game?appid=...` bzw. `GET /api/game?name=...` Beschreibung, Genres, Entwickler, Release-Datum, Screenshots und verfügbare Trailer aus den Steam-Store-Appdetails.
- Die Detailseite zeigt Preisangebote aus SuperDuperBundle nur dann, wenn diese in der Antwort vorhanden sind. Steam-Metadaten und Preisvergleichsangebote sind getrennte Datenquellen.
- Die Steam-Store-Endpunkte sind öffentlich erreichbare Store-Endpunkte, keine zugesicherte kommerzielle API. Vor einem kostenpflichtigen Betrieb müssen Nutzungsbedingungen und Rechte für die angezeigten Medien geprüft werden.

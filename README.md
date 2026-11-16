# Steam Deal Radar 2.0

Eine erweiterte Beta-Version auf Basis deines bisherigen GameRadar-Projekts. Das vorhandene Design und die serverseitige GamePrices-Suche bleiben erhalten. Dazu kommen Konten, Login, SQLite-Datenbank, Sitzungen, Rollen, ein Owner-Konto und eine Abo-Stufen-Verwaltung.

## Was funktioniert?

- Registrierung und Login mit Passwort-Hashing (PBKDF2-HMAC-SHA256)
- Serverseitige Sitzungen mit HttpOnly-Cookie, SameSite=Lax und CSRF-Token für geschützte Aktionen
- SQLite-Datenbank für Konten und Sitzungen
- Owner-Konto wird über `OWNER_EMAIL` festgelegt und erhält Ultimate-Funktionen dauerhaft
- Owner Console zum manuellen Freischalten von Test-Abos
- GamePrices-Suche über den Python-Server; der API-Key wird nicht an den Browser gesendet
- Free: maximal 3 Suchtreffer; Radar: bis zu 10; Pro/Ultimate: Vergleich und Store-Filter
- Responsive Oberfläche, PWA-Dateien und Service Worker
- Sicherheits-Header, einfache Rate-Limits für Registrierung und Login

## Noch nicht live / benötigt externe Konten

Diese Punkte sind absichtlich nicht als fertige Funktionen ausgegeben:

1. **Zahlungen:** Es ist noch kein Stripe-/PayPal-Checkout eingebaut. Die angezeigten 5/10/30 € sind geplante Preise. Die Owner Console vergibt Teststufen manuell.
2. **KI:** Der Ultimate-Tarif zeigt die geplante KI-Funktion, aber es ist noch kein KI-Anbieter angebunden.
3. **Store-Abdeckung:** Der Code fragt den GamePrices-Endpunkt `/api/v1/best` ab. Welche Stores tatsächlich Ergebnisse liefern, hängt von API-Tarif, API-Dokumentation und Verfügbarkeit ab. Die Plattform-Kacheln sind keine Garantie für aktive Integrationen.
4. **Produktionsreife:** Vor einem öffentlichen Bezahlstart fehlen u. a. E-Mail-Verifizierung, Passwort-Reset, Datenschutz-/Rechtstexte, Zahlungs-Webhooks, automatisierte Abo-Laufzeiten/Kündigungen, Monitoring und ein belastbarer Backup-/Restore-Prozess.

## Lokal starten

Voraussetzung: Python 3.10 oder neuer.

```bash
python server.py
```

Danach `http://localhost:8000` öffnen. Ohne `GAMEPRICES_API_KEY` funktionieren Registrierung/Login, aber die Live-Preissuche antwortet mit einem verständlichen Hinweis.

## Umgebungsvariablen

Kopiere `.env.example` als Vorlage. Die Datei wird nicht automatisch geladen. Setze die Werte in deiner Hosting-Plattform als Environment Variables:

- `PORT`: Port des Webservers (Render setzt ihn selbst)
- `GAMEPRICES_API_KEY`: persönlicher GamePrices-API-Key
- `OWNER_EMAIL`: E-Mail-Adresse, mit der du dich als Owner registrierst
- `DATABASE_PATH`: Pfad zur SQLite-Datei; auf Render z. B. `/var/data/gameradar.sqlite3`, wenn ein persistentes Disk unter `/var/data` eingebunden ist
- `SESSION_DAYS`: Sitzungsdauer in Tagen (Standard 14)
- `FORCE_HTTPS=1`: Secure-Cookie lokal/auf anderem Hosting erzwingen, wenn HTTPS aktiv ist

### Owner einrichten

1. Setze `OWNER_EMAIL` vor der ersten Registrierung auf deine eigene E-Mail-Adresse.
2. Starte den Server neu.
3. Registriere dich über „LOGIN / SIGN UP“ exakt mit dieser E-Mail.
4. Das Konto bekommt serverseitig `role=owner`, `tier=ultimate` und Zugriff auf die Owner Console.

Wenn das Konto bereits existiert, wird es beim nächsten Serverstart anhand von `OWNER_EMAIL` zum Owner hochgestuft. Andere bisherige Owner werden dabei auf normale Free-Konten zurückgesetzt.

## Render-Deployment

1. Lade die Dateien aus diesem ZIP in dein GitHub-Repository hoch.
2. In Render den bestehenden Web Service mit dem Repository verbinden.
3. Build Command: leer lassen (keine externen Python-Pakete nötig).
4. Start Command: `python server.py`.
5. Environment Variables setzen: `GAMEPRICES_API_KEY`, `OWNER_EMAIL` und `DATABASE_PATH=/var/data/gameradar.sqlite3`.
6. Ein persistentes Render Disk mit Mount Path `/var/data` hinzufügen. Ohne persistentes Laufwerk können Konten bei einem Neustart/Neu-Deploy verloren gehen.
7. Deploy ausführen und `/api/health` prüfen. `api_key_configured` muss `true` sein, wenn die Preissuche verwendet werden soll.

## Abo-Test

Melde dich als Owner an. Unten erscheint die Owner Console. Dort kannst du anhand der E-Mail-Adresse einem Testkonto die Stufe `free`, `radar`, `pro` oder `ultimate` zuweisen. Das ist nur eine interne Freischaltung und keine Zahlung.

## Wichtige Sicherheitshinweise

- Niemals `.env`, API-Keys, Datenbankdateien oder Passwörter in GitHub veröffentlichen.
- Verwende für den Owner ein starkes, einzigartiges Passwort.
- Aktiviere öffentliche Zahlungen erst nach korrekter rechtlicher und technischer Einrichtung.
- Das Projekt enthält keine E-Mail-Verifizierung und keinen Passwort-Reset. Deshalb ist es eine Beta-Grundlage und noch kein fertiger kommerzieller SaaS-Betrieb.

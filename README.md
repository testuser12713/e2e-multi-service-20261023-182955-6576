# Textanalyse-Aufträge – Auftragsverarbeitung mit API, Worker und Frontend

Ein kleines System zur Verarbeitung von Textanalyse-Aufträgen, bestehend aus drei unabhängig startbaren Diensten: Eine **FastAPI-API** nimmt Aufträge entgegen und speichert sie in einer SQLite-Datei, ein separater **Python-Worker** holt wartende Aufträge aus derselben Datenbank, analysiert den Text (Wörter zählen, häufigste Wörter, Lesezeit schätzen) und schreibt Ergebnis und Status zurück, und ein **Vite/React/TypeScript-Frontend** legt Aufträge an und zeigt die Auftragsliste mit Status und Ergebnis an, die sich alle drei Sekunden von selbst aktualisiert.

## Funktionen

- Aufträge über ein Formular oder per REST-API anlegen (Text bis 100.000 Zeichen, eine von drei Analysen)
- Validierung schon beim Request: leerer Text, reiner Leerraum, zu langer Text oder unbekannte Analyse werden mit 422 abgewiesen, ohne dass etwas gespeichert wird
- Hintergrundverarbeitung durch einen eigenen Worker-Prozess mit den Status `pending` → `running` → `done` bzw. `failed`
- Atomare Übernahme von Aufträgen: Auch mit mehreren Worker-Prozessen wird jeder Auftrag genau einmal verarbeitet
- Fehlerhafte Aufträge enden als `failed` mit einer kurzen, lesbaren Fehlermeldung; der Worker läuft weiter
- Auftragsliste im Browser mit Status-Badges (wartend, in Arbeit, fertig, fehlgeschlagen), Ergebnis bzw. Fehlermeldung, Leerzustand und sichtbarem Hinweis, wenn die API nicht erreichbar ist
- Automatische Aktualisierung der Liste alle 3 Sekunden ohne Neuladen der Seite
- Health-Endpunkt `GET /health`; die API legt das Datenbankschema beim Start selbst an
- Sicherheit und Datenschutz: nur parametrisierte SQL-Abfragen, CORS nur für ausdrücklich gelistete Origins ohne Credentials, keine Stacktraces oder Pfade in 5xx-Antworten, kein Job-Text in Logs, keine Drittanbieter-Ressourcen im Frontend

## Tech-Stack

| Dienst    | Technik                                                     |
|-----------|-------------------------------------------------------------|
| `api`     | Python 3, FastAPI, uvicorn, sqlite3 (Standardbibliothek), pytest + httpx |
| `worker`  | Python 3, sqlite3 (Standardbibliothek), pytest              |
| `web`     | Vite, React, TypeScript, Vitest + Testing Library           |
| Datenbank | Eine SQLite-Datei (WAL-Modus), gemeinsam genutzt über `DATABASE_PATH` |

## Projektstruktur

```
api/        FastAPI-Dienst (main.py, db.py, schemas.py, routers/jobs.py, tests/)
worker/     Worker-Prozess (main.py, db.py, analyses.py, claim.py, processor.py, tests/)
web/        Frontend (Vite + React + TypeScript, src/)
data/       SQLite-Datenbank jobs.db (wird beim Start angelegt, nicht versioniert)
dev.sh      Startet alle drei Dienste mit einem Befehl
RUN.json    Maschinenlesbare Startbeschreibung der Dienste
.env.example  Vorlage für die Konfiguration
```

## Voraussetzungen

- Python 3.13 (3.11 oder neuer)
- Node.js 20 oder neuer mit npm
- Bash (Linux, macOS oder Git Bash unter Windows) für `./dev.sh`

## Installation

```bash
git clone <repository-url>
cd <repository>
cp .env.example .env          # optional, alle Werte haben funktionierende Standardwerte
```

`./dev.sh` installiert alle Abhängigkeiten selbst (siehe unten). Wer die Dienste einzeln betreiben möchte, installiert sie so:

```bash
python3 -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r api/requirements.txt
pip install -r worker/requirements.txt
cd web && npm install
```

## Starten (Entwicklung)

### Alles mit einem Befehl

```bash
./dev.sh
```

Das Skript legt bei Bedarf die virtuelle Umgebung `.venv/` an, installiert die Abhängigkeiten von API, Worker und Frontend und startet anschließend alle drei Dienste gemeinsam:

- API: http://127.0.0.1:8000 (Health-Check: http://127.0.0.1:8000/health)
- Frontend: http://localhost:5173
- Worker: läuft im Hintergrund und verarbeitet wartende Aufträge

`Strg+C` beendet alle Dienste; beendet sich einer der Dienste, stoppt das Skript auch die anderen. Eine vorhandene `.env` im Projektverzeichnis wird eingelesen, die Ports lassen sich über `API_PORT` und `WEB_PORT` ändern.

### Dienste einzeln starten

Jeder Dienst läuft in seinem eigenen Verzeichnis. API und Worker müssen dieselbe Datenbankdatei verwenden; der relative Standardwert `../data/jobs.db` zeigt aus `api/` und aus `worker/` auf dieselbe Datei `data/jobs.db`.

**API** (im Verzeichnis `api/`):

```bash
cd api
export DATABASE_PATH=../data/jobs.db
export CORS_ORIGINS=http://localhost:5173
uvicorn main:app --port 8000
```

**Worker** (im Verzeichnis `worker/`, in einem zweiten Terminal):

```bash
cd worker
export DATABASE_PATH=../data/jobs.db
python main.py
```

Der Worker wartet beim Start, bis die API das Schema angelegt hat. Für parallele Verarbeitung können beliebig viele Worker-Prozesse gestartet werden.

**Frontend** (im Verzeichnis `web/`, in einem dritten Terminal):

```bash
cd web
export VITE_API_BASE_URL=http://127.0.0.1:8000
npm run dev
```

Danach http://localhost:5173 im Browser öffnen. Das Frontend muss über den Vite-Server (oder einen anderen HTTP-Server) ausgeliefert werden; das direkte Öffnen der Dateien per `file://` funktioniert nicht.

## Build für die Produktion

**Frontend:** Die API-Adresse wird beim Build fest eingebaut.

```bash
cd web
VITE_API_BASE_URL=https://api.example.org npm run build
```

Das Ergebnis liegt in `web/dist/` und besteht nur aus statischen Dateien, die jeder Webserver ausliefern kann; lokal lässt sich der Build mit `npx vite preview` ansehen.

**API und Worker** brauchen keinen Build. In der Produktion die API ohne Entwicklungsoptionen starten und `CORS_ORIGINS` auf den Origin des ausgelieferten Frontends setzen:

```bash
cd api
DATABASE_PATH=/var/lib/jobs/jobs.db CORS_ORIGINS=https://app.example.org \
  uvicorn main:app --host 0.0.0.0 --port 8000

cd worker
DATABASE_PATH=/var/lib/jobs/jobs.db python main.py
```

## Konfiguration

Alle Einstellungen kommen aus Umgebungsvariablen; keine davon ist geheim, alle haben funktionierende Standardwerte. Vorlage: `.env.example`.

| Variable               | Dienst        | Standardwert              | Bedeutung |
|------------------------|---------------|---------------------------|-----------|
| `DATABASE_PATH`        | api, worker   | `data/jobs.db` im Projektverzeichnis | Pfad der gemeinsamen SQLite-Datei. Relative Pfade gelten ab dem Verzeichnis des Dienstes, daher `../data/jobs.db`. Die API legt Verzeichnis und Schema beim Start an. |
| `CORS_ORIGINS`         | api           | `http://localhost:5173`   | Kommagetrennte Liste der erlaubten Origins. Nur explizite `http(s)`-Origins, `*` wird nie akzeptiert; Credentials werden nicht freigegeben. |
| `VITE_API_BASE_URL`    | web           | Adresse der lokalen API   | Basis-URL der API für das Frontend (beim Build fest eingebaut). |
| `WORKER_POLL_INTERVAL` | worker        | `1`                       | Sekunden, die der Worker wartet, wenn kein Auftrag ansteht. |
| `API_PORT`, `WEB_PORT` | `dev.sh`      | `8000`, `5173`            | Ports, auf denen `./dev.sh` API und Frontend startet. |

Beispiel für einen Start mit eigener Konfiguration:

```bash
DATABASE_PATH=../data/jobs.db CORS_ORIGINS=http://localhost:5173 ./dev.sh
```

## Bedienung der Oberfläche

Die Startseite `/` zeigt links (auf schmalen Bildschirmen oben) das Formular **Neuer Auftrag** und rechts bzw. darunter die Liste **Aufträge**.

1. Text in das Feld **Text** einfügen (Zeichenzähler bis 100.000).
2. Unter **Analyse** eine Auswertung wählen: *Wörter zählen*, *Häufigste Wörter* oder *Lesezeit schätzen*.
3. **Auftrag erstellen** klicken. Die Schaltfläche ist deaktiviert, solange das Textfeld leer ist oder gerade gesendet wird.

Der neue Auftrag erscheint sofort oben in der Liste mit dem Status *wartend*, wechselt zu *in Arbeit*, sobald der Worker ihn übernimmt, und zu *fertig* mit Ergebnis (bzw. *fehlgeschlagen* mit Fehlermeldung). Die Liste aktualisiert sich alle 3 Sekunden von selbst. Ohne Aufträge erscheint der Hinweis „Noch keine Aufträge“; ist die API nicht erreichbar, steht über der Liste ein Fehlerhinweis, und die zuletzt geladene Liste bleibt sichtbar.

## REST-API

Basis-URL lokal: `http://127.0.0.1:8000`. Alle Antworten sind JSON, es gibt keine Authentifizierung und kein Pfad-Präfix. Die interaktive OpenAPI-Dokumentation steht unter `/docs`.

### Datenmodell `Job`

```json
{
  "id": 1,
  "text": "eins zwei drei",
  "analysis": "word_count",
  "status": "done",
  "result": "3",
  "error": null,
  "created_at": "2026-10-23T12:00:00+00:00",
  "updated_at": "2026-10-23T12:00:01+00:00"
}
```

| Feld         | Typ            | Beschreibung |
|--------------|----------------|--------------|
| `id`         | int            | Fortlaufende Nummer |
| `text`       | string         | Der (getrimmte) Text |
| `analysis`   | string         | `word_count`, `top_words` oder `reading_time` |
| `status`     | string         | `pending`, `running`, `done` oder `failed` |
| `result`     | string \| null | Ergebnis, sobald `done` (Format siehe „Analysen“) |
| `error`      | string \| null | Kurze Fehlermeldung, wenn `failed` |
| `created_at` | string         | Zeitpunkt der Anlage, ISO 8601 in UTC |
| `updated_at` | string         | Zeitpunkt der letzten Änderung, ISO 8601 in UTC |

### `POST /jobs` – Auftrag anlegen

Body:

```json
{ "text": "eins zwei drei", "analysis": "word_count" }
```

- `text`: string, wird getrimmt, danach nicht leer und höchstens 100.000 Zeichen
- `analysis`: `"word_count"` | `"top_words"` | `"reading_time"`

Antwort `201 Created`:

```json
{
  "id": 1,
  "text": "eins zwei drei",
  "analysis": "word_count",
  "status": "pending",
  "result": null,
  "error": null,
  "created_at": "2026-10-23T12:00:00+00:00",
  "updated_at": "2026-10-23T12:00:00+00:00"
}
```

Ungültige Eingaben ergeben `422 Unprocessable Content` mit dem Validierungsfehler-Format von FastAPI; es wird nichts gespeichert:

```json
{
  "detail": [
    { "type": "string_too_short", "loc": ["body", "text"], "msg": "String should have at least 1 character" }
  ]
}
```

Beispiel mit `curl`:

```bash
curl -X POST http://127.0.0.1:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"text": "eins zwei drei", "analysis": "word_count"}'
```

### `GET /jobs` – alle Aufträge

Antwort `200 OK`: Liste von `Job`, neueste zuerst (absteigende `id`).

```json
[
  { "id": 2, "text": "Ein kurzer Text", "analysis": "reading_time", "status": "pending", "result": null, "error": null, "created_at": "2026-10-23T12:00:05+00:00", "updated_at": "2026-10-23T12:00:05+00:00" },
  { "id": 1, "text": "eins zwei drei", "analysis": "word_count", "status": "done", "result": "3", "error": null, "created_at": "2026-10-23T12:00:00+00:00", "updated_at": "2026-10-23T12:00:01+00:00" }
]
```

### `GET /jobs/{id}` – ein Auftrag

Antwort `200 OK`: ein `Job`. Eine unbekannte `id` ergibt `404 Not Found` mit einer kurzen Meldung in `detail`, zum Beispiel:

```json
{ "detail": "Job 42 not found" }
```

### `GET /health` – Health-Check

Antwort `200 OK`, sobald die Datenbank erreichbar ist:

```json
{ "status": "ok" }
```

### Fehlerantworten

Unerwartete Serverfehler antworten mit `500` und immer demselben Inhalt, ohne Stacktrace, Dateipfade oder Job-Text:

```json
{ "detail": "Internal Server Error" }
```

## Analysen

| Analyse        | Bezeichnung im Frontend | Ergebnis (`result`) |
|----------------|-------------------------|---------------------|
| `word_count`   | Wörter zählen           | Anzahl der Wörter als String, z. B. `"3"` für „eins zwei drei“ |
| `top_words`    | Häufigste Wörter        | JSON-String mit höchstens 5 Einträgen `[{"word": str, "count": int}]`, ohne Beachtung der Groß-/Kleinschreibung gezählt, bei gleicher Häufigkeit alphabetisch, z. B. `"[{\"word\": \"eins\", \"count\": 2}, {\"word\": \"zwei\", \"count\": 1}]"` |
| `reading_time` | Lesezeit schätzen       | Lesezeit in ganzen Minuten als String bei 200 Wörtern pro Minute, aufgerundet und mindestens `"1"` |

Ein Auftrag mit einer unbekannten Analyse endet als `failed` mit einer kurzen Fehlermeldung in `error`.

## Auftragsstatus

| Status    | Anzeige im Frontend | Bedeutung |
|-----------|---------------------|-----------|
| `pending` | wartend             | Angelegt, noch von keinem Worker übernommen |
| `running` | in Arbeit           | Ein Worker hat den Auftrag atomar übernommen und analysiert ihn |
| `done`    | fertig              | Analyse abgeschlossen, Ergebnis in `result` |
| `failed`  | fehlgeschlagen      | Analyse nicht möglich, Fehlermeldung in `error` |

## Tests

Jeder Dienst wird in seinem eigenen Verzeichnis getestet:

```bash
cd api && python -m pytest       # API: Endpunkte, Validierung, Schema, CORS, Fehlerbehandlung
cd worker && python -m pytest    # Worker: Analysen, atomare Übernahme, Statusübergänge
cd web && npm test               # Frontend (Vitest): Formular, Liste, Status-Badges, Aktualisierung
```

Die Python-Tests legen ihre SQLite-Datenbanken in temporären Verzeichnissen an und benötigen keine Vorbereitung. Codestil der Python-Dienste prüfen (im jeweiligen Verzeichnis):

```bash
ruff format --check . && ruff check .
```

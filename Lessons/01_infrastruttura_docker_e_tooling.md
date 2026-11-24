# Lezione 01 — Infrastruttura, Docker e Tooling (Tappa 1)

**Data**: 2026-11-24  
**Argomenti**: Architettura multi-container, Docker Compose, Multi-stage Dockerfile, `uv` vs `pip`, `Uvicorn`, `Vite`, `Nginx`.

> **Nota sul deploy**: la cartella `Lessons/` si trova nella root del repository ed è completamente esclusa dai build context Docker (`./backend` e `./frontend`), quindi **non viene mai inclusa nelle immagini né nei deploy di produzione**.

---

## 1. Visione d'insieme dell'Applicazione

Finance4Dummies è strutturata in **5 container indipendenti** collegati da una rete virtuale privata gestita da Docker Compose:

```text
  Browser (tuo PC)
     │
     ├──► http://localhost:5173  ──► [f4d-frontend]  (React + Vite in dev / Nginx in prod)
     │
     └──► http://localhost:8000  ──► [f4d-api]       (FastAPI + Uvicorn, API REST/SSE)
                                          │
                       ┌──────────────────┴──────────────────┐
                       ▼                                     ▼
               [f4d-postgres]                           [f4d-redis]
         (PostgreSQL 16 + TimescaleDB)           (Cache + Coda job + Pub/Sub)
                       ▲                                     ▲
                       └──────────────────┬──────────────────┘
                                          │
                                    [f4d-worker]     (ARQ: job asincroni e cron)
```

**Concetto chiave**: il codice React gira nel **browser**, non nel container `frontend`. Il container `frontend` consegna i file JS/CSS/HTML al browser; poi è il browser a effettuare le chiamate HTTP verso l'API (`:8000`). Il container `f4d-worker` invece non espone porte HTTP: resta collegato a Redis ed esegue job schedulati o asincroni in background.

---

## 2. Come Funziona [docker-compose.yml](../docker-compose.yml)

I 5 meccanismi principali configurati nel file:

1. **DNS interno di Docker**:
   - Dentro la rete Docker ogni servizio è raggiungibile usando il proprio nome (`postgres:5432`, `redis:6379`) al posto di `localhost` (che dentro un container indica il container stesso).
   - Nel mapping porte `"${REDIS_PORT:-6379}:6379"`, la parte a sinistra è la porta sull'host Windows (configurata a `6380` nel `.env` locale per evitare conflitti con un altro Redis), mentre la parte a destra resta `6379` nella rete privata Docker.
2. **`healthcheck` + `depends_on: condition: service_healthy`**:
   - Postgres viene verificato con `pg_isready`, Redis con `redis-cli ping`.
   - `api` e `worker` partono solo quando entrambi i servizi rispondono realmente pronti, evitando crash all'avvio.
3. **File di ambiente a cascata (`env_file`)**:
   - Si carica prima [`.env.example`](../.env.example) (`required: true`) e poi `.env` (`required: false`).
   - Il progetto parte subito con i default anche senza `.env`, mentre le variabili definite nel `.env` locale sovrascrivono selettivamente i default.
4. **Trucco dei doppi volumi (Bind Mount + Named Volume)**:
   - Backend: `./backend:/app` + `backend_venv:/app/.venv`
   - Frontend: `./frontend:/app` + `frontend_node_modules:/app/node_modules`
   - Il bind mount sincronizza in tempo reale il codice dal PC al container (abilitando hot-reload), mentre il named volume "protegge" le dipendenze Linux installate nel container impedendo al filesystem Windows di sovrascriverle.
5. **Persistenza dei dati**:
   - I volumi `postgres_data` e `redis_data` sopravvivono a `docker compose down` (si azzerano solo con `docker compose down -v`).
   - Redis è avviato con `--appendonly yes` (AOF) per non perdere le code di lavoro ARQ al riavvio.

---

## 3. Multi-Stage Build nei Dockerfile

### [backend/Dockerfile](../backend/Dockerfile) (`base` → `dev` / `prod`)
- **`base`**: parte da `python:3.13-slim`, copia il binario di `uv` da `ghcr.io/astral-sh/uv:0.6`, imposta `PYTHONUNBUFFERED=1` (log immediati) e `UV_LINK_MODE=copy` (stabile sui layer Docker). Copia prima solo `pyproject.toml` e `uv.lock*` per sfruttare la **cache dei layer Docker**: modificando un `.py`, le librerie non vengono riscaricate.
- **`dev`**: esegue `uv sync --no-install-project` (include `ruff`, `mypy`, `pytest`) e avvia Uvicorn con `--reload`.
- **`prod`**: esegue `uv sync --no-dev --no-install-project`, copia solo `app/` e `alembic/` e avvia Uvicorn senza `--reload`.

### [frontend/Dockerfile](../frontend/Dockerfile) (`base` → `dev` / `build` → `prod`)
- **`dev`**: avvia Vite dev server su `0.0.0.0:5173`.
- **`build`**: esegue `npm run build` generando i file statici ottimizzati in `/app/dist`.
- **`prod`**: scarta completamente Node.js e `node_modules`, parte da `nginx:1.27-alpine` e copia solo `/app/dist` servito tramite [nginx.conf](../frontend/nginx.conf).

---

## 4. Domande & Approfondimenti della Sessione

### Domanda: *Approfondiamo `uv` vs `pip`, `Nginx`, `Uvicorn` e `Vite` (tecnologie che non conosco).*

#### 4.1 `pip` vs `uv` — Package Manager Python
- **`pip` (tradizionale)**: richiede tool separati (`python -m venv`, attivazione manuale, `pip install -r requirements.txt`), è più lento nella risoluzione delle dipendenze e un semplice `requirements.txt` non congela automaticamente tutte le sotto-dipendenze con hash crittografici.
- **`uv` (moderno, scritto in Rust da Astral)**: unifica gestione ambienti virtuali, risoluzione dipendenze e lockfile deterministico con velocità 10–100x superiore.
- **Come lo usiamo nel progetto**:
  - [backend/pyproject.toml](../backend/pyproject.toml): dichiara le dipendenze di produzione (`[project].dependencies`) e quelle di sviluppo (`[dependency-groups].dev`).
  - [backend/uv.lock](../backend/uv.lock): congela versioni esatte e hash SHA-256 di ogni libreria e sotto-libreria per build 100% riproducibili.
  - Comandi chiave: `uv sync` (allinea `.venv` al lockfile), `uv run <cmd>` (esegue dentro `.venv` senza attivarlo), `uv add <pkg>` (installa e aggiorna `pyproject.toml` + `uv.lock`).

#### 4.2 `Uvicorn` — Server ASGI per FastAPI
- **FastAPI** è il framework applicativo (rotte, validazione Pydantic, logica); da solo non apre porte TCP né gestisce HTTP.
- **Uvicorn** è il server **ASGI** (*Asynchronous Server Gateway Interface*) che ascolta su `:8000`, riceve le richieste HTTP grezze, le passa a FastAPI (`app.main:app`) e restituisce le risposte HTTP.
- **ASGI vs WSGI**: a differenza del vecchio standard sincrono WSGI (dove una richiesta in attesa di DB blocca il worker), ASGI usa un **event loop asincrono (`asyncio`)** che gestisce molte richieste concorrenti mentre aspetta I/O (Postgres, Redis, API esterne) e supporta nativamente **SSE** e **WebSocket** (utili in Fase 3 per le quotazioni live).
- Comando in dev: `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` (`--host 0.0.0.0` rende il server raggiungibile fuori dal container; `--reload` riavvia al salvataggio solo in sviluppo).

#### 4.3 `Vite` — Dev Server e Build Tool per il Frontend
- Il browser non esegue direttamente TypeScript (`.tsx`), JSX né le direttive Tailwind CSS: capisce solo HTML, JavaScript standard e CSS.
- **In sviluppo (`npm run dev`)**: Vite serve su `:5173`, compila i file `.tsx` al volo su richiesta, offre **HMR (Hot Module Replacement)** per aggiornamenti istantanei senza perdere stato e include un `proxy` `/api` configurato in [frontend/vite.config.ts](../frontend/vite.config.ts).
- **In produzione (`npm run build`)**: compila, rimuove codice inutilizzato (*tree-shaking*) e minifica tutto in pochi file statici in `dist/` (`index.html`, `index-<hash>.js`, `index-<hash>.css`, dove l'hash abilita il *cache busting*). Dopo la build, Vite e Node.js non servono più a runtime.

#### 4.4 `Nginx` — Web Server Statico e Reverse Proxy
- Web server ad alte prestazioni scritto in C, leggerissimo in memoria.
- **Ruolo 1 (già configurato in [frontend/nginx.conf](../frontend/nginx.conf)) — Servire la SPA React in produzione**:
  - Consegna i file statici di `dist/` da `/usr/share/nginx/html`.
  - Attiva `gzip on;` per comprimere al volo JS/CSS/JSON (es. bundle JS da `272 KB` a `84 KB`).
  - Usa `try_files $uri $uri/ /index.html;`: se il browser chiede un file fisico (es. un `.js`) lo restituisce; se chiede una rotta logica React (es. `/accounts/mediolanum`) restituisce `index.html` evitando un `404 Not Found` e lasciando al router client-side il rendering della pagina.
- **Ruolo 2 (Fase 4 — Deploy Online) — Reverse Proxy**:
  - Davanti a tutto su HTTPS (`:443`), può smistare `/api/*` verso Uvicorn (`api:8000`) e tutto il resto verso i file statici React sotto un unico dominio (semplificando TLS, cookie `HttpOnly` e CORS).

---

## 5. Tabella Riassuntiva: Dev vs Produzione

| Ruolo | In Sviluppo (`docker-compose.yml`) | In Produzione (Deploy Online) |
| :--- | :--- | :--- |
| **Dipendenze Python** | `uv sync` (runtime + dev tools) | `uv sync --no-dev` (solo runtime, bloccato da `uv.lock`) |
| **Server Backend** | **Uvicorn** con `--reload` | **Uvicorn** senza `--reload` (dietro reverse proxy HTTPS) |
| **Frontend** | **Vite dev server** (compilazione al volo + HMR) | **Vite build** crea `dist/` → **Nginx** serve file statici (Node rimosso) |

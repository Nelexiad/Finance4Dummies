# Finance4Dummies — Comandi Utili

Guida rapida ai comandi principali per avviare, gestire, testare e fare debug dell'applicazione in locale (PowerShell / terminale dalla root del repository).

---

## 1. Avvio e Gestione Stack Docker

> **Prerequisito**: assicurati che esista il file `.env` nella root (copia di [`.env.example`](../.env.example), già configurato con `REDIS_PORT=6380` in locale).

```powershell
# Avvia tutto lo stack (log visibili nel terminale, Ctrl+C per fermare)
docker compose up

# Avvia in background (detached)
docker compose up -d

# Ricostruisce le immagini (utile dopo modifiche a Dockerfile, pyproject.toml o package.json)
docker compose up -d --build

# Stato dei container
docker compose ps

# Ferma e rimuove i container (i dati del DB nei volumi restano salvati)
docker compose down

# RESET COMPLETO: ferma tutto e cancella anche i volumi (PostgreSQL + Redis + venv/node_modules)
docker compose down -v
```

### Log dei Servizi

```powershell
# Log live di tutti i servizi
docker compose logs -f

# Log di un singolo servizio (api | worker | frontend | postgres | redis)
docker compose logs -f api
docker compose logs -f worker
docker compose logs --tail=50 postgres
```

### URL Locali

- **Frontend (React)**: `http://localhost:5173`
- **Backend Swagger UI**: `http://localhost:8000/api/v1/docs`
- **Backend ReDoc**: `http://localhost:8000/api/v1/redoc`
- **OpenAPI JSON**: `http://localhost:8000/api/v1/openapi.json`
- **Health (Liveness)**: `http://localhost:8000/api/v1/health`
- **Readiness (DB + Redis)**: `http://localhost:8000/api/v1/health/ready`

```powershell
# Verifica rapida da terminale
curl.exe -s http://localhost:8000/api/v1/health
curl.exe -s http://localhost:8000/api/v1/health/ready
```

---

## 2. Database (PostgreSQL / TimescaleDB) & Migrazioni Alembic

```powershell
# Applica tutte le migrazioni fino all'ultima versione
docker compose exec api uv run alembic upgrade head

# Controlla la revisione attuale del DB
docker compose exec api uv run alembic current

# Storico delle migrazioni
docker compose exec api uv run alembic history --verbose

# Genera una nuova migrazione dopo aver modificato i modelli SQLAlchemy
docker compose exec api uv run alembic revision --autogenerate -m "descrizione_modifica"

# Torna indietro di una migrazione
docker compose exec api uv run alembic downgrade -1
```

### Ispezione Diretta PostgreSQL (`psql`)

```powershell
# Apri la console interattiva psql dentro il container Postgres
docker compose exec postgres psql -U finance -d finance4dummies

# Lista tutte le tabelle create (one-shot)
docker compose exec postgres psql -U finance -d finance4dummies -c "\dt"

# Verifica le hypertable TimescaleDB attive
docker compose exec postgres psql -U finance -d finance4dummies -c "SELECT hypertable_name FROM timescaledb_information.hypertables;"
```

---

## 3. Redis & Worker ARQ

```powershell
# Ping veloce a Redis
docker compose exec redis redis-cli ping

# Apri redis-cli interattivo
docker compose exec redis redis-cli

# Controlla il worker ARQ
docker compose logs -f worker
```

---

## 4. Backend — Lint, Type-Checking, Test e Dipendenze

Tutti i comandi girano dentro il container `api` usando `uv`:

```powershell
# Linter Ruff (controllo)
docker compose exec api uv run ruff check .

# Linter Ruff con auto-fix (import e fix sicuri)
docker compose exec api uv run ruff check --fix .

# Formattazione codice Python
docker compose exec api uv run ruff format .

# Type-checking statico (mypy strict)
docker compose exec api uv run mypy app

# Esegui tutti i test Pytest
docker compose exec api uv run pytest -v

# Esegui un singolo file di test
docker compose exec api uv run pytest tests/test_foundation.py -v

# Aggiungi una nuova dipendenza Python (aggiorna pyproject.toml e uv.lock)
docker compose exec api uv add <nome-pacchetto>

# Aggiungi una dipendenza solo dev
docker compose exec api uv add --dev <nome-pacchetto>
```

---

## 5. Frontend — Dev, Lint, Test, Build e Tipi API

Puoi eseguirli direttamente in locale dentro `frontend/` (oppure prefissandoli con `docker compose exec frontend ...`):

```powershell
cd frontend

# Installa dipendenze
npm install

# Avvio dev server locale (alternativa al container frontend)
npm run dev

# Linter ESLint
npm run lint

# Type-checking TypeScript (app + vite.config)
npm run typecheck

# Test unitari Vitest
npm run test

# Build di produzione
npm run build

# Rigenera i tipi TypeScript dallo schema OpenAPI di FastAPI (richiede API attiva su :8000)
npm run gen:api
```

---

## 6. Checklist Rapida "Prima di un Commit"

```powershell
# Backend (con stack Docker attivo)
docker compose exec api uv run ruff check .
docker compose exec api uv run mypy app
docker compose exec api uv run pytest

# Frontend
cd frontend
npm run lint
npm run typecheck
npm run test
npm run build
```

# Sessione 01 — Riepilogo & Guida di Studio (Fase 0)

**Data**: 2026-11-23  
**Branch**: `dev`  
**Commit inclusi**:
- `c82ec39` — `feat(backend): scaffold Phase 0 FastAPI backend, domain models, and Docker setup`
- `d696e83` — `fix(backend): keep FK names within PostgreSQL 63-char limit and pass ruff/mypy`
- `be02385` — `feat(frontend): scaffold Phase 0 React TypeScript Vite app and update README`

Questo documento riassume **tutte le scelte architetturali e i file creati oggi**, pensato per essere studiato passo-passo nella prossima sessione.

---

## 1. Decisioni Architetturali Prese

1. **Lingua del progetto**: inglese ovunque (codice, tabelle DB, API, UI).
2. **Modello utenti**: **multi-utente** fin dal giorno 1 (`user_id` su tutte le entità di dominio utente), con flag `ALLOW_PUBLIC_REGISTRATION` per chiudere o aprire la registrazione quando l'app sarà online.
3. **Architettura backend**: **Modular Monolith** organizzato in 6 bounded context sotto [backend/app/modules/](../backend/app/modules):
   - `identity` (utenti e refresh token)
   - `accounts` (attori bancari e conti)
   - `cashflow` (categorie, movimenti, trasferimenti, regole ricorrenti e scadenze)
   - `portfolio` (strumenti finanziari, obbligazioni, ledger operazioni, piani PAC)
   - `market_data` (storico prezzi e tassi FX)
   - `analytics` (snapshot giornalieri del patrimonio)
4. **Precisione finanziaria**: mai `float` per il denaro. In Python si usa `Decimal`, su PostgreSQL `NUMERIC`:
   - Importi monetari: `NUMERIC(18, 2)`
   - Quantità/quote (anche frazionate): `NUMERIC(18, 8)`
   - Prezzi unitari: `NUMERIC(18, 6)`
   - Tassi FX: `NUMERIC(18, 8)`
5. **Database unico per relazionale + serie storiche**: **PostgreSQL 16 + TimescaleDB**. Le tabelle transazionali sfruttano vincoli ACID e FK; `market_prices`, `fx_rates` e `portfolio_daily_snapshots` sono **hypertable** partizionate per tempo.
6. **Chiavi primarie UUIDv7**: generate lato applicativo ([ids.py](../backend/app/core/ids.py)) così gli ID sono sia globalmente univoci sia ordinati cronologicamente (evitando frammentazione negli indici B-Tree di PostgreSQL).

---

## 2. Mappa dei File Creati (Cosa fa ogni file)

### A. Root & Infrastruttura Docker
| File | Ruolo e concetti chiave |
| :--- | :--- |
| [docker-compose.yml](../docker-compose.yml) | Orchestra i 5 servizi locali: `postgres` (TimescaleDB), `redis`, `api` (FastAPI con hot-reload), `worker` (ARQ), `frontend` (Vite dev server). Include `healthcheck` su Postgres e Redis così API e Worker partono solo quando i DB sono pronti. |
| [.env.example](../.env.example) | Template di tutte le variabili d'ambiente (JWT, porte, DB URL, Redis URL, CORS, `ALLOW_PUBLIC_REGISTRATION`). |
| [.gitignore](../.gitignore) | Esclude `.env`, `.venv/`, `node_modules/`, cache di pytest/ruff/mypy, build frontend. |
| [README.md](../README.md) | Guida rapida di avvio con Docker Compose e comandi di verifica qualità. |

### B. Backend Core (`backend/app/core/`)
| File | Ruolo e concetti chiave |
| :--- | :--- |
| [pyproject.toml](../backend/pyproject.toml) | Dipendenze gestite con `uv` (`fastapi`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `arq`, `redis`, `pyjwt`, `argon2-cffi`) e configurazione di `ruff`, `mypy --strict`, `pytest`. |
| [backend/Dockerfile](../backend/Dockerfile) | Dockerfile **multi-stage** (`base`, `dev`, `prod`) che usa `uv` e copia `uv.lock` per build deterministiche. |
| [config.py](../backend/app/core/config.py) | Gestione configurazione tipizzata con `pydantic-settings` + caching tramite `@lru_cache`. |
| [ids.py](../backend/app/core/ids.py) | Implementazione di `new_uuid7()` secondo RFC 9562 (48 bit timestamp ms + bit random). |
| [database.py](../backend/app/core/database.py) | Engine async SQLAlchemy 2.0, `AsyncSessionLocal`, `Base` dichiarativa con `NAMING_CONVENTION` deterministica per Alembic, tipi `Numeric` riutilizzabili e mixin `UUIDPrimaryKeyMixin` / `TimestampMixin`. |
| [redis.py](../backend/app/core/redis.py) | Client Redis asincrono singleton (`get_redis_client`, `close_redis_client`). |
| [security.py](../backend/app/core/security.py) | Hashing password con **Argon2id**, creazione/verifica **Access Token JWT**, generazione **Refresh Token** (in DB salviamo solo l'hash SHA-256, mai il token in chiaro). |
| [logging.py](../backend/app/core/logging.py) | Configurazione logging strutturato su `stdout` (standard per container Docker). |

### C. Modelli di Dominio (`backend/app/modules/`) — 17 Tabelle
| Modulo | File | Tabelle definite | Concetti di dominio principali |
| :--- | :--- | :--- | :--- |
| Identity | [identity/models.py](../backend/app/modules/identity/models.py) | `users`, `refresh_tokens` | Multi-tenancy su `user_id`, revoca e rotazione sessioni. |
| Accounts | [accounts/models.py](../backend/app/modules/accounts/models.py) | `institutions`, `accounts` | Separazione tra **attore bancario** (Mediolanum, Revolut, Trade Republic...) e i singoli **conti** (CC, deposito, conto titoli, wallet multi-valuta). |
| Cashflow | [cashflow/models.py](../backend/app/modules/cashflow/models.py) | `categories`, `cash_transactions`, `recurring_rules`, `recurring_occurrences` | Importi con segno garantiti da `CHECK` constraint DB; giroconti collegati via `transfer_group_id`; flag `is_extraordinary` per separare cashflow ordinario da 13ª, 14ª, premi e una tantum; `interval_count` per cadenze bimestrali; vincolo `UNIQUE(recurring_rule_id, scheduled_date)` per idempotenza worker. |
| Portfolio | [portfolio/models.py](../backend/app/modules/portfolio/models.py) | `instruments`, `instrument_provider_symbols`, `bond_details`, `portfolio_transactions`, `pac_plans`, `pac_executions` | Approccio **ISIN-first** con mapping separato verso ticker dei provider; estensione 1:1 `bond_details` per cedole/scadenza/tassazione; ledger `portfolio_transactions` da cui derivare posizioni, PMC e P&L; `linked_cash_transaction_id` opzionale per movimentare la liquidità; PAC schedulabili in modalità `AUTO_DRAFT` o `AUTO_EXECUTE`. |
| Market Data | [market_data/models.py](../backend/app/modules/market_data/models.py) | `market_prices`, `fx_rates` | Hypertable TimescaleDB partizionate su `recorded_at`. |
| Analytics | [analytics/models.py](../backend/app/modules/analytics/models.py) | `portfolio_daily_snapshots` | Hypertable TimescaleDB partizionata su `snapshot_date` per grafici storici istantanei. |
| Registry | [modules/__init__.py](../backend/app/modules/__init__.py) | *(re-export)* | Importa tutti i modelli così `Base.metadata` è sempre completo quando Alembic ispeziona lo schema. |

### D. API, Migrazioni, Worker & Test Backend
| File | Ruolo e concetti chiave |
| :--- | :--- |
| [main.py](../backend/app/main.py) | Factory `create_app()`, ciclo di vita `lifespan` (chiusura pulita Redis + DB engine), CORS middleware, router `/api/v1`. |
| [health.py](../backend/app/api/v1/health.py) | `GET /api/v1/health` (liveness) e `GET /api/v1/health/ready` (verifica reale `SELECT 1` su Postgres + `PING` su Redis, ritorna `503` se degradato). |
| [alembic/env.py](../backend/alembic/env.py) | Configurazione Alembic **asincrona** (`async_engine_from_config` + `connection.run_sync`). |
| [0001_initial_schema.py](../backend/alembic/versions/0001_initial_schema.py) | Prima migrazione completa: abilita `timescaledb`, crea tutte le 17 tabelle con indici/vincoli e converte le 3 serie storiche in hypertable con `create_hypertable(...)`. |
| [worker/settings.py](../backend/app/worker/settings.py) & [worker/tasks.py](../backend/app/worker/tasks.py) | Setup worker asincrono ARQ su Redis con cron schedulati placeholder per ricorrenze cashflow e piani PAC. |
| [test_foundation.py](../backend/tests/test_foundation.py) | Test base su `/api/v1/health`, UUIDv7, Argon2/JWT roundtrip e registrazione di tutte le 17 tabelle su `Base.metadata`. |

### E. Frontend (`frontend/`)
| File | Ruolo e concetti chiave |
| :--- | :--- |
| [package.json](../frontend/package.json) | React 19, TypeScript, Vite, Tailwind CSS v4, TanStack Query, `lucide-react`, `openapi-typescript`, ESLint, Vitest + React Testing Library. |
| [vite.config.ts](../frontend/vite.config.ts) | Configurazione Vite + plugin Tailwind v4 + proxy `/api` verso il backend + setup test `jsdom`. |
| [frontend/Dockerfile](../frontend/Dockerfile) & [nginx.conf](../frontend/nginx.conf) | Build multi-stage: target `dev` con hot-reload Vite e target `prod` con bundle statico servito da Nginx (fallback SPA su `/index.html`). |
| [client.ts](../frontend/src/api/client.ts) | Wrapper `fetchJson` tipizzato e chiamate `fetchHealth` / `fetchReadiness`. |
| [DashboardShell.tsx](../frontend/src/pages/DashboardShell.tsx) | Shell iniziale che interroga in live API, PostgreSQL e Redis tramite `useQuery` di TanStack Query e mostra i moduli della roadmap. |
| [App.test.tsx](../frontend/src/App.test.tsx) | Test di integrazione UI con mock di `fetch` che verifica il passaggio dei badge allo stato `Online`. |

---

## 3. Problemi Reali Emersi in Verifica e Come li Abbiamo Risolti

Ottimi spunti pratici da rivedere insieme nella prossima sessione:

1. **Limite 63 caratteri degli identificatori PostgreSQL**: due nomi di Foreign Key auto-generati (`70` e `65` caratteri) hanno fatto fallire `alembic upgrade head`. Risolto assegnando nomi espliciti compatti (`fk_portfolio_tx_linked_cash_tx` e `fk_pac_executions_portfolio_tx`) sia nei modelli ORM sia nella migrazione.
2. **Type-checking di `vite.config.ts` con `tsc -b`**: l'uso di `process.env` falliva perché `tsconfig.node.json` non includeva `@types/node`. Risolto in modo idiomatico Vite usando `loadEnv(mode, ".", "")` dentro `defineConfig(({ mode }) => ...)`.
3. **Strict `mypy` con `arq`**: il protocollo `WorkerCoroutine` di ARQ richiede che il primo argomento delle funzioni task si chiami esattamente `ctx` (e non `_ctx`). Sistemato mantenendo `mypy --strict` pulito senza `# type: ignore`.
4. **Ruff `RUF012` e import sorting**: aggiunte annotazioni `ClassVar` sugli attributi mutabili di classe (`Base.type_annotation_map`, `WorkerSettings.functions/cron_jobs`) e `known-first-party = ["app"]` in `pyproject.toml`.
5. **Porta Redis `6379` già occupata sull'host**: grazie alla parametrizzazione `${REDIS_PORT:-6379}:6379` in `docker-compose.yml`, è bastato impostare `REDIS_PORT=6380` per avviare lo stack senza toccare il codice.

---

## 4. Percorso Consigliato per Studiare Insieme la Prossima Volta

Quando riprenderemo nella prossima sessione, possiamo analizzare il codice seguendo questo ordine (dal basso verso l'alto):

1. **Infrastruttura**: [docker-compose.yml](../docker-compose.yml) + [backend/Dockerfile](../backend/Dockerfile) + [frontend/Dockerfile](../frontend/Dockerfile) — come dialogano i 5 container e perché usiamo multi-stage build.
2. **Core & Sicurezza**: [config.py](../backend/app/core/config.py), [database.py](../backend/app/core/database.py), [ids.py](../backend/app/core/ids.py), [security.py](../backend/app/core/security.py) — async SQLAlchemy, `Decimal`, UUIDv7, Argon2 + JWT.
3. **Modello Dati & Migrazioni**: [accounts/models.py](../backend/app/modules/accounts/models.py), [cashflow/models.py](../backend/app/modules/cashflow/models.py), [portfolio/models.py](../backend/app/modules/portfolio/models.py) e [0001_initial_schema.py](../backend/alembic/versions/0001_initial_schema.py) — vincoli DB, hypertable TimescaleDB, pattern ricorrenze e ledger.
4. **API, Worker & Frontend**: [main.py](../backend/app/main.py), [health.py](../backend/app/api/v1/health.py), [worker/settings.py](../backend/app/worker/settings.py), [client.ts](../frontend/src/api/client.ts) e [DashboardShell.tsx](../frontend/src/pages/DashboardShell.tsx) — ciclo richiesta/risposta, TanStack Query e strategia di test.

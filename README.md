# Finance4Dummies

Personal finance, banking-actor tracking, recurring cashflow, and investment portfolio (stocks, ETFs, bonds, PAC) web application built for both real-world use and software engineering study.

## Tech Stack

- **Backend**: Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), Alembic, ARQ worker, `uv`
- **Database**: PostgreSQL 16 + TimescaleDB (hypertables for market prices, FX rates, and daily portfolio snapshots)
- **Cache & Messaging**: Redis 7 (caching, ARQ queue, Pub/Sub for SSE real-time updates)
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4, TanStack Query, Vitest
- **Infrastructure**: Docker & Docker Compose

## Architecture (Modular Monolith)

```text
backend/app/modules/
├── identity/     # Multi-user auth (Argon2id + JWT + refresh token rotation)
├── accounts/     # Banking actors (institutions) & multi-currency accounts
├── cashflow/     # Income/expenses, transfers, recurring rules (salary, 13th/14th, bonuses, bills)
├── portfolio/    # ISIN-first instruments, bonds, ledger transactions, PAC plans
├── market_data/  # Market prices & FX rates (TimescaleDB hypertables)
└── analytics/    # Daily portfolio & net worth snapshots
```

## Quick Start (Docker Compose)

1. Copy the example environment file (optional — defaults work out of the box for local dev):

   ```bash
   cp .env.example .env
   ```

2. Build and start the full stack:

   ```bash
   docker compose up --build
   ```

3. Run database migrations:

   ```bash
   docker compose exec api uv run alembic upgrade head
   ```

4. Access the services:
   - **Frontend**: http://localhost:5173
   - **API Swagger Docs**: http://localhost:8000/api/v1/docs
   - **Health / Readiness**: http://localhost:8000/api/v1/health and http://localhost:8000/api/v1/health/ready

## Local Quality Checks

### Backend (inside Docker or with `uv`)

```bash
docker compose exec api uv run ruff check .
docker compose exec api uv run mypy app
docker compose exec api uv run pytest
```

### Frontend

```bash
cd frontend
npm run lint
npm run typecheck
npm run test
npm run build
```


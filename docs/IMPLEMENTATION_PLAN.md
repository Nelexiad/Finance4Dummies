# Finance4Dummies — Piano Implementativo

> **Come usare questo file**: aggiorna le checkbox (`[ ]` → `[x]`) e lo stato delle fasi man mano che completi le funzionalità. Ogni fase è pensata per essere sia un incremento usabile del tool sia un modulo di studio mirato.

## Stato Complessivo

| Fase | Obiettivo | Stato |
| :--- | :--- | :--- |
| **Fase 0** | Fondamenta, Monorepo, Docker, Schema DB & CI locale | Completata |
| **Fase 1** | Identity, Attori Bancari/Conti, Cashflow & Regole Ricorrenti | Da iniziare |
| **Fase 2** | Portfolio Ledger (Azioni, ETF, Obbligazioni) & Piani PAC | Da iniziare |
| **Fase 3** | Market Data (Free Tier), Worker Asincroni, Real-Time SSE & Grafici | Da iniziare |
| **Fase 4** | Analytics Avanzate, Hardening Sicurezza & Deploy Online | Da iniziare |

---

## Fase 0 — Fondamenta & Architettura (Completata)

- [x] Definizione stack tecnologico (`FastAPI` + `SQLAlchemy 2.0 async` + `PostgreSQL/TimescaleDB` + `Redis/ARQ` + `React 19 / TypeScript / Vite / Tailwind v4`)
- [x] Configurazione repository (`.gitignore`, `.env.example`, `docker-compose.yml`, branch `dev`)
- [x] Modello dati completo per tutti i 6 bounded context (17 tabelle + 3 hypertable TimescaleDB)
- [x] Setup Alembic async e prima migrazione `0001_initial_schema` applicata e verificata
- [x] Endpoint di liveness/readiness (`/api/v1/health`, `/api/v1/health/ready`)
- [x] Scheletro worker ARQ connesso a Redis con cron placeholder
- [x] Scheletro frontend React + TanStack Query + test Vitest + build Nginx prod
- [x] Verifica end-to-end locale (`ruff`, `mypy --strict`, `pytest`, `eslint`, `tsc -b`, `vitest`, `vite build`, `docker compose`)

---

## Fase 1 — Core Identity, Banche, Cashflow & Ricorrenze

**Obiettivo didattico**: autenticazione JWT/Argon2 con refresh rotation, separazione Router → Service → Repository (Clean/Hexagonal), calcoli monetari esatti con `Decimal`, gestione idempotente di scadenze ricorrenti.

### 1.1 Identity & Multi-User Auth (`backend/app/modules/identity`)
- [ ] Service di registrazione utente (controllato da `ALLOW_PUBLIC_REGISTRATION`) con seed automatico delle categorie di default (`Salary -> Base / 13th Month / 14th Month`, `Bonuses & Awards`, `One-Off Income`, `Housing`, `Utilities`, `Subscriptions`, ecc.)
- [ ] Login con verifica Argon2id, rilascio Access Token JWT + Refresh Token in cookie `HttpOnly`
- [ ] Endpoint `/api/v1/auth/refresh` con **token rotation** e revoca in caso di riuso
- [ ] Endpoint `/api/v1/auth/logout` e `/api/v1/auth/me`
- [ ] Dependency FastAPI `get_current_user` per isolare tutte le query su `user_id`
- [ ] Test automatici (registrazione, login, refresh, revoca, accesso non autorizzato)

### 1.2 Banking Actors & Accounts (`backend/app/modules/accounts`)
- [ ] Preset opzionali di attori bancari comuni (Mediolanum, MPS, UniCredit, Revolut, Trade Republic, Fineco, Directa, ecc.)
- [ ] CRUD `institutions` (con archiviazione logica `is_archived`)
- [ ] CRUD `accounts` collegati all'attore bancario (`CHECKING`, `SAVINGS`, `BROKERAGE`, `CASH_WALLET`, `DEPOSIT`, `CREDIT_CARD`)
- [ ] Calcolo saldo corrente per conto (`initial_balance + SUM(cash_transactions.amount)`) e saldo aggregato per attore bancario
- [ ] Test automatici di isolamento multi-utente e calcolo saldi

### 1.3 Cashflow & Trasferimenti (`backend/app/modules/cashflow`)
- [ ] CRUD `categories` (gerarchia padre/figlio per `INCOME` e `EXPENSE`)
- [ ] CRUD `cash_transactions` per:
  - [ ] Entrate e uscite ordinarie
  - [ ] Entrate/uscite **una tantum** e straordinarie (`is_extraordinary = true`: regali, rimborsi, premi spot, imprevisti)
  - [ ] **Trasferimenti tra conti** atomici (creazione coppia `TRANSFER_OUT` + `TRANSFER_IN` legati dallo stesso `transfer_group_id`, esclusi dai totali spese/entrate)
- [ ] Filtri e paginazione (per data, conto, attore bancario, categoria, tag, ordinario vs straordinario)
- [ ] Endpoint riepilogo cashflow mensile/annuale (distinguendo **Cashflow Ordinario** vs **Cashflow Totale**)

### 1.4 Regole Ricorrenti: Spese Fisse, Stipendio, 13ª, 14ª, Premi (`backend/app/modules/cashflow`)
- [ ] CRUD `recurring_rules` (`WEEKLY`, `BIWEEKLY`, `MONTHLY` + `interval_count` per bimestrali, `QUARTERLY`, `SEMI_ANNUAL`, `YEARLY` con `month_of_year` per 13ª/14ª/premi)
- [ ] Logica di calcolo `next_run_date` (gestione fine mese es. 31 → 28/29/30)
- [ ] Job ARQ `process_due_recurring_rules`:
  - [ ] Generazione idempotente di `recurring_occurrences` (`UNIQUE(recurring_rule_id, scheduled_date)`)
  - [ ] `AUTO_EXECUTE` → contabilizza subito `cash_transactions`
  - [ ] `AUTO_DRAFT` → lascia in stato `PENDING` per conferma importo reale (bollette variabili, premi, 13ª/14ª)
- [ ] Endpoint di conferma (`POST /recurring-occurrences/{id}/confirm` con importo effettivo modificabile) e skip (`skip`)
- [ ] Calendario scadenze future (prossimi 30/90 giorni)

### 1.5 Frontend Fase 1 (`frontend/`)
- [ ] Generazione automatica tipi TypeScript via `npm run gen:api` dallo schema OpenAPI di FastAPI
- [ ] Routing con TanStack Router e layout applicativo con sidebar + protezione rotte autenticate
- [ ] Pagine Login / Register
- [ ] Gestione Attori Bancari e Conti (card per banca con saldi)
- [ ] Registro Movimenti (filtri, form rapido entrata/uscita/una tantum/giroconto)
- [ ] Gestione Regole Ricorrenti & coda scadenze `PENDING` da confermare
- [ ] Dashboard Cashflow (entrate/uscite ordinarie vs straordinarie, saving rate)

---

## Fase 2 — Portfolio (Azioni, ETF, Obbligazioni) & Piani PAC

**Obiettivo didattico**: modello contabile a ledger (posizioni derivate dalle transazioni), calcolo **PMC (Prezzo Medio di Carico)**, P&L realizzato/non realizzato, matematica obbligazionaria, gestione piani PAC.

### 2.1 Anagrafica Strumenti & Obbligazioni (`backend/app/modules/portfolio`)
- [ ] CRUD `instruments` (ISIN-first: `STOCK`, `ETF`, `BOND`, `MUTUAL_FUND`, `ETC`)
- [ ] Gestione `instrument_provider_symbols` (mapping ISIN → ticker Yahoo/Finnhub/Twelve Data)
- [ ] Estensione `bond_details` per obbligazioni (emittente, cedola, frequenza, scadenza, convenzione giorni, tassazione `12.5%` vs `26%`)
- [ ] Servizio di calcolo obbligazionario in Python:
  - [ ] Calendario cedole future
  - [ ] Rateo maturato (accrued interest)
  - [ ] Rendimento lordo/netto a scadenza (**YTM**)

### 2.2 Ledger Portafoglio & Calcolo Posizioni
- [ ] CRUD `portfolio_transactions` (`BUY`, `SELL`, `DIVIDEND`, `COUPON`, `FEE`, `TAX`, `SPLIT`, `TRANSFER_IN`, `TRANSFER_OUT`)
- [ ] Opzione di regolamento automatico sul conto liquidità collegato (`linked_cash_transaction_id`)
- [ ] Motore di calcolo posizioni (per singolo conto titoli, per attore bancario, o consolidato globale):
  - [ ] Quantità detenuta (supporto quote frazionate a 8 decimali)
  - [ ] Prezzo Medio di Carico (**PMC** — Weighted Average Cost)
  - [ ] Costo investito, P&L realizzato, dividendi e cedole incassati
- [ ] Suite di unit test finanziari con scenari multi-acquisto, vendite parziali, commissioni, split e multi-valuta

### 2.3 Piani PAC (`pac_plans` & `pac_executions`)
- [ ] CRUD `pac_plans` collegati a conto titoli, conto liquidità opzionale e strumento
- [ ] Job ARQ `process_due_pac_plans` per creare le rate pianificate in modo idempotente
- [ ] Flusso di conferma rata PAC (`AUTO_DRAFT`: inserimento prezzo/quote effettive del broker → crea `portfolio_transaction` + eventuale `cash_transaction`)

### 2.4 Frontend Fase 2
- [ ] Vista Portfolio per Attore Bancario e vista Consolidata
- [ ] Tabella posizioni con Azioni, ETF e Obbligazioni (PMC, quantità, controvalore, peso %)
- [ ] Dettaglio singolo titolo (storico eseguiti, dividendi/cedole, dati bond e scadenze)
- [ ] Form registrazione operazioni (`BUY`/`SELL`/`DIVIDEND`/`COUPON`)
- [ ] Gestione Piani PAC e conferma rate in attesa

---

## Fase 3 — Dati di Mercato (Free Tier), Real-Time & Grafici

**Obiettivo didattico**: Ports & Adapters verso API esterne, fallback/circuit-breaker, caching Redis con TTL, Pub/Sub → Server-Sent Events (SSE), serie storiche con TimescaleDB.

### 3.1 Market Data Adapters (`backend/app/modules/market_data`)
- [ ] Interfaccia `MarketDataPort` (quotazione spot + storico OHLCV)
- [ ] Adapter `YahooFinanceAdapter` (azioni/ETF US + EU `.MI`/`.DE`) con rate-limiting e gestione errori
- [ ] Adapter `FinnhubAdapter` / `TwelveDataAdapter` (fallback opzionale con API key free tier)
- [ ] Adapter `FrankfurterFxAdapter` (tassi di cambio BCE gratuiti senza API key)
- [ ] Supporto inserimento/aggiornamento prezzo manuale per obbligazioni non coperte da API free
- [ ] Caching Redis (`quote:{instrument_id}`) + persistenza su hypertable `market_prices` e `fx_rates`

### 3.2 Worker & Real-Time Streaming
- [ ] Job ARQ periodico per refresh quotazioni degli strumenti effettivamente in portafoglio (durante gli orari di mercato)
- [ ] Pubblicazione aggiornamenti prezzo su Redis Pub/Sub
- [ ] Endpoint SSE FastAPI (`/api/v1/market-data/stream`) autenticato per spingere i prezzi live al browser
- [ ] Job ARQ notturno per popolare `portfolio_daily_snapshots` (storico patrimonio netto per conto e totale)

### 3.3 Frontend Fase 3
- [ ] Sottoscrizione SSE in React con aggiornamento live di prezzi, P&L non realizzato e variazione giornaliera
- [ ] Grafici storici prezzi titoli e andamento patrimonio con **TradingView Lightweight Charts**
- [ ] Grafici di allocazione (per asset class, per attore bancario, per valuta) e Cashflow nel tempo

---

## Fase 4 — Analytics Avanzate, Sicurezza & Deploy Online

**Obiettivo didattico**: metriche di rendimento finanziario (TWR/MWR), sicurezza applicativa in produzione, CI/CD e deploy containerizzato su VPS/cloud.

- [ ] Metriche avanzate di performance portafoglio (Time-Weighted Return, Money-Weighted Return / XIRR)
- [ ] Export/Import CSV (es. movimenti bancari e report portafoglio)
- [ ] Backup automatico cifrato di PostgreSQL
- [ ] Hardening sicurezza: rate limiting login/API, security headers, 2FA (TOTP) opzionale, audit log
- [ ] Pipeline CI con GitHub Actions (`ruff`, `mypy`, `pytest`, `eslint`, `tsc`, `vitest`, build Docker)
- [ ] Configurazione deploy produzione (`docker-compose.prod.yml` + reverse proxy Caddy/Traefik con HTTPS automatico)

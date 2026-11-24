# Lezione 02 — Core Backend, Sicurezza e SQLAlchemy (Tappa 2)

**Data**: 2026-11-24  
**Argomenti**: Configurazione tipizzata (`pydantic-settings`), UUIDv7, `Decimal`/`Numeric`, SQLAlchemy 2.0 Async, Argon2id + JWT + Refresh Token, Redis, Logging, confronto SQLAlchemy + Alembic vs Entity Framework Core.

---

## 1. Configurazione Tipizzata — [config.py](../backend/app/core/config.py)

Tutte le impostazioni applicative sono centralizzate in `Settings(BaseSettings)` tramite **`pydantic-settings`**:
- **Fail-fast all'avvio**: converte automaticamente le variabili d'ambiente nei tipi Python (`bool`, `int`, `Literal[...]`) e blocca l'avvio se mancano requisiti minimi (es. `jwt_secret_key` con `min_length=32`).
- **Precedenza**: variabili d'ambiente del container/sistema > `.env` > valori di default.
- **Normalizzazione**: `@field_validator` garantisce lo `/` iniziale su `api_v1_prefix`; `@property` trasforma `cors_origins` in lista.
- **Singleton con `@lru_cache(maxsize=1)`**: `get_settings()` legge e valida la configurazione una sola volta invece che a ogni richiesta HTTP.

---

## 2. Chiavi Primarie UUIDv7 — [ids.py](../backend/app/core/ids.py)

| Tipo di ID | Pro | Contro |
| :--- | :--- | :--- |
| **`INT` / `BIGSERIAL`** | Piccolo, B-Tree molto veloce | Espone sequenza e volumi negli URL (`/accounts/42`), generato solo dal DB |
| **`UUIDv4` (random)** | Imprevedibile, generabile lato app | Inserimenti sparsi nell'indice B-Tree di PostgreSQL → frammentazione (*page splits*) |
| **`UUIDv7` (RFC 9562)** | Imprevedibile, generabile lato app **e ordinato cronologicamente** | 16 byte invece di 8 |

In `new_uuid7()`:
- I **primi 48 bit** contengono il timestamp Unix in millisecondi → ogni nuovo ID è crescente (append-friendly per PostgreSQL).
- Seguono i bit di versione (`0x7`), variante RFC (`0b10`) e bit casuali crittografici generati via `secrets.randbits`.

---

## 3. Database Async & Precisione Finanziaria — [database.py](../backend/app/core/database.py)

1. **`NAMING_CONVENTION`**: assegna nomi deterministici a indici (`ix_`), unique (`uq_`), check (`ck_`), foreign key (`fk_`) e primary key (`pk_`), essenziali affinché Alembic possa modificare o rimuovere vincoli in futuro.
2. **Mai `float` per il denaro (`Decimal` + `Numeric`)**: i `float` binari introducono errori (`0.1 + 0.2 != 0.3`). Usiamo 6 tipi `Numeric(..., asdecimal=True)`:
   - `MoneyAmount` `(18, 2)` — importi monetari
   - `AssetQuantity` `(18, 8)` — quote frazionate (es. ETF / Trade Republic)
   - `UnitPrice` `(18, 6)` — prezzi unitari
   - `FxRateValue` `(18, 8)` — tassi di cambio
   - `CouponRateValue` `(8, 6)` e `TaxRateValue` `(5, 4)` — cedole e aliquote fiscali bond
3. **`Base` e Mixin**: `type_annotation_map` mappa `uuid.UUID → PG_UUID`, `datetime → TIMESTAMPTZ` (sempre UTC) e `Decimal → MoneyAmount`; `UUIDPrimaryKeyMixin` e `TimestampMixin` evitano duplicazione su tutte le 17 tabelle.
4. **Engine Async & `AsyncSessionLocal`**:
   - Driver `asyncpg` non bloccante per l'event loop ASGI di Uvicorn.
   - `pool_pre_ping=True`: verifica che la connessione presa dal pool sia viva prima di usarla.
   - `expire_on_commit=False`: evita che dopo `await session.commit()` la lettura degli attributi inneschi query lazy sincrone (che in async lanciano `MissingGreenlet`).
5. **Dependency Injection**: `get_db_session()` è un `AsyncGenerator` usato con `Depends(get_db_session)` in FastAPI — apre una sessione per ogni richiesta HTTP e la chiude automaticamente a fine richiesta.

---

## 4. Sicurezza: Argon2id, JWT e Refresh Token — [security.py](../backend/app/core/security.py)

1. **Password Hashing con Argon2id**:
   - Mai password in chiaro e mai SHA-256 (troppo veloce su GPU).
   - **Argon2id** è lento, *memory-hard* e genera automaticamente un **salt casuale** univoco per utente.
2. **Access Token JWT (stateless, 15 minuti)**:
   - Firmato con HMAC-SHA256 (`jwt_secret_key`), contiene `sub` (UUID utente), `iat`, `exp`, `type: "access"`.
   - **Attenzione**: il payload JWT **non è cifrato** (è Base64 leggibile), è solo **firmato** (non falsificabile) → non inserire mai segreti nel payload.
   - Verifica istantanea in RAM senza query al DB; durata breve perché non revocabile istantaneamente.
3. **Refresh Token (stateful, opaco, 30 giorni)**:
   - Generato con `secrets.token_urlsafe(48)` (384 bit di entropia).
   - Viaggerà in un cookie `HttpOnly` (invisibile a JavaScript → protezione XSS).
   - Nel DB (`refresh_tokens`) salviamo **solo il digest SHA-256**: sicuro perché l'entropia è altissima, protegge in caso di leak del DB e permette **revoca immediata** al logout o in caso di rotazione sospetta.

---

## 5. Redis & Logging — [redis.py](../backend/app/core/redis.py) e [logging.py](../backend/app/core/logging.py)

- **`redis.py`**: client asincrono lazy singleton con `decode_responses=True` (restituisce `str` invece di `bytes`) e `close_redis_client()` chiamato allo shutdown di FastAPI (`lifespan`).
- **`logging.py`**: log inviati su `sys.stdout` secondo il principio *12-Factor App* (in Docker i log non si scrivono su file nel container ma su stdout).

---

## 6. Domande & Approfondimenti della Sessione

### Domanda 1: *Parlami di SQLAlchemy*

- **Due strati**:
  - **SQLAlchemy Core**: gestisce Connection Pool (`Engine`) e query SQL parametrizzate sicure contro SQL Injection.
  - **SQLAlchemy ORM**: mappa classi Python (`Institution`, `Account`, ...) a tabelle SQL e istanze a righe.
  - Sotto SQLAlchemy gira il driver di rete **`asyncpg`**, che comunica in binario con PostgreSQL.
- **I 4 mattoni**:
  1. `Engine` → Connection Pool creato una volta sola all'avvio.
  2. `AsyncSession` → Unit of Work (carrello transazionale) per singola richiesta HTTP; salva atomicamente con `await session.commit()` o annulla con `rollback()`.
  3. `Base.metadata` → catalogo centrale di tutte le tabelle (popolato grazie a [modules/__init__.py](../backend/app/modules/__init__.py)).
  4. Modelli 2.0 (`Mapped[...]` + `mapped_column(...)` + `relationship(...)`) → unificano typing statico Python (`mypy`) e definizione colonne SQL; `relationship()` non crea colonne fisiche ma collega gli oggetti lato Python.
- **Query sicure 2.0**: si scrivono con `select(Model).where(...)` + `await session.execute(stmt)` → `result.scalars().all()` (parametrizzazione nativa, zero SQL Injection).
- **2 trappole tipiche in Async**:
  1. **No Lazy Loading implicito (`MissingGreenlet`)**: in async è vietato fare query nascoste accedendo a una relazione; si usa caricamento esplicito con `.options(selectinload(...))` (evitando anche il problema N+1).
  2. **`expire_on_commit=False`**: impedisce di invalidare gli attributi dopo il commit.
- **SQLAlchemy vs Alembic**: SQLAlchemy lavora sui **dati** a runtime (`SELECT/INSERT/UPDATE/DELETE`); Alembic versiona l'evoluzione dello **schema** nel tempo (`CREATE TABLE`, `ALTER TABLE`).

---

### Domanda 2: *SQLAlchemy e Alembic insieme sono come Entity Framework?*

**Sì, concettualmente svolgono lo stesso ruolo** di Entity Framework Core in .NET, diviso in due librerie gemelle dello stesso autore.

| Entity Framework Core (.NET) | SQLAlchemy 2.0 + Alembic (Python) |
| :--- | :--- |
| `DbContext` (scoped per richiesta) | `AsyncSession` via `Depends(get_db_session)` |
| `AddDbContext` + Connection Pool | `AsyncEngine` (`create_async_engine`) |
| Entità + Fluent API (`OnModelCreating`) | Classi che ereditano da `Base` (`Mapped`, `mapped_column`, `__table_args__`) |
| Navigation property (`ICollection<T>`) | `relationship(back_populates=...)` |
| LINQ (`ctx.Accounts.Where(...).ToListAsync()`) | `await session.execute(select(Account).where(...))` |
| `.Include(i => i.Accounts)` | `.options(selectinload(Institution.accounts))` |
| `ctx.Add(x)` + `SaveChangesAsync()` | `session.add(x)` + `await session.commit()` |
| `dotnet ef migrations add` | `uv run alembic revision --autogenerate -m "..."` |
| `dotnet ef database update` | `uv run alembic upgrade head` |
| Tabella `__EFMigrationsHistory` | Tabella `alembic_version` |
| `migrationBuilder.Sql("...")` | `op.execute("...")` |

**Le 3 differenze chiave da ricordare rispetto a EF Core**:
1. **Nessun `DbContext` monolitico con tutti i `DbSet<T>`**: `AsyncSession` è generica e funziona su qualsiasi modello registrato su `Base` (ideale per un Modular Monolith).
2. **Copre anche il ruolo di Dapper**: grazie a SQLAlchemy Core puoi scrivere query analitiche complesse, CTE, window functions e `UPSERT` di Postgres nella stessa libreria senza introdurre un secondo tool.
3. **Niente `ModelSnapshot.cs`**: Alembic confronta `Base.metadata` direttamente contro il DB di sviluppo live; i comandi speciali (come `create_hypertable` di TimescaleDB) si aggiungono/verificano esplicitamente nel file di migrazione.

---

### Domanda 3: *Approfondimento su Argon2 e JWT*

#### Argon2 (`argon2id`) — Perché e come protegge le password
- **Problema**: le password umane hanno poca entropia. Con hash veloci (MD5, SHA-256) una GPU prova miliardi di combinazioni al secondo, e senza *salt* le Rainbow Tables le craccano istantaneamente.
- **Come lavora `Argon2id`** ([security.py](../backend/app/core/security.py)):
  1. **One-way**: non è cifratura reversibile; al login si ricalcola l'hash e si confronta (`verify_password`).
  2. **Salt casuale automatico**: due utenti con la stessa password producono hash completamente diversi.
  3. **Memory-hard**: richiede decine di MB di RAM per ogni tentativo (`m=65536` = 64 MB), neutralizzando il parallelismo massivo delle GPU.
  4. **Formato auto-descrittivo salvato in DB**:
     ```text
     $argon2id$v=19$m=65536,t=3,p=4$<salt_base64>$<hash_base64>
     ```
     Include algoritmo (`argon2id`, ibrido resistente sia a GPU sia a side-channel), versione, parametri (`m` memoria, `t` iterazioni, `p` parallelismo), salt e hash. Se in futuro aumenti `m` o `t`, le vecchie password restano verificabili.

#### JWT (JSON Web Token) — Struttura e garanzie
Un JWT è una stringa `HEADER.PAYLOAD.SIGNATURE`:
- **Header** (Base64URL): es. `{"alg": "HS256", "typ": "JWT"}`.
- **Payload** (Base64URL): i *claims* creati in `create_access_token()` (`sub` = UUID utente, `iat`, `exp` = +15 min, `type = "access"`).
- **Signature**: `HMAC_SHA256(base64(header) + "." + base64(payload), JWT_SECRET_KEY)`.

**Regola fondamentale**: Header e Payload sono solo **codificati in Base64** (leggibili da chiunque), **NON cifrati**. La sicurezza è nella **firma**: qualsiasi modifica al payload invalida la firma e fa fallire `decode_access_token()`. Per questo nel payload non si mettono mai dati sensibili.
- **`HS256` (simmetrico)** vs **`RS256` (asimmetrico)**: usiamo `HS256` perché nel nostro Modular Monolith solo l'API emette e verifica i token; `RS256` serve in architetture a microservizi dove servizi terzi verificano con chiave pubblica senza possedere la chiave privata.

#### Ciclo completo: Argon2 + Access JWT + Refresh Token Rotation
1. **Login**: verifica password via **Argon2id** → emette **Access Token JWT** (15 min, tenuto in memoria lato frontend, mandato come `Authorization: Bearer <jwt>`) + **Refresh Token opaco** (30 giorni, cookie `HttpOnly; Secure; SameSite=Lax`, salvato in `refresh_tokens` solo come hash SHA-256).
2. **Chiamate API**: l'API valida la firma HMAC + scadenza del JWT in RAM (0 query di autenticazione al DB).
3. **Refresh con Rotation**: scaduto il JWT (15 min), il browser chiama `/api/v1/auth/refresh` inviando il cookie `HttpOnly`. Il backend verifica l'hash in DB, **revoca il vecchio refresh token** e ne rilascia una nuova coppia. Se un token già revocato viene riutilizzato (indice di furto), si possono revocare tutte le sessioni dell'utente.
4. **Logout**: revoca immediata del refresh token in DB (`revoked_at = now()`) e rimozione del cookie.


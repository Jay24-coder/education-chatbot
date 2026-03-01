# Application Startup Guide

Use this checklist when starting the Education Chatbot application. It covers infrastructure, database setup, and schema creation.

---

## 1. Prerequisites to consider

- **Environment**: Copy `.env.example` to `.env` and set at least:
  - `DATABASE_URL` or `POSTGRES_*` (host, port, db, user, password)
  - `REDIS_*` if using Redis (cache/queues)
  - `LLM_PROVIDER`, `LLM_API_KEY`, `MODEL_ID` for the LLM
- **Dependencies**: Install with `poetry install` (or your project’s package manager).

---

## 2. Start infrastructure (Docker)

From the project root:

```bash
docker compose up -d postgres redis
```

- **Postgres**: port `5434` (mapped from 5432). The database `education_chatbot` is created automatically on first run if defined in `docker-compose.yaml` (`POSTGRES_DB: education_chatbot`).
- **Redis**: port `6380` (mapped from 6379).

If the Postgres volume was created before `POSTGRES_DB=education_chatbot` was set, create the database manually:

```bash
docker compose exec postgres psql -U postgres -c "CREATE DATABASE education_chatbot;"
```

---

## 3. Create database tables

Connect to the `education_chatbot` database and run the schema below. Either:

- **One-shot from host** (requires `psql`):

  ```bash
  psql -h localhost -p 5434 -U postgres -d education_chatbot -f docs/schema.sql
  ```

- **Or** open a session and paste the SQL:

  ```bash
  docker compose exec postgres psql -U postgres -d education_chatbot
  ```

Then run the contents of `docs/schema.sql` (see next section).

---

## 4. Schema SQL

The application expects the tables defined in **`docs/schema.sql`** (conversations, messages, jobs). Create them once before starting the app by running that file as in step 3.

---

## 5. Quick reference

| Step | Action |
|------|--------|
| 1 | Configure `.env` (DB, Redis, LLM). |
| 2 | `docker compose up -d postgres redis` |
| 3 | Ensure DB `education_chatbot` exists (auto or manual `CREATE DATABASE`). |
| 4 | Run schema in `docs/schema.sql` against `education_chatbot`. |
| 5 | Start the application (e.g. `uvicorn` or your dev command). |

---

## 6. Useful commands

- **Shell inside Postgres container**:  
  `docker compose exec postgres bash`

- **psql into default DB**:  
  `docker compose exec postgres psql -U postgres`

- **psql into application DB**:  
  `docker compose exec postgres psql -U postgres -d education_chatbot`

- **Exit psql**:  
  `\q`

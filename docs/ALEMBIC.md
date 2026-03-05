# Alembic in this project

## What is Alembic?

Alembic is a **database migration tool** for SQLAlchemy. It keeps a linear history of schema changes (revisions) and lets you:

- **Upgrade** the database to a newer revision (apply migrations).
- **Downgrade** to an older revision (undo migrations).
- **Generate** new revisions from schema diffs or by hand.

Each revision is a Python file in `alembic/versions/` with `upgrade()` and `downgrade()` so changes are reversible.

## How we use it

- **Config**: The DB URL is taken from the same Postgres settings as the app (`app.config.db_redis`). Migrations use the **sync** driver (`psycopg2`) so you can run them from the CLI; the app keeps using `asyncpg`.
- **Revisions**:
  - `001_initial`: Creates `conversations`, `messages`, and `jobs` (current schema).
  - `002_updated_at`: Example upgrade that adds `updated_at` to `messages`.

## Commands (run from project root)

| Command | Purpose |
|--------|--------|
| `alembic current` | Show current revision in the database. |
| `alembic history` | List all revisions. |
| `alembic upgrade head` | Apply all migrations (bring DB to latest). |
| `alembic upgrade +1` | Apply the next one revision. |
| `alembic downgrade -1` | Undo one revision. |
| `alembic downgrade base` | Undo all (back to empty). |
| `alembic stamp head` | Mark DB as “at head” without running migrations (use when DB already matches schema). |

## If the database already exists

If you created the DB with `docs/schema.sql` and/or the old SQL migrations in `app/db/migrations/`, you have two options:

1. **Stamp and go forward**  
   Run once:  
   `alembic stamp head`  
   This tells Alembic “this DB is already at the latest revision.” Use this when the schema already matches and you only want Alembic for *future* changes.

2. **Start from empty and migrate**  
   Drop and recreate the DB, then run:  
   `alembic upgrade head`  
   This applies `001_initial` and `002_updated_at` from scratch.

## Creating a new migration (upgrading a table)

1. **Create a new revision file**  
   From project root:  
   `alembic revision -m "short_description"`  
   This creates `alembic/versions/<rev_id>_short_description.py`.

2. **Edit the new file**  
   - Set `down_revision` to the current head (e.g. `"002_updated_at"`).
   - In `upgrade()`: use `op.add_column()`, `op.create_table()`, `op.create_index()`, etc.
   - In `downgrade()`: reverse those (e.g. `op.drop_column()`, `op.drop_table()`).

3. **Apply it**  
   `alembic upgrade head`

**Reasoning**: One revision per logical change keeps history clear and makes downgrades predictable.

## Offline SQL (no DB connection)

To emit SQL without connecting:

`alembic upgrade head --sql > upgrade.sql`

Useful for applying migrations via a different tool or reviewing the script.

## Dependencies

- `alembic` – migration runner.
- `psycopg2-binary` – sync Postgres driver used only by Alembic when running migrations from the CLI.

The app continues to use `asyncpg` for normal queries.

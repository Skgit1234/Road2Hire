# Road2Hire PostgreSQL setup

The backend uses PostgreSQL. SQLAlchemy runtime connection configuration is read from `DATABASE_URL`. Alembic's online migration connection is read from `Backend/alembic.ini` (`sqlalchemy.url`), unless `ALEMBIC_TEST_URL` is explicitly set. Configure both to point at the same database when running the application and migrations.

## 1. Create a database

Create a PostgreSQL database using your local PostgreSQL role, for example:

```sql
CREATE DATABASE road2hire;
```

Alternatively, use PostgreSQL's `createdb road2hire` command. Choose database and role names according to your environment; do not commit credentials.

## 2. Configure environment and migration URL

Copy `Backend/.env.example` to `Backend/.env` and set the variables locally:

```dotenv
DATABASE_URL=postgresql+psycopg://<database-user>:<database-password>@localhost:5432/road2hire
SECRET_KEY=<locally-managed-secret>
```

`SECRET_KEY` is used by application authentication and is not a database credential. Do not put real secrets in documentation or commit them.

The current `Backend/alembic/env.py` does not read `DATABASE_URL` as its migration URL. Set the `sqlalchemy.url` entry in your local `Backend/alembic.ini` to the same PostgreSQL DSN, or use `ALEMBIC_TEST_URL` when intentionally using that environment override. Keep local credentials out of tracked files.

## 3. Apply migrations

From the repository root in PowerShell:

```powershell
cd Backend
.\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
```

From a POSIX shell:

```sh
cd Backend
python -m alembic -c alembic.ini upgrade head
```

Use the project's backend environment so the installed PostgreSQL driver and Alembic dependencies are available. Do not use `Database/schema.sql` as a migration mechanism; Alembic owns schema creation and upgrades.

## 4. Inspect the migration revision

From `Backend/`, display the revision recorded by the connected database:

```powershell
.\.venv\Scripts\python.exe -m alembic -c alembic.ini current
```

The current repository migration head is `a41c9e76bd20`. To inspect available revisions and the head without checking a database connection:

```powershell
.\.venv\Scripts\python.exe -m alembic -c alembic.ini heads
.\.venv\Scripts\python.exe -m alembic -c alembic.ini history --verbose
```

The database stores its applied revision in Alembic's `alembic_version` table. It can also be inspected with:

```sql
SELECT version_num FROM alembic_version;
```

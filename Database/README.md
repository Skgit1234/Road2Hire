# Road2Hire Database

This folder contains basic database documentation for Road2Hire.

## Database
Road2Hire uses PostgreSQL. Application models are maintained in `Backend/Models/`.

## Schema and migrations
- See [Database Schema](Design/Database_Schema.md) for a high-level overview of the database tables.
- Alembic migrations in `Backend/alembic/versions/` are the source of truth for creating and updating the schema.

## Important
Do not maintain duplicate table-creation scripts here. Update the SQLAlchemy models and create Alembic migrations when the application schema changes.

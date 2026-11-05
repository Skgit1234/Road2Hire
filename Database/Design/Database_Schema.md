# Road2Hire Database Schema

This document gives a high-level overview of the tables represented in the backend.

| Table | Purpose |
|---|---|
| `users` | Stores user account and authentication information. |
| `resumes` | Stores metadata for uploaded resumes. |
| `candidate_profiles` | Stores candidate information extracted from a resume, including skills and detected profile sections. |
| `skill_gaps` | Stores skill-gap analysis results. |
| `learning_tasks` | Stores learning tasks associated with a candidate's development. |

## Schema source

For exact column definitions, data types, primary keys, foreign keys, indexes, and constraints, refer to:

- SQLAlchemy models: `Backend/Models/`
- Alembic migrations: `Backend/alembic/versions/`

Update this document when a table is added, removed, or its purpose changes.

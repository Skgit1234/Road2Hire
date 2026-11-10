# Road2Hire entity-relationship diagram

The diagram shows the foreign-key cardinalities in the current database schema. `pipeline_runs` has both a user foreign key and an ownership-enforcing composite foreign key to `resumes`.

```mermaid
erDiagram
    USERS {
        int id PK
        varchar name
        varchar email UK
        varchar password_hash
    }
    RESUMES {
        int id PK
        int user_id FK
        varchar original_name
        varchar stored_name UK
        varchar file_path
        timestamptz uploaded_at
    }
    CANDIDATE_PROFILES {
        int id PK
        int user_id FK,UK
        int resume_id FK "nullable/optional"
        jsonb skills
        jsonb education
        jsonb experience
        jsonb projects
        jsonb certifications
        timestamptz updated_at
    }
    PIPELINE_RUNS {
        int id PK
        int user_id FK
        int resume_id FK "composite owner FK"
        varchar status
        jsonb canonical_output
        timestamptz created_at
        timestamptz completed_at
    }
    SKILL_GAPS {
        int id PK
        int pipeline_run_id FK,UK
        varchar target_occupation_uri
        varchar target_occupation_title
        float overall_skill_coverage_score
        float essential_skill_coverage_score
        float optional_skill_coverage_score
    }
    LEARNING_TASKS {
        int id PK
        int pipeline_run_id FK
        varchar logical_item_key
        varchar status
        int progress
        jsonb roadmap_item_data
    }
    JOBS {
        int id PK
        int user_id FK
        varchar title
        varchar target_occupation
        jsonb required_skills
        timestamptz created_at
    }

    USERS ||--o{ RESUMES : owns
    USERS ||--o| CANDIDATE_PROFILES : has_unique_user_profile
    RESUMES o|--o{ CANDIDATE_PROFILES : optional_resume_fk
    USERS ||--o{ PIPELINE_RUNS : owns
    RESUMES ||--o{ PIPELINE_RUNS : composite_user_resume_fk
    PIPELINE_RUNS ||--o| SKILL_GAPS : summarized_by
    PIPELINE_RUNS ||--o{ LEARNING_TASKS : has_roadmap_progress
    USERS ||--o{ JOBS : owns
```

## Relationship and deletion details

- `candidate_profiles.user_id` is unique, so each user can have at most one profile. `candidate_profiles.resume_id` is nullable and uses `ON DELETE SET NULL`; it is not unique and is not constrained together with `user_id`. Therefore the database does not guarantee that the profile's resume belongs to its user, nor that a resume is referenced by at most one profile. The ORM's scalar `Resume.candidate_profile` relationship is stronger than the database constraint.
- `pipeline_runs.resume_id` is mandatory. The composite `(user_id, resume_id)` foreign key references `resumes(user_id, id)` and uses `ON DELETE RESTRICT`, preventing both cross-user resume association and deletion of a resume with run history. The separate `pipeline_runs.user_id` foreign key points to `users.id` with `ON DELETE CASCADE`.
- `skill_gaps.pipeline_run_id` is unique and cascades on run deletion, giving a run zero or one summary.
- `learning_tasks` belongs to a run and cascades on run deletion. Its `(pipeline_run_id, logical_item_key)` unique constraint prevents duplicate roadmap-item rows within a run.
- User deletion cascades to the user's resumes, pipeline runs, and jobs; candidate profiles are removed through the user foreign key. Resume deletion cascades to no pipeline run: it is restricted when run history references it.

For full column definitions and indexes, see [schema.sql](./schema.sql).

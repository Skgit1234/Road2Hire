-- Road2Hire PostgreSQL reference schema.
-- Source: the current Alembic migration chain through head a41c9e76bd20.
-- This file documents application tables only; use Alembic for schema changes.

CREATE TABLE users (
    id SERIAL NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    CONSTRAINT users_pkey PRIMARY KEY (id),
    CONSTRAINT uq_users_email UNIQUE (email)
);

CREATE TABLE resumes (
    id SERIAL NOT NULL,
    user_id INTEGER NOT NULL,
    original_name VARCHAR(255) NOT NULL,
    stored_name VARCHAR(40) NOT NULL,
    file_path VARCHAR(1024) NOT NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT resumes_pkey PRIMARY KEY (id),
    CONSTRAINT uq_resumes_user_id_id UNIQUE (user_id, id),
    CONSTRAINT resumes_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT resumes_stored_name_key UNIQUE (stored_name)
);

CREATE TABLE candidate_profiles (
    id SERIAL NOT NULL,
    user_id INTEGER NOT NULL,
    resume_id INTEGER,
    skills JSONB NOT NULL,
    education JSONB NOT NULL,
    experience JSONB NOT NULL,
    projects JSONB NOT NULL,
    certifications JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT candidate_profiles_pkey PRIMARY KEY (id),
    CONSTRAINT uq_candidate_profiles_user_id UNIQUE (user_id),
    CONSTRAINT candidate_profiles_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT candidate_profiles_resume_id_fkey
        FOREIGN KEY (resume_id) REFERENCES resumes (id) ON DELETE SET NULL
);

CREATE INDEX ix_candidate_profiles_resume_id
    ON candidate_profiles (resume_id);

CREATE TABLE pipeline_runs (
    id SERIAL NOT NULL,
    user_id INTEGER NOT NULL,
    resume_id INTEGER NOT NULL,
    target_occupation_uri VARCHAR(512),
    target_occupation_title VARCHAR(255),
    selection_mode VARCHAR(20) DEFAULT 'explicit' NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    pipeline_version VARCHAR(30) DEFAULT '3.0.0' NOT NULL,
    schema_version VARCHAR(20) DEFAULT '1.0.0' NOT NULL,
    overall_skill_coverage_score FLOAT,
    essential_skill_coverage_score FLOAT,
    optional_skill_coverage_score FLOAT,
    readiness_class VARCHAR(50),
    is_ood BOOLEAN DEFAULT false NOT NULL,
    canonical_output JSONB DEFAULT '{}'::jsonb NOT NULL,
    error_code VARCHAR(100),
    error_stage VARCHAR(50),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pipeline_runs_pkey PRIMARY KEY (id),
    CONSTRAINT fk_pipeline_runs_resume_owner
        FOREIGN KEY (user_id, resume_id)
        REFERENCES resumes (user_id, id) ON DELETE RESTRICT,
    CONSTRAINT pipeline_runs_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT ck_pipeline_runs_status
        CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    CONSTRAINT ck_pipeline_runs_selection_mode
        CHECK (selection_mode IN ('explicit', 'auto_selected')),
    CONSTRAINT ck_pipeline_runs_overall_score_range
        CHECK (
            overall_skill_coverage_score IS NULL
            OR (overall_skill_coverage_score >= 0.0
                AND overall_skill_coverage_score <= 1.0)
        ),
    CONSTRAINT ck_pipeline_runs_essential_score_range
        CHECK (
            essential_skill_coverage_score IS NULL
            OR (essential_skill_coverage_score >= 0.0
                AND essential_skill_coverage_score <= 1.0)
        ),
    CONSTRAINT ck_pipeline_runs_optional_score_range
        CHECK (
            optional_skill_coverage_score IS NULL
            OR (optional_skill_coverage_score >= 0.0
                AND optional_skill_coverage_score <= 1.0)
        )
);

CREATE INDEX ix_pipeline_runs_completed_at
    ON pipeline_runs (completed_at);
CREATE INDEX ix_pipeline_runs_resume
    ON pipeline_runs (resume_id);
CREATE INDEX ix_pipeline_runs_status
    ON pipeline_runs (status);
CREATE INDEX ix_pipeline_runs_target_occupation_uri
    ON pipeline_runs (target_occupation_uri);
CREATE INDEX ix_pipeline_runs_user_created
    ON pipeline_runs (user_id, created_at);

CREATE TABLE skill_gaps (
    id SERIAL NOT NULL,
    pipeline_run_id INTEGER NOT NULL,
    target_occupation_uri VARCHAR(512) NOT NULL,
    target_occupation_title VARCHAR(255) NOT NULL,
    overall_skill_coverage_score FLOAT NOT NULL,
    essential_skill_coverage_score FLOAT NOT NULL,
    optional_skill_coverage_score FLOAT NOT NULL,
    matched_skill_count INTEGER DEFAULT 0 NOT NULL,
    missing_essential_skill_count INTEGER DEFAULT 0 NOT NULL,
    missing_optional_skill_count INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT skill_gaps_pkey PRIMARY KEY (id),
    CONSTRAINT ck_skill_gaps_overall_score_range
        CHECK (overall_skill_coverage_score >= 0.0
            AND overall_skill_coverage_score <= 1.0),
    CONSTRAINT ck_skill_gaps_essential_score_range
        CHECK (essential_skill_coverage_score >= 0.0
            AND essential_skill_coverage_score <= 1.0),
    CONSTRAINT ck_skill_gaps_optional_score_range
        CHECK (optional_skill_coverage_score >= 0.0
            AND optional_skill_coverage_score <= 1.0),
    CONSTRAINT ck_skill_gaps_matched_skill_count_non_negative
        CHECK (matched_skill_count >= 0),
    CONSTRAINT ck_skill_gaps_missing_essential_count_non_negative
        CHECK (missing_essential_skill_count >= 0),
    CONSTRAINT ck_skill_gaps_missing_optional_count_non_negative
        CHECK (missing_optional_skill_count >= 0),
    CONSTRAINT uq_skill_gaps_pipeline_run_id UNIQUE (pipeline_run_id),
    CONSTRAINT skill_gaps_pipeline_run_id_fkey
        FOREIGN KEY (pipeline_run_id)
        REFERENCES pipeline_runs (id) ON DELETE CASCADE
);

CREATE INDEX ix_skill_gaps_target_occupation_uri
    ON skill_gaps (target_occupation_uri);

CREATE TABLE learning_tasks (
    id SERIAL NOT NULL,
    pipeline_run_id INTEGER NOT NULL,
    logical_item_key VARCHAR(255) NOT NULL,
    roadmap_phase_number INTEGER NOT NULL,
    roadmap_phase_name VARCHAR(120),
    skill_name VARCHAR(255) NOT NULL,
    skill_uri VARCHAR(512),
    priority VARCHAR(20),
    status VARCHAR(20) DEFAULT 'not_started' NOT NULL,
    progress INTEGER DEFAULT 0 NOT NULL,
    roadmap_item_data JSONB DEFAULT '{}'::jsonb NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT learning_tasks_pkey PRIMARY KEY (id),
    CONSTRAINT ck_learning_tasks_status
        CHECK (status IN ('not_started', 'in_progress', 'completed')),
    CONSTRAINT ck_learning_tasks_progress
        CHECK (progress >= 0 AND progress <= 100),
    CONSTRAINT ck_learning_tasks_roadmap_phase_number
        CHECK (roadmap_phase_number >= 1 AND roadmap_phase_number <= 4),
    CONSTRAINT uq_learning_task_pipeline_run_logical_item
        UNIQUE (pipeline_run_id, logical_item_key),
    CONSTRAINT learning_tasks_pipeline_run_id_fkey
        FOREIGN KEY (pipeline_run_id)
        REFERENCES pipeline_runs (id) ON DELETE CASCADE
);

CREATE INDEX ix_learning_tasks_skill_name
    ON learning_tasks (skill_name);
CREATE INDEX ix_learning_tasks_status
    ON learning_tasks (status);

CREATE TABLE jobs (
    id SERIAL NOT NULL,
    user_id INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    target_occupation VARCHAR(512) NOT NULL,
    required_skills JSONB DEFAULT '[]'::jsonb NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT jobs_pkey PRIMARY KEY (id),
    CONSTRAINT jobs_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_jobs_user_created
    ON jobs (user_id, created_at);

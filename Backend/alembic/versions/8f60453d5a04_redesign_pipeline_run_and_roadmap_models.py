
"""redesign pipeline run and roadmap models

Revision ID: 8f60453d5a04
Revises: f1a2b3c4d5e6
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "8f60453d5a04"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Preserve the existing tables and their records.
    # PostgreSQL updates the existing foreign-key reference when a table is renamed.
    op.rename_table("skill_gaps", "legacy_skill_gaps")
    op.rename_table("learning_tasks", "legacy_learning_tasks")

    # Free primary-key index and sequence names for the redesigned tables.
    op.execute("ALTER INDEX skill_gaps_pkey RENAME TO legacy_skill_gaps_pkey")
    op.execute("ALTER INDEX learning_tasks_pkey RENAME TO legacy_learning_tasks_pkey")
    op.execute("ALTER SEQUENCE skill_gaps_id_seq RENAME TO legacy_skill_gaps_id_seq")
    op.execute("ALTER SEQUENCE learning_tasks_id_seq RENAME TO legacy_learning_tasks_id_seq")

    # 2. Remove redundant resume indexes.
    op.drop_index("ix_resumes_id", table_name="resumes")
    op.drop_index("ix_resumes_user_id", table_name="resumes")

    # 3. Add composite uniqueness before pipeline_runs references it.
    op.create_unique_constraint(
        "uq_resumes_user_id_id",
        "resumes",
        ["user_id", "id"],
    )

    # 4. Create pipeline_runs.
    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("target_occupation_uri", sa.String(512), nullable=True),
        sa.Column("target_occupation_title", sa.String(255), nullable=True),
        sa.Column(
            "selection_mode",
            sa.String(20),
            server_default="explicit",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(20),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "pipeline_version",
            sa.String(30),
            server_default="3.0.0",
            nullable=False,
        ),
        sa.Column(
            "schema_version",
            sa.String(20),
            server_default="1.0.0",
            nullable=False,
        ),
        sa.Column("overall_skill_coverage_score", sa.Float(), nullable=True),
        sa.Column("essential_skill_coverage_score", sa.Float(), nullable=True),
        sa.Column("optional_skill_coverage_score", sa.Float(), nullable=True),
        sa.Column("readiness_class", sa.String(50), nullable=True),
        sa.Column(
            "is_ood",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "canonical_output",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_stage", sa.String(50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),

        sa.CheckConstraint(
            "selection_mode IN ('explicit', 'auto_selected')",
            name="ck_pipeline_runs_selection_mode",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_pipeline_runs_status",
        ),
        sa.CheckConstraint(
            "overall_skill_coverage_score IS NULL OR "
            "(overall_skill_coverage_score >= 0.0 "
            "AND overall_skill_coverage_score <= 1.0)",
            name="ck_pipeline_runs_overall_score_range",
        ),
        sa.CheckConstraint(
            "essential_skill_coverage_score IS NULL OR "
            "(essential_skill_coverage_score >= 0.0 "
            "AND essential_skill_coverage_score <= 1.0)",
            name="ck_pipeline_runs_essential_score_range",
        ),
        sa.CheckConstraint(
            "optional_skill_coverage_score IS NULL OR "
            "(optional_skill_coverage_score >= 0.0 "
            "AND optional_skill_coverage_score <= 1.0)",
            name="ck_pipeline_runs_optional_score_range",
        ),
        sa.ForeignKeyConstraint(
            ["user_id", "resume_id"],
            ["resumes.user_id", "resumes.id"],
            name="fk_pipeline_runs_resume_owner",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 5. Pipeline run indexes.
    op.create_index(
        "ix_pipeline_runs_completed_at",
        "pipeline_runs",
        ["completed_at"],
    )
    op.create_index(
        "ix_pipeline_runs_resume",
        "pipeline_runs",
        ["resume_id"],
    )
    op.create_index(
        "ix_pipeline_runs_status",
        "pipeline_runs",
        ["status"],
    )
    op.create_index(
        "ix_pipeline_runs_target_occupation_uri",
        "pipeline_runs",
        ["target_occupation_uri"],
    )
    op.create_index(
        "ix_pipeline_runs_user_created",
        "pipeline_runs",
        ["user_id", "created_at"],
    )

    # 6. Convert candidate profile JSON columns to JSONB.
    for column in (
        "skills",
        "education",
        "experience",
        "projects",
        "certifications",
    ):
        op.alter_column(
            "candidate_profiles",
            column,
            existing_type=postgresql.JSON(),
            type_=postgresql.JSONB(),
            existing_nullable=False,
            postgresql_using=f"{column}::jsonb",
        )

    # Remove obsolete candidate profile indexes.
    op.drop_index(
        "ix_candidate_profiles_id",
        table_name="candidate_profiles",
    )
    op.drop_index(
        "ix_candidate_profiles_user_id",
        table_name="candidate_profiles",
    )


    # Retain resume lookup index.
    op.create_index(
        "ix_candidate_profiles_resume_id",
        "candidate_profiles",
        ["resume_id"],
    )

    # 7. Create redesigned skill_gaps table.
    op.create_table(
        "skill_gaps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pipeline_run_id", sa.Integer(), nullable=False),
        sa.Column("target_occupation_uri", sa.String(512), nullable=False),
        sa.Column("target_occupation_title", sa.String(255), nullable=False),
        sa.Column("overall_skill_coverage_score", sa.Float(), nullable=False),
        sa.Column("essential_skill_coverage_score", sa.Float(), nullable=False),
        sa.Column("optional_skill_coverage_score", sa.Float(), nullable=False),
        sa.Column(
            "matched_skill_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "missing_essential_skill_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "missing_optional_skill_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        sa.CheckConstraint(
            "overall_skill_coverage_score >= 0.0 "
            "AND overall_skill_coverage_score <= 1.0",
            name="ck_skill_gaps_overall_score_range",
        ),
        sa.CheckConstraint(
            "essential_skill_coverage_score >= 0.0 "
            "AND essential_skill_coverage_score <= 1.0",
            name="ck_skill_gaps_essential_score_range",
        ),
        sa.CheckConstraint(
            "optional_skill_coverage_score >= 0.0 "
            "AND optional_skill_coverage_score <= 1.0",
            name="ck_skill_gaps_optional_score_range",
        ),
        sa.CheckConstraint(
            "matched_skill_count >= 0",
            name="ck_skill_gaps_matched_skill_count_non_negative",
        ),
        sa.CheckConstraint(
            "missing_essential_skill_count >= 0",
            name="ck_skill_gaps_missing_essential_count_non_negative",
        ),
        sa.CheckConstraint(
            "missing_optional_skill_count >= 0",
            name="ck_skill_gaps_missing_optional_count_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "pipeline_run_id",
            name="uq_skill_gaps_pipeline_run_id",
        ),
    )

    op.create_index(
        "ix_skill_gaps_target_occupation_uri",
        "skill_gaps",
        ["target_occupation_uri"],
    )

    # 8. Create redesigned learning_tasks table.
    op.create_table(
        "learning_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pipeline_run_id", sa.Integer(), nullable=False),
        sa.Column("logical_item_key", sa.String(255), nullable=False),
        sa.Column("roadmap_phase_number", sa.Integer(), nullable=False),
        sa.Column("roadmap_phase_name", sa.String(120), nullable=True),
        sa.Column("skill_name", sa.String(255), nullable=False),
        sa.Column("skill_uri", sa.String(512), nullable=True),
        sa.Column("priority", sa.String(20), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            server_default="not_started",
            nullable=False,
        ),
        sa.Column(
            "progress",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "roadmap_item_data",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        sa.CheckConstraint(
            "status IN ('not_started', 'in_progress', 'completed')",
            name="ck_learning_tasks_status",
        ),
        sa.CheckConstraint(
            "progress >= 0 AND progress <= 100",
            name="ck_learning_tasks_progress",
        ),
        sa.CheckConstraint(
            "roadmap_phase_number >= 1 AND roadmap_phase_number <= 4",
            name="ck_learning_tasks_roadmap_phase_number",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "pipeline_run_id",
            "logical_item_key",
            name="uq_learning_task_pipeline_run_logical_item",
        ),
    )

    op.create_index(
        "ix_learning_tasks_skill_name",
        "learning_tasks",
        ["skill_name"],
    )
    op.create_index(
        "ix_learning_tasks_status",
        "learning_tasks",
        ["status"],
    )

    # 9. Remove obsolete user indexes and enforce email uniqueness.
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")

    op.create_unique_constraint(
        "uq_users_email",
        "users",
        ["email"],
    )


def downgrade() -> None:
    # 1. Drop new tables in reverse dependency order.
    op.drop_table("learning_tasks")
    op.drop_table("skill_gaps")
    op.drop_table("pipeline_runs")

    # 2. Restore previous user email index.
    op.drop_constraint(
        "uq_users_email",
        "users",
        type_="unique",
    )
    op.create_index(
        "ix_users_email",
        "users",
        ["email"],
        unique=True,
    )
    op.create_index(
        "ix_users_id",
        "users",
        ["id"],
        unique=False,
    )

    # 3. Restore old candidate profile indexes and JSON types.
    op.drop_index(
        "ix_candidate_profiles_resume_id",
        table_name="candidate_profiles",
    )
    op.create_index(
        "ix_candidate_profiles_user_id",
        "candidate_profiles",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_candidate_profiles_id",
        "candidate_profiles",
        ["id"],
        unique=False,
    )

    for column in (
        "certifications",
        "projects",
        "experience",
        "education",
        "skills",
    ):
        op.alter_column(
            "candidate_profiles",
            column,
            existing_type=postgresql.JSONB(),
            type_=postgresql.JSON(),
            existing_nullable=False,
            postgresql_using=f"{column}::json",
        )

    # 4. Remove resume composite uniqueness and restore old indexes.
    op.drop_constraint(
        "uq_resumes_user_id_id",
        "resumes",
        type_="unique",
    )
    op.create_index(
        "ix_resumes_user_id",
        "resumes",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_resumes_id",
        "resumes",
        ["id"],
        unique=False,
    )

    # 5. Restore the preserved legacy tables and their original names.
    op.rename_table("legacy_skill_gaps", "skill_gaps")
    op.rename_table("legacy_learning_tasks", "learning_tasks")

    # Restore original primary-key index and sequence names.
    op.execute("ALTER INDEX legacy_skill_gaps_pkey RENAME TO skill_gaps_pkey")
    op.execute("ALTER INDEX legacy_learning_tasks_pkey RENAME TO learning_tasks_pkey")
    op.execute("ALTER SEQUENCE legacy_skill_gaps_id_seq RENAME TO skill_gaps_id_seq")
    op.execute("ALTER SEQUENCE legacy_learning_tasks_id_seq RENAME TO learning_tasks_id_seq")
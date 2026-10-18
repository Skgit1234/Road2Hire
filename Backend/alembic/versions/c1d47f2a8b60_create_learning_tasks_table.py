"""create learning tasks table

Revision ID: c1d47f2a8b60
Revises: e629ccef0ddf
Create Date: 2026-10-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1d47f2a8b60"
down_revision: Union[str, Sequence[str], None] = "e629ccef0ddf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "learning_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("skill_gap_id", sa.Integer(), nullable=False),
        sa.Column("skill_name", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
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
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
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
        sa.ForeignKeyConstraint(
            ["skill_gap_id"],
            ["skill_gaps.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "skill_gap_id",
            "skill_name",
            name="uq_learning_task_skill",
        ),
    )
    op.create_index(
        op.f("ix_learning_tasks_id"),
        "learning_tasks",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_learning_tasks_user_id"),
        "learning_tasks",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_learning_tasks_skill_gap_id"),
        "learning_tasks",
        ["skill_gap_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_learning_tasks_skill_gap_id"), table_name="learning_tasks")
    op.drop_index(op.f("ix_learning_tasks_user_id"), table_name="learning_tasks")
    op.drop_index(op.f("ix_learning_tasks_id"), table_name="learning_tasks")
    op.drop_table("learning_tasks")

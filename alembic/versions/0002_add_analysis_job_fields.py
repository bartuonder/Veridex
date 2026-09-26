"""add job tracking fields to analysis_results"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_analysis_job_fields"
down_revision: Union[str, Sequence[str], None] = "0001_create_core_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("analysis_results", sa.Column("job_id", sa.String(length=64), nullable=True))
    op.add_column(
        "analysis_results",
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
    )
    op.add_column("analysis_results", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column("analysis_results", sa.Column("result_payload", sa.Text(), nullable=True))
    op.create_index(op.f("ix_analysis_results_job_id"), "analysis_results", ["job_id"], unique=True)
    op.alter_column("analysis_results", "job_id", existing_type=sa.String(length=64), nullable=False)


def downgrade() -> None:
    op.alter_column("analysis_results", "job_id", existing_type=sa.String(length=64), nullable=True)
    op.drop_index(op.f("ix_analysis_results_job_id"), table_name="analysis_results")
    op.drop_column("analysis_results", "result_payload")
    op.drop_column("analysis_results", "error_message")
    op.drop_column("analysis_results", "status")
    op.drop_column("analysis_results", "job_id")

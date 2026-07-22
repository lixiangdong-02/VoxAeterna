"""add_trial_period

Revision ID: a1b2c3d4e5f6
Revises: d6382e45fc8f
Create Date: 2026-07-19

给 trial_counts 新增 period_start_at 字段用于双周周期重置。
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'd6382e45fc8f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('trial_counts',
        sa.Column('period_start_at', sa.TIMESTAMP(), nullable=True))


def downgrade() -> None:
    op.drop_column('trial_counts', 'period_start_at')

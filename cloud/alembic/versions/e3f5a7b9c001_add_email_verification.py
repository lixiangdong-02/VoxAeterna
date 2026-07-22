"""add email verification

Revision ID: e3f5a7b9c001
Revises: d6382e45fc8f
Create Date: 2026-07-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3f5a7b9c001'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # email_verifications table
    op.create_table(
        'email_verifications',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('code', sa.String(6), nullable=False),
        sa.Column('purpose', sa.Enum('register', 'reset_password'), nullable=False),
        sa.Column('expires_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('used', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_email_purpose', 'email_verifications', ['email', 'purpose'])

    # Add 'pending' to users.status enum and change default
    op.execute("ALTER TABLE users MODIFY status ENUM('active','disabled','banned','pending') NOT NULL DEFAULT 'active'")

    # Add new columns to payment_orders for qrcode tracking
    op.add_column('payment_orders', sa.Column('out_trade_no', sa.String(128), server_default=''))
    op.add_column('payment_orders', sa.Column('qrcode_url', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_index('idx_email_purpose', table_name='email_verifications')
    op.drop_table('email_verifications')

    # Restore users.status enum (remove 'pending')
    # First set any pending users back to active
    op.execute("UPDATE users SET status = 'active' WHERE status = 'pending'")
    op.execute("ALTER TABLE users MODIFY status ENUM('active','disabled','banned') NOT NULL DEFAULT 'active'")

    op.drop_column('payment_orders', 'qrcode_url')
    op.drop_column('payment_orders', 'out_trade_no')

"""add customer notes table

Revision ID: 20260118_add_notes
Revises: 20260118_add_archived
Create Date: 2026-01-18 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260118_add_notes'
down_revision = '20260118_add_archived'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'customer_notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('admin_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('note', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['admin_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['customer_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_customer_notes_customer_id'), 'customer_notes', ['customer_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_customer_notes_customer_id'), table_name='customer_notes')
    op.drop_table('customer_notes')

"""add support ticket assignment and SLA

Revision ID: 20260118_add_support_features
Revises: 20260118_add_ad_tracking
Create Date: 2026-01-18 06:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '20260118_add_support_features'
down_revision = '20260118_add_ad_tracking'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('support_tickets', sa.Column('assigned_to', UUID(as_uuid=True), nullable=True))
    op.add_column('support_tickets', sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('support_tickets', sa.Column('sla_due_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('support_tickets', sa.Column('sla_breached', sa.Boolean(), nullable=False, server_default='false'))
    
    op.create_foreign_key('fk_support_tickets_assigned_to', 'support_tickets', 'users', ['assigned_to'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_support_tickets_assigned_to', 'support_tickets', type_='foreignkey')
    op.drop_column('support_tickets', 'sla_breached')
    op.drop_column('support_tickets', 'sla_due_at')
    op.drop_column('support_tickets', 'assigned_at')
    op.drop_column('support_tickets', 'assigned_to')

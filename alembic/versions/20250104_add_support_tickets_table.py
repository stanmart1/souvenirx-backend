"""Add support_tickets table

Revision ID: 20250104_add_support_tickets
Revises: 20250103_add_notifications
Create Date: 2025-01-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250104_add_support_tickets'
down_revision = '20250103_add_notifications'
branch_labels = None
depends_on = None


def upgrade():
    # Create support_tickets table
    op.create_table(
        'support_tickets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('guest_email', sa.String(255), nullable=True),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('attachment_url', sa.String(500), nullable=True),
        sa.Column('attachment_name', sa.String(255), nullable=True),
        sa.Column('status', sa.Enum('open', 'in_progress', 'resolved', 'closed', name='ticketstatus'), nullable=False, default='open'),
        sa.Column('priority', sa.Enum('low', 'medium', 'high', 'urgent', name='ticketpriority'), nullable=False, default='medium'),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('admin_response', sa.Text(), nullable=True),
        sa.Column('admin_responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('admin_responded_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table('support_tickets')

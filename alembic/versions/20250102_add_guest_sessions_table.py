"""Add guest_sessions table

Revision ID: 20250102_add_guest_sessions
Revises: 20250101_add_logo_uploads
Create Date: 2025-01-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250102_add_guest_sessions'
down_revision = '20250101_add_logo_uploads'
branch_labels = None
depends_on = None


def upgrade():
    # Create guest_sessions table
    op.create_table(
        'guest_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('cart_data', sa.Text(), nullable=True),
        sa.Column('converted_to_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('converted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table('guest_sessions')

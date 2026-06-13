"""Add logo_uploads table

Revision ID: 20250101_add_logo_uploads
Revises: 
Create Date: 2025-01-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250101_add_logo_uploads'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create logo_uploads table (idempotent)
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    
    if 'logo_uploads' not in inspector.get_table_names():
        op.create_table(
            'logo_uploads',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
            sa.Column('order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=True),
            sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=True),
            sa.Column('file_name', sa.String(255), nullable=False),
            sa.Column('file_url', sa.Text(), nullable=False),
            sa.Column('file_size', sa.String(50), nullable=False),
            sa.Column('mime_type', sa.String(100), nullable=False),
            sa.Column('status', sa.Enum('pending', 'approved', 'rejected', name='logouploadstatus'), nullable=False, server_default='pending'),
            sa.Column('rejection_reason', sa.Text(), nullable=True),
            sa.Column('admin_notes', sa.Text(), nullable=True),
            sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        )


def downgrade():
    op.drop_table('logo_uploads')

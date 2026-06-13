"""Add homepage content management

Revision ID: 20250113_add_homepage_content
Revises: 20250112_add_west_africa_lga_support
Create Date: 2025-01-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20250113_add_homepage_content'
down_revision = '20250112_add_west_africa_lga_support'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'homepage_content',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('section', sa.String(50), unique=True, nullable=False),
        sa.Column('content', postgresql.JSONB(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('sort_order', sa.Integer(), default=0),
    )


def downgrade():
    op.drop_table('homepage_content')

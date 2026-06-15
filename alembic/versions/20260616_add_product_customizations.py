"""Add product_customizations table

The table was defined in the ORM model (ProductCustomization) but a migration
was never written, so the table was absent from the production database.
This caused every query that selectinload(Product.customizations) to raise:
    ProgrammingError: relation "product_customizations" does not exist

Revision ID: 20260616_add_product_customizations
Revises: 20260615_wishlist
Create Date: 2026-06-16 00:00:00.000000
"""
from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '20260616_add_product_customizations'
down_revision: Union[str, None] = '20260615_wishlist'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent — safe to run even if the table already exists
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)

    if 'product_customizations' not in inspector.get_table_names():
        op.create_table(
            'product_customizations',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column(
                'product_id',
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey('products.id', ondelete='CASCADE'),
                nullable=False,
            ),
            sa.Column('type', sa.String(20), nullable=False),     # text | option | logo
            sa.Column('label', sa.String(100), nullable=False),
            sa.Column('max_length', sa.Integer(), nullable=True),
            sa.Column('values', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )
        op.create_index(
            'ix_product_customizations_product_id',
            'product_customizations',
            ['product_id'],
        )


def downgrade() -> None:
    op.drop_index('ix_product_customizations_product_id', table_name='product_customizations')
    op.drop_table('product_customizations')

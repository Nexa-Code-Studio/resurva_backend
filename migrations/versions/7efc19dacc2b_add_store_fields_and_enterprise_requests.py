"""add_store_fields_and_enterprise_requests

Revision ID: 7efc19dacc2b
Revises: ddcbc413838c
Create Date: 2026-07-15 16:01:02.555869

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7efc19dacc2b'
down_revision: Union[str, Sequence[str], None] = 'ddcbc413838c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE stores ADD COLUMN IF NOT EXISTS categories_data VARCHAR")
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS weight DOUBLE PRECISION DEFAULT 0.1")
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS is_published BOOLEAN DEFAULT TRUE")
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS auto_surplus_enabled BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS surplus_trigger_hours INTEGER DEFAULT 0")
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS ingredients_data VARCHAR")
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS sku VARCHAR")
    op.execute("""
    CREATE TABLE IF NOT EXISTS product_variant_groups (
        id UUID PRIMARY KEY,
        product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
        name VARCHAR NOT NULL,
        is_required BOOLEAN DEFAULT FALSE NOT NULL,
        max_selections INTEGER DEFAULT 1 NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS product_variant_options (
        id UUID PRIMARY KEY,
        variant_group_id UUID NOT NULL REFERENCES product_variant_groups(id) ON DELETE CASCADE,
        name VARCHAR NOT NULL,
        additional_price INTEGER DEFAULT 0 NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS order_item_variant_options (
        id UUID PRIMARY KEY,
        order_item_id UUID NOT NULL REFERENCES order_items(id) ON DELETE CASCADE,
        variant_option_id UUID REFERENCES product_variant_options(id) ON DELETE SET NULL,
        name VARCHAR NOT NULL,
        additional_price INTEGER DEFAULT 0 NOT NULL
    )
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS inventory_transactions (
        id UUID PRIMARY KEY,
        product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
        store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
        inventory_batch_id UUID REFERENCES inventory_batches(id) ON DELETE SET NULL,
        batch_tag VARCHAR,
        type VARCHAR NOT NULL,
        quantity INTEGER NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """)
    op.create_table('enterprise_requests',
    sa.Column('store_id', sa.Uuid(), nullable=False),
    sa.Column('corporate_name', sa.String(), nullable=False),
    sa.Column('pic_name', sa.String(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('phone', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_enterprise_requests_id'), 'enterprise_requests', ['id'], unique=False)
    op.alter_column('inventory_transactions', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False,
               existing_server_default=sa.text('now()'))
    op.create_index(op.f('ix_inventory_transactions_id'), 'inventory_transactions', ['id'], unique=False)
    op.create_index(op.f('ix_order_item_variant_options_id'), 'order_item_variant_options', ['id'], unique=False)
    op.alter_column('product_variant_groups', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False,
               existing_server_default=sa.text('now()'))
    op.create_index(op.f('ix_product_variant_groups_id'), 'product_variant_groups', ['id'], unique=False)
    op.alter_column('product_variant_options', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False,
               existing_server_default=sa.text('now()'))
    op.create_index(op.f('ix_product_variant_options_id'), 'product_variant_options', ['id'], unique=False)
    op.alter_column('products', 'weight',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=False,
               existing_server_default=sa.text('0.1'))
    op.alter_column('products', 'is_published',
               existing_type=sa.BOOLEAN(),
               nullable=False,
               existing_server_default=sa.text('true'))
    op.alter_column('products', 'auto_surplus_enabled',
               existing_type=sa.BOOLEAN(),
               nullable=False,
               existing_server_default=sa.text('false'))
    op.alter_column('products', 'surplus_trigger_hours',
               existing_type=sa.INTEGER(),
               nullable=False,
               existing_server_default=sa.text('0'))
    op.alter_column('products', 'ingredients_data',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.add_column('stores', sa.Column('description', sa.String(), nullable=True))
    op.add_column('stores', sa.Column('banner_url', sa.String(), nullable=True))
    op.add_column('stores', sa.Column('is_branch', sa.Boolean(), server_default='false', nullable=False))
    op.alter_column('stores', 'categories_data',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('stores', 'categories_data',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.drop_column('stores', 'is_branch')
    op.drop_column('stores', 'banner_url')
    op.drop_column('stores', 'description')
    op.alter_column('products', 'ingredients_data',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('products', 'surplus_trigger_hours',
               existing_type=sa.INTEGER(),
               nullable=True,
               existing_server_default=sa.text('0'))
    op.alter_column('products', 'auto_surplus_enabled',
               existing_type=sa.BOOLEAN(),
               nullable=True,
               existing_server_default=sa.text('false'))
    op.alter_column('products', 'is_published',
               existing_type=sa.BOOLEAN(),
               nullable=True,
               existing_server_default=sa.text('true'))
    op.alter_column('products', 'weight',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=True,
               existing_server_default=sa.text('0.1'))
    op.drop_index(op.f('ix_product_variant_options_id'), table_name='product_variant_options')
    op.alter_column('product_variant_options', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True,
               existing_server_default=sa.text('now()'))
    op.drop_index(op.f('ix_product_variant_groups_id'), table_name='product_variant_groups')
    op.alter_column('product_variant_groups', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True,
               existing_server_default=sa.text('now()'))
    op.drop_index(op.f('ix_order_item_variant_options_id'), table_name='order_item_variant_options')
    op.drop_index(op.f('ix_inventory_transactions_id'), table_name='inventory_transactions')
    op.alter_column('inventory_transactions', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True,
               existing_server_default=sa.text('now()'))
    op.drop_index(op.f('ix_enterprise_requests_id'), table_name='enterprise_requests')
    op.drop_table('enterprise_requests')
    # ### end Alembic commands ###

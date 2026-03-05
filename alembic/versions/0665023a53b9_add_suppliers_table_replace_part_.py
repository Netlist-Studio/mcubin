"""add suppliers table, replace part supplier text with supplier_id fk

Revision ID: 0665023a53b9
Revises: a3f1b2c4d5e6
Create Date: 2026-03-05 11:46:15.208179

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0665023a53b9'
down_revision: Union[str, Sequence[str], None] = 'a3f1b2c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'suppliers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('api_key', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    # SQLite requires batch mode to modify existing tables
    with op.batch_alter_table('parts') as batch_op:
        batch_op.add_column(sa.Column('supplier_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_parts_supplier_id', 'suppliers', ['supplier_id'], ['id'])
        batch_op.drop_column('supplier')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('parts') as batch_op:
        batch_op.add_column(sa.Column('supplier', sa.VARCHAR(), nullable=True))
        batch_op.drop_constraint('fk_parts_supplier_id', type_='foreignkey')
        batch_op.drop_column('supplier_id')
    op.drop_table('suppliers')

"""add locations table

Revision ID: a3f1b2c4d5e6
Revises: e9a4373f9cad
Create Date: 2026-03-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f1b2c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'e9a4373f9cad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create locations table
    op.create_table(
        'locations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(), nullable=False, unique=True),
    )

    # 2. Populate locations from existing parts.location values
    op.execute(sa.text(
        "INSERT INTO locations (name) "
        "SELECT DISTINCT location FROM parts "
        "WHERE location IS NOT NULL AND location != ''"
    ))

    # 3. Add location_id column to parts
    op.add_column('parts', sa.Column('location_id', sa.Integer(), nullable=True))

    # 4. Set location_id from location name
    op.execute(sa.text(
        "UPDATE parts SET location_id = ("
        "  SELECT id FROM locations WHERE locations.name = parts.location"
        ") WHERE location IS NOT NULL AND location != ''"
    ))

    # 5. Drop the old location text column (batch required for SQLite)
    with op.batch_alter_table('parts') as batch_op:
        batch_op.drop_column('location')


def downgrade() -> None:
    # 1. Re-add the location text column
    with op.batch_alter_table('parts') as batch_op:
        batch_op.add_column(sa.Column('location', sa.String(), nullable=True))

    # 2. Restore location text from FK
    op.execute(sa.text(
        "UPDATE parts SET location = ("
        "  SELECT name FROM locations WHERE locations.id = parts.location_id"
        ")"
    ))

    # 3. Drop location_id
    with op.batch_alter_table('parts') as batch_op:
        batch_op.drop_column('location_id')

    # 4. Drop locations table
    op.drop_table('locations')

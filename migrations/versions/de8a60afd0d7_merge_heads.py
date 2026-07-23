"""merge heads

Revision ID: de8a60afd0d7
Revises: 07ecb8d43f5d, 3174dd71df7a
Create Date: 2026-07-23 09:49:22.536662

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de8a60afd0d7'
down_revision: Union[str, Sequence[str], None] = ('07ecb8d43f5d', '3174dd71df7a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

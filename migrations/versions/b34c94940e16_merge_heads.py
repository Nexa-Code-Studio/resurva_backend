"""merge_heads

Revision ID: b34c94940e16
Revises: 3174dd71df7a, 07ecb8d43f5d
Create Date: 2026-07-23 00:26:47.268980

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b34c94940e16'
down_revision: Union[str, Sequence[str], None] = ('3174dd71df7a', '07ecb8d43f5d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

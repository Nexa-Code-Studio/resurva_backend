"""merge main heads

Revision ID: 888a3d7d626f
Revises: 8e63ae99cefc, b4f6d4b7314d
Create Date: 2026-07-23 15:25:06.598050

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '888a3d7d626f'
down_revision: Union[str, Sequence[str], None] = ('8e63ae99cefc', 'b4f6d4b7314d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

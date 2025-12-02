"""Current state marker

Revision ID: 003_current_state
Revises: 
Create Date: 2025-11-26 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_current_state'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Mark current database state as latest."""
    pass


def downgrade() -> None:
    """No downgrade needed."""
    pass

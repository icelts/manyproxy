"""Create core ManyProxy tables if they are missing.

Revision ID: 004_bootstrap_core_tables
Revises: 003_current_state
Create Date: 2025-12-01 20:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

from app.core.database import Base

# Ensure all models are imported so their tables are registered on Base.metadata
import app.models.user  # noqa: F401
import app.models.proxy  # noqa: F401
import app.models.order  # noqa: F401

# revision identifiers, used by Alembic.
revision = "004_bootstrap_core_tables"
down_revision = "003_current_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create every ORM-defined table if it does not already exist."""
    bind = op.get_bind()
    # Guard against missing metadata definitions
    if not Base.metadata.tables:
        raise RuntimeError("Base metadata has no tables registered; models import failed.")

    # create_all is idempotent when checkfirst=True, so existing tables stay untouched
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    """Drop ORM-defined tables (used only when rolling back this revision)."""
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind, checkfirst=True)

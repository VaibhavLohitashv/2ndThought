"""rename post columns and add threadrole member

Revision ID: a1b2c3d4e5f6
Revises: 38bfd3962f22
Create Date: 2025-12-02 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "38bfd3962f22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename columns on posts table
    with op.batch_alter_table("posts") as batch_op:
        batch_op.alter_column("parent_post_id", new_column_name="parent_id")
        batch_op.alter_column("created_by", new_column_name="user_id")

    # Add new enum value 'member' to threadrole (Postgres)
    # Use IF NOT EXISTS when supported
    try:
        op.execute("ALTER TYPE threadrole ADD VALUE IF NOT EXISTS 'member';")
    except Exception:
        # Fallback for Postgres versions without IF NOT EXISTS
        # Attempt to add; if it fails because value exists, ignore
        try:
            op.execute("ALTER TYPE threadrole ADD VALUE 'member';")
        except Exception:
            pass


def downgrade() -> None:
    # Rename columns back
    with op.batch_alter_table("posts") as batch_op:
        batch_op.alter_column("parent_id", new_column_name="parent_post_id")
        batch_op.alter_column("user_id", new_column_name="created_by")

    # NOTE: Removing enum values in Postgres is non-trivial; we leave 'member' value in place.

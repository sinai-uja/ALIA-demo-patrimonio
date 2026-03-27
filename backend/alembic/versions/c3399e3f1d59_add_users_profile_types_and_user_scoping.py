"""add users profile types and user scoping

Revision ID: c3399e3f1d59
Revises: 17bdc32dc6df
Create Date: 2026-03-27 22:50:26.845749

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3399e3f1d59"
down_revision: Union[str, Sequence[str], None] = "17bdc32dc6df"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Pre-generated UUIDs for seed data (deterministic for idempotency)
PROFILE_INVESTIGADOR_ID = "a1b2c3d4-0001-4000-8000-000000000001"
PROFILE_CIUDADANO_ID = "a1b2c3d4-0001-4000-8000-000000000002"


def upgrade() -> None:
    """Create user_profile_types and users tables, add user_id to chat_sessions and virtual_routes, seed profile types."""
    # 1. Create user_profile_types table
    op.create_table(
        "user_profile_types",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # 2. Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("profile_type_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["profile_type_id"], ["user_profile_types.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )

    # 3. Add user_id to chat_sessions
    op.add_column("chat_sessions", sa.Column("user_id", sa.UUID(), nullable=True))
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"], unique=False)
    op.create_foreign_key(
        "fk_chat_sessions_user_id", "chat_sessions", "users", ["user_id"], ["id"]
    )

    # 4. Add user_id to virtual_routes
    op.add_column("virtual_routes", sa.Column("user_id", sa.UUID(), nullable=True))
    op.create_index("ix_virtual_routes_user_id", "virtual_routes", ["user_id"], unique=False)
    op.create_foreign_key(
        "fk_virtual_routes_user_id", "virtual_routes", "users", ["user_id"], ["id"]
    )

    # 5. Seed initial profile types
    op.execute(
        sa.text(
            "INSERT INTO user_profile_types (id, name) VALUES "
            f"('{PROFILE_INVESTIGADOR_ID}', 'investigador'), "
            f"('{PROFILE_CIUDADANO_ID}', 'ciudadano')"
        )
    )


def downgrade() -> None:
    """Remove user scoping columns and drop users/profile_types tables."""
    # 1. Remove user_id from virtual_routes
    op.drop_constraint("fk_virtual_routes_user_id", "virtual_routes", type_="foreignkey")
    op.drop_index("ix_virtual_routes_user_id", table_name="virtual_routes")
    op.drop_column("virtual_routes", "user_id")

    # 2. Remove user_id from chat_sessions
    op.drop_constraint("fk_chat_sessions_user_id", "chat_sessions", type_="foreignkey")
    op.drop_index("ix_chat_sessions_user_id", table_name="chat_sessions")
    op.drop_column("chat_sessions", "user_id")

    # 3. Drop tables (users first due to FK to user_profile_types)
    op.drop_table("users")
    op.drop_table("user_profile_types")

"""initial schema with enums and unique constraints

Revision ID: 20260214_0001
Revises:
Create Date: 2026-02-14 09:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260214_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    user_role_enum = sa.Enum("admin", "creator", "feedbacker", name="user_role", native_enum=False)
    item_status_enum = sa.Enum("ongoing", "finished", name="item_status", native_enum=False)
    feedback_status_enum = sa.Enum("pending", "done", "completed", name="feedback_status", native_enum=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("password_hash", sa.String(), nullable=True),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("group", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("is_org", sa.Boolean(), nullable=True),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
    )
    op.create_index("ix_groups_id", "groups", ["id"], unique=False)
    op.create_index("ix_groups_name", "groups", ["name"], unique=False)

    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("status", item_status_enum, nullable=False),
        sa.Column("must_feedback", sa.Boolean(), nullable=True),
        sa.Column("deadline", sa.DateTime(), nullable=True),
        sa.Column("creator_id", sa.Integer(), nullable=True),
        sa.Column("attachments", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"]),
    )
    op.create_index("ix_items_id", "items", ["id"], unique=False)

    op.create_table(
        "item_users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("feedback_status", feedback_status_enum, nullable=False),
        sa.Column("last_feedback_time", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("item_id", "user_id", name="uq_item_user_item_user"),
    )
    op.create_index("ix_item_users_id", "item_users", ["id"], unique=False)

    op.create_table(
        "feedbacks",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("item_user_id", sa.Integer(), nullable=True),
        sa.Column("content", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["item_user_id"], ["item_users.id"]),
        sa.UniqueConstraint("item_user_id", name="uq_feedback_item_user"),
    )
    op.create_index("ix_feedbacks_id", "feedbacks", ["id"], unique=False)

    op.create_table(
        "group_users",
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("group_id", "user_id"),
    )

    op.create_table(
        "operation_logs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(), nullable=True),
        sa.Column("target_id", sa.String(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_operation_logs_id", "operation_logs", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_operation_logs_id", table_name="operation_logs")
    op.drop_table("operation_logs")

    op.drop_table("group_users")

    op.drop_index("ix_feedbacks_id", table_name="feedbacks")
    op.drop_table("feedbacks")

    op.drop_index("ix_item_users_id", table_name="item_users")
    op.drop_table("item_users")

    op.drop_index("ix_items_id", table_name="items")
    op.drop_table("items")

    op.drop_index("ix_groups_name", table_name="groups")
    op.drop_index("ix_groups_id", table_name="groups")
    op.drop_table("groups")

    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")

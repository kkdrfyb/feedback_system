"""add query indexes for hot paths

Revision ID: 20260214_0002
Revises: 20260214_0001
Create Date: 2026-02-14 10:20:00
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260214_0002"
down_revision: Union[str, Sequence[str], None] = "20260214_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_items_creator_id", "items", ["creator_id"], unique=False)
    op.create_index("ix_items_status", "items", ["status"], unique=False)
    op.create_index("ix_items_deadline", "items", ["deadline"], unique=False)

    op.create_index("ix_item_users_item_id", "item_users", ["item_id"], unique=False)
    op.create_index("ix_item_users_user_id", "item_users", ["user_id"], unique=False)
    op.create_index("ix_item_users_feedback_status", "item_users", ["feedback_status"], unique=False)

    op.create_index("ix_groups_owner_id", "groups", ["owner_id"], unique=False)

    op.create_index("ix_operation_logs_user_id", "operation_logs", ["user_id"], unique=False)
    op.create_index("ix_operation_logs_timestamp", "operation_logs", ["timestamp"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_operation_logs_timestamp", table_name="operation_logs")
    op.drop_index("ix_operation_logs_user_id", table_name="operation_logs")

    op.drop_index("ix_groups_owner_id", table_name="groups")

    op.drop_index("ix_item_users_feedback_status", table_name="item_users")
    op.drop_index("ix_item_users_user_id", table_name="item_users")
    op.drop_index("ix_item_users_item_id", table_name="item_users")

    op.drop_index("ix_items_deadline", table_name="items")
    op.drop_index("ix_items_status", table_name="items")
    op.drop_index("ix_items_creator_id", table_name="items")

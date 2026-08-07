"""add spreadsheet tables for online Excel collaboration

Revision ID: 20260214_0003
Revises: 20260214_0002
Create Date: 2026-08-06
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "20260214_0003"
down_revision: Union[str, Sequence[str], None] = "20260214_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "spreadsheets",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("creator_id", sa.Integer(), nullable=False),
        sa.Column("columns", sa.String(), nullable=True),
        sa.Column("owner_column", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"]),
    )
    op.create_index("ix_spreadsheets_id", "spreadsheets", ["id"], unique=False)

    op.create_table(
        "spreadsheet_rows",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("spreadsheet_id", sa.Integer(), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("data", sa.String(), nullable=True),
        sa.Column("last_edited_by", sa.Integer(), nullable=True),
        sa.Column("last_edited_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["spreadsheet_id"], ["spreadsheets.id"]),
        sa.ForeignKeyConstraint(["last_edited_by"], ["users.id"]),
    )
    op.create_index("ix_spreadsheet_rows_id", "spreadsheet_rows", ["id"], unique=False)
    op.create_index("ix_spreadsheet_rows_sheet_id", "spreadsheet_rows", ["spreadsheet_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_spreadsheet_rows_sheet_id", table_name="spreadsheet_rows")
    op.drop_index("ix_spreadsheet_rows_id", table_name="spreadsheet_rows")
    op.drop_table("spreadsheet_rows")

    op.drop_index("ix_spreadsheets_id", table_name="spreadsheets")
    op.drop_table("spreadsheets")

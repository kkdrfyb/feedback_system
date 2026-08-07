import argparse
import os
import sqlite3
import sys


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def _required_tables_present(conn: sqlite3.Connection) -> bool:
    required = ["users", "items", "item_users", "feedbacks"]
    missing = [name for name in required if not _table_exists(conn, name)]
    if missing:
        print(f"Missing required tables: {', '.join(missing)}", file=sys.stderr)
        return False
    return True


def _collect_stats(conn: sqlite3.Connection) -> dict:
    stats = {}
    stats["invalid_user_roles"] = conn.execute(
        """
        SELECT COUNT(*) FROM users
        WHERE role IS NULL OR TRIM(role) = '' OR role NOT IN ('admin', 'creator', 'feedbacker')
        """
    ).fetchone()[0]
    stats["invalid_item_status"] = conn.execute(
        """
        SELECT COUNT(*) FROM items
        WHERE status IS NULL OR TRIM(status) = '' OR status NOT IN ('ongoing', 'finished')
        """
    ).fetchone()[0]
    stats["invalid_feedback_status"] = conn.execute(
        """
        SELECT COUNT(*) FROM item_users
        WHERE feedback_status IS NULL OR TRIM(feedback_status) = ''
           OR feedback_status NOT IN ('pending', 'done', 'completed')
        """
    ).fetchone()[0]

    duplicate_item_user_groups = conn.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT item_id, user_id, COUNT(*) AS c
            FROM item_users
            GROUP BY item_id, user_id
            HAVING c > 1
        )
        """
    ).fetchone()[0]
    duplicate_item_user_rows = conn.execute(
        """
        SELECT COALESCE(SUM(c - 1), 0) FROM (
            SELECT COUNT(*) AS c
            FROM item_users
            GROUP BY item_id, user_id
            HAVING c > 1
        )
        """
    ).fetchone()[0]
    stats["duplicate_item_user_groups"] = duplicate_item_user_groups
    stats["duplicate_item_user_rows"] = duplicate_item_user_rows

    duplicate_feedback_groups = conn.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT item_user_id, COUNT(*) AS c
            FROM feedbacks
            WHERE item_user_id IS NOT NULL
            GROUP BY item_user_id
            HAVING c > 1
        )
        """
    ).fetchone()[0]
    duplicate_feedback_rows = conn.execute(
        """
        SELECT COALESCE(SUM(c - 1), 0) FROM (
            SELECT COUNT(*) AS c
            FROM feedbacks
            WHERE item_user_id IS NOT NULL
            GROUP BY item_user_id
            HAVING c > 1
        )
        """
    ).fetchone()[0]
    stats["duplicate_feedback_groups"] = duplicate_feedback_groups
    stats["duplicate_feedback_rows"] = duplicate_feedback_rows

    stats["orphan_feedback_rows"] = conn.execute(
        """
        SELECT COUNT(*) FROM feedbacks
        WHERE item_user_id IS NULL
           OR item_user_id NOT IN (SELECT id FROM item_users)
        """
    ).fetchone()[0]
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Check legacy data health before migrations.")
    default_db = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "feedback.db"))
    parser.add_argument("--db", default=default_db, help="Path to sqlite db file (default: backend/feedback.db)")
    parser.add_argument("--strict", action="store_true", help="Exit with non-zero code if any issue is found")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"Database file not found: {args.db}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(args.db)
    try:
        if not _required_tables_present(conn):
            sys.exit(1)

        stats = _collect_stats(conn)
        total_issues = sum(stats.values())

        print("Legacy Data Health Report")
        print(f"db: {args.db}")
        for key, value in stats.items():
            print(f"{key}: {value}")
        print(f"total_issues: {total_issues}")

        if total_issues > 0:
            print("Suggestion: run `python scripts/cleanup_legacy_data.py --dry-run` then `python scripts/cleanup_legacy_data.py`.")
            if args.strict:
                sys.exit(2)
    finally:
        conn.close()


if __name__ == "__main__":
    main()

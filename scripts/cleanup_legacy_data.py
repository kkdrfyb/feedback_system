import argparse
import os
import sqlite3
import sys
from datetime import datetime


VALID_USER_ROLES = {"admin", "creator", "feedbacker"}
VALID_ITEM_STATUS = {"ongoing", "finished"}
VALID_FEEDBACK_STATUS = {"pending", "done", "completed"}


def _safe_dt(value: str) -> datetime:
    if not value:
        return datetime.min
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min


def _normalize_invalid_values(conn: sqlite3.Connection, stats: dict) -> None:
    role_changed = conn.execute(
        """
        UPDATE users
        SET role = 'feedbacker'
        WHERE role IS NULL OR TRIM(role) = '' OR role NOT IN ('admin', 'creator', 'feedbacker')
        """
    ).rowcount
    stats["users_role_fixed"] += role_changed

    item_status_changed = conn.execute(
        """
        UPDATE items
        SET status = 'ongoing'
        WHERE status IS NULL OR TRIM(status) = '' OR status NOT IN ('ongoing', 'finished')
        """
    ).rowcount
    stats["items_status_fixed"] += item_status_changed

    feedback_status_changed = conn.execute(
        """
        UPDATE item_users
        SET feedback_status = 'pending'
        WHERE feedback_status IS NULL OR TRIM(feedback_status) = ''
           OR feedback_status NOT IN ('pending', 'done', 'completed')
        """
    ).rowcount
    stats["item_users_status_fixed"] += feedback_status_changed


def _deduplicate_item_users(conn: sqlite3.Connection, stats: dict) -> None:
    groups = conn.execute(
        """
        SELECT item_id, user_id, COUNT(*) as cnt
        FROM item_users
        GROUP BY item_id, user_id
        HAVING cnt > 1
        """
    ).fetchall()

    for group in groups:
        item_id = group["item_id"]
        user_id = group["user_id"]
        rows = conn.execute(
            """
            SELECT id, feedback_status, last_feedback_time
            FROM item_users
            WHERE item_id = ? AND user_id = ?
            ORDER BY id ASC
            """,
            (item_id, user_id),
        ).fetchall()

        if len(rows) <= 1:
            continue

        def row_score(row):
            status = row["feedback_status"] or ""
            status_rank = 2 if status in ("done", "completed") else (1 if status == "pending" else 0)
            dt_rank = _safe_dt(row["last_feedback_time"])
            return (status_rank, dt_rank, row["id"])

        survivor = max(rows, key=row_score)
        donor_ids = [r["id"] for r in rows if r["id"] != survivor["id"]]

        final_status = "done" if any((r["feedback_status"] or "") in ("done", "completed") for r in rows) else "pending"
        max_feedback_time = max((_safe_dt(r["last_feedback_time"]) for r in rows), default=datetime.min)
        max_feedback_time_str = None if max_feedback_time == datetime.min else max_feedback_time.isoformat()

        conn.execute(
            """
            UPDATE item_users
            SET feedback_status = ?, last_feedback_time = ?
            WHERE id = ?
            """,
            (final_status, max_feedback_time_str, survivor["id"]),
        )

        for donor_id in donor_ids:
            moved = conn.execute(
                """
                UPDATE feedbacks
                SET item_user_id = ?
                WHERE item_user_id = ?
                """,
                (survivor["id"], donor_id),
            ).rowcount
            stats["feedback_reassigned"] += moved

        deleted = conn.execute(
            f"""
            DELETE FROM item_users
            WHERE id IN ({",".join("?" for _ in donor_ids)})
            """,
            donor_ids,
        ).rowcount

        stats["duplicate_item_user_groups"] += 1
        stats["item_users_deleted"] += deleted


def _deduplicate_feedbacks(conn: sqlite3.Connection, stats: dict) -> None:
    groups = conn.execute(
        """
        SELECT item_user_id, COUNT(*) AS cnt
        FROM feedbacks
        WHERE item_user_id IS NOT NULL
        GROUP BY item_user_id
        HAVING cnt > 1
        """
    ).fetchall()

    for group in groups:
        item_user_id = group["item_user_id"]
        rows = conn.execute(
            """
            SELECT id, content, created_at, updated_at
            FROM feedbacks
            WHERE item_user_id = ?
            ORDER BY id ASC
            """,
            (item_user_id,),
        ).fetchall()

        if len(rows) <= 1:
            continue

        def row_score(row):
            ts = row["updated_at"] or row["created_at"] or ""
            return (_safe_dt(ts), row["id"])

        survivor = max(rows, key=row_score)
        donor_ids = [r["id"] for r in rows if r["id"] != survivor["id"]]

        deleted = conn.execute(
            f"""
            DELETE FROM feedbacks
            WHERE id IN ({",".join("?" for _ in donor_ids)})
            """,
            donor_ids,
        ).rowcount

        stats["duplicate_feedback_groups"] += 1
        stats["feedback_deleted"] += deleted


def _cleanup_orphans(conn: sqlite3.Connection, stats: dict) -> None:
    deleted = conn.execute(
        """
        DELETE FROM feedbacks
        WHERE item_user_id IS NULL
           OR item_user_id NOT IN (SELECT id FROM item_users)
        """
    ).rowcount
    stats["orphan_feedback_deleted"] += deleted


def main() -> None:
    parser = argparse.ArgumentParser(description="Cleanup legacy dirty data before enabling stricter schema constraints.")
    default_db = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "feedback.db"))
    parser.add_argument("--db", default=default_db, help="Path to sqlite db file (default: backend/feedback.db)")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes and rollback")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"Database file not found: {args.db}", file=sys.stderr)
        sys.exit(1)

    stats = {
        "users_role_fixed": 0,
        "items_status_fixed": 0,
        "item_users_status_fixed": 0,
        "duplicate_item_user_groups": 0,
        "item_users_deleted": 0,
        "feedback_reassigned": 0,
        "duplicate_feedback_groups": 0,
        "feedback_deleted": 0,
        "orphan_feedback_deleted": 0,
    }

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    try:
        _normalize_invalid_values(conn, stats)
        _deduplicate_item_users(conn, stats)
        _deduplicate_feedbacks(conn, stats)
        _cleanup_orphans(conn, stats)

        if args.dry_run:
            conn.rollback()
            print("Dry run complete (rolled back).")
        else:
            conn.commit()
            print("Cleanup committed.")

        for key, value in stats.items():
            print(f"{key}: {value}")
    except Exception as exc:
        conn.rollback()
        print(f"Cleanup failed: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()

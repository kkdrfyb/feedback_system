import argparse
import json
import os
import sys

from sqlalchemy import or_

try:
    from backend.database import SessionLocal
    from backend import models
except (ImportError, ValueError):
    from database import SessionLocal
    import models


def safe_remove_file(path):
    if not path:
        return
    file_path = path.lstrip("/")
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass


def collect_items(session, run_id):
    return session.query(models.Item).filter(
        or_(
            models.Item.title.like(f"Sim Item {run_id}-%"),
            models.Item.title.like(f"Coverage Item {run_id}%"),
        )
    ).all()


def collect_users(session, run_id):
    return session.query(models.User).filter(
        or_(
            models.User.username.like(f"sim_{run_id}_%"),
            models.User.username.like(f"import_{run_id}_%"),
            models.User.username == f"temp_delete_{run_id}",
        )
    ).all()


def collect_groups(session, run_id):
    group_names = [
        f"SimGroup_{run_id}",
        f"OldGroup_{run_id}",
        f"Imported_{run_id}_A",
        f"Imported_{run_id}_B",
        f"TempGroup_{run_id}",
    ]
    return session.query(models.Group).filter(models.Group.name.in_(group_names)).all()


def delete_items(session, run_id, dry_run=False):
    items = collect_items(session, run_id)
    item_ids = [item.id for item in items]
    if dry_run:
        return len(item_ids)

    for item in items:
        if item.attachments:
            try:
                attachments = json.loads(item.attachments)
                if isinstance(attachments, list):
                    for attachment in attachments:
                        if isinstance(attachment, dict):
                            safe_remove_file(attachment.get("path"))
            except json.JSONDecodeError:
                pass

    if item_ids:
        iu_ids = [
            item_user_id
            for (item_user_id,) in session.query(models.ItemUser.id)
            .filter(models.ItemUser.item_id.in_(item_ids))
            .all()
        ]
        if iu_ids:
            session.query(models.Feedback).filter(
                models.Feedback.item_user_id.in_(iu_ids)
            ).delete(synchronize_session=False)
            session.query(models.ItemUser).filter(
                models.ItemUser.id.in_(iu_ids)
            ).delete(synchronize_session=False)
        session.query(models.Item).filter(models.Item.id.in_(item_ids)).delete(
            synchronize_session=False
        )
    return len(item_ids)


def delete_users(session, run_id, dry_run=False):
    users = collect_users(session, run_id)
    user_ids = [user.id for user in users]
    if dry_run:
        return len(user_ids)

    if user_ids:
        session.execute(
            models.group_users.delete().where(models.group_users.c.user_id.in_(user_ids))
        )

        iu_ids = [
            item_user_id
            for (item_user_id,) in session.query(models.ItemUser.id)
            .filter(models.ItemUser.user_id.in_(user_ids))
            .all()
        ]
        if iu_ids:
            session.query(models.Feedback).filter(
                models.Feedback.item_user_id.in_(iu_ids)
            ).delete(synchronize_session=False)
            session.query(models.ItemUser).filter(
                models.ItemUser.id.in_(iu_ids)
            ).delete(synchronize_session=False)

        session.query(models.OperationLog).filter(
            models.OperationLog.user_id.in_(user_ids)
        ).delete(synchronize_session=False)

        session.query(models.User).filter(models.User.id.in_(user_ids)).delete(
            synchronize_session=False
        )
    return len(user_ids)


def delete_groups(session, run_id, dry_run=False):
    groups = collect_groups(session, run_id)
    group_ids = [group.id for group in groups]
    if dry_run:
        return len(group_ids)

    if group_ids:
        session.execute(
            models.group_users.delete().where(models.group_users.c.group_id.in_(group_ids))
        )
        session.query(models.Group).filter(models.Group.id.in_(group_ids)).delete(
            synchronize_session=False
        )
    return len(group_ids)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True, help="Run id from simulate_user_actions.py")
    parser.add_argument("--dry-run", action="store_true", help="Only report counts")
    args = parser.parse_args()

    session = SessionLocal()
    try:
        items_count = delete_items(session, args.run_id, dry_run=args.dry_run)
        users_count = delete_users(session, args.run_id, dry_run=args.dry_run)
        groups_count = delete_groups(session, args.run_id, dry_run=args.dry_run)

        if args.dry_run:
            print(
                f"Dry run: items={items_count}, users={users_count}, groups={groups_count}"
            )
            session.rollback()
            return

        session.commit()
        print(
            f"Cleanup complete: items={items_count}, users={users_count}, groups={groups_count}"
        )
    except Exception as exc:
        session.rollback()
        print(f"Cleanup failed: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()

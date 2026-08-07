import argparse
import csv
import io
import json
import os
import random
import sys
import time
from datetime import datetime, timedelta

import requests


def api_request(method, base_url, path, token=None, **kwargs):
    url = f"{base_url}{path}"
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.request(method, url, headers=headers, timeout=60, **kwargs)
    if response.status_code >= 400:
        raise RuntimeError(f"{method} {path} -> {response.status_code}: {response.text}")
    return response


def login(base_url, username, password):
    res = api_request(
        "POST",
        base_url,
        "/api/login",
        json={"username": username, "password": password},
    )
    data = res.json()
    return data["access_token"], data["user_id"], data.get("role")


def ensure_user(base_url, token, users_by_username, username, name, password, role, group):
    if username in users_by_username:
        return users_by_username[username]
    payload = {
        "username": username,
        "name": name,
        "password": password,
        "role": role,
        "group": group,
    }
    res = api_request("POST", base_url, "/api/users", token=token, json=payload)
    user = res.json()
    users_by_username[username] = user
    return user


def build_import_csv(rows):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["username", "name", "password", "role", "group"])
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue().encode("utf-8-sig")


def create_item(
    base_url,
    token,
    creator_id,
    title,
    description,
    deadline,
    user_ids,
    with_attachment=False,
):
    data = {
        "title": title,
        "description": description,
        "deadline": deadline,
        "must_feedback": "true",
        "creator_id": str(creator_id),
        "user_ids": json.dumps(user_ids),
    }
    files = []
    if with_attachment:
        files.append(("files", ("template.txt", b"Attachment template", "text/plain")))
    res = api_request(
        "POST",
        base_url,
        "/api/items",
        token=token,
        data=data,
        files=files if files else None,
    )
    return res.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--admin-user", default="admin")
    parser.add_argument("--admin-pass", default="123")
    parser.add_argument("--run-id", default=datetime.now().strftime("%Y%m%d%H%M%S"))
    parser.add_argument("--creator-count", type=int, default=20)
    parser.add_argument("--participant-count", type=int, default=30)
    parser.add_argument("--min-participants", type=int, default=20)
    parser.add_argument("--max-participants", type=int, default=30)
    parser.add_argument("--feedback-rate", type=float, default=0.6)
    parser.add_argument("--update-rate", type=float, default=0.3)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    run_id = args.run_id

    print(f"Sim run id: {run_id}")

    admin_token, admin_id, admin_role = login(base_url, args.admin_user, args.admin_pass)
    print(f"Admin login OK (id={admin_id}, role={admin_role})")

    users_res = api_request("GET", base_url, "/api/users", token=admin_token)
    users_by_username = {u["username"]: u for u in users_res.json()}

    # Create a user and delete it (admin action)
    temp_user = ensure_user(
        base_url,
        admin_token,
        users_by_username,
        f"temp_delete_{run_id}",
        f"Temp Delete {run_id}",
        "123456",
        "feedbacker",
        f"TempGroup_{run_id}",
    )
    api_request("DELETE", base_url, f"/api/users/{temp_user['id']}", token=admin_token)
    users_by_username.pop(temp_user["username"], None)
    print("Admin create/delete user OK")

    # Prepare normal users
    participants = []
    for i in range(1, args.participant_count + 1):
        username = f"sim_{run_id}_{i:02d}"
        user = ensure_user(
            base_url,
            admin_token,
            users_by_username,
            username,
            f"Sim User {i:02d}",
            "123456",
            "feedbacker",
            f"SimGroup_{run_id}",
        )
        participants.append(user)
    print(f"Prepared {len(participants)} participants")

    # Create group and update membership
    group_payload = {
        "name": f"SimGroup_{run_id}",
        "description": "Simulation group",
        "is_org": True,
        "user_ids": [u["id"] for u in participants[:5]],
    }
    group_res = api_request(
        "POST",
        base_url,
        f"/api/groups?owner_id={admin_id}&role=admin",
        token=admin_token,
        json=group_payload,
    )
    group_id = group_res.json()["id"]

    updated_ids = [u["id"] for u in participants[5:10]]
    group_data = group_res.json()
    api_request(
        "PUT",
        base_url,
        f"/api/groups/{group_id}?user_id={admin_id}&role=admin",
        token=admin_token,
        json={
            "name": group_data.get("name"),
            "description": group_data.get("description", ""),
            "is_org": group_data.get("is_org", True),
            "user_ids": updated_ids,
        },
    )
    print("Group create/update OK")

    # Create and delete an old group
    old_group_res = api_request(
        "POST",
        base_url,
        f"/api/groups?owner_id={admin_id}&role=admin",
        token=admin_token,
        json={
            "name": f"OldGroup_{run_id}",
            "description": "Old group to delete",
            "is_org": True,
            "user_ids": [],
        },
    )
    old_group_id = old_group_res.json()["id"]
    api_request(
        "DELETE",
        base_url,
        f"/api/groups/{old_group_id}?user_id={admin_id}&role=admin",
        token=admin_token,
    )
    print("Group delete OK")

    # Import groups via CSV
    import_rows = [
        {
            "username": f"import_{run_id}_01",
            "name": "Import User 01",
            "password": "admin",
            "role": "feedbacker",
            "group": f"Imported_{run_id}_A",
        },
        {
            "username": f"import_{run_id}_02",
            "name": "Import User 02",
            "password": "admin",
            "role": "feedbacker",
            "group": f"Imported_{run_id}_B",
        },
    ]
    import_csv = build_import_csv(import_rows)
    api_request(
        "POST",
        base_url,
        f"/api/groups/import?owner_id={admin_id}",
        token=admin_token,
        files={"file": ("groups.csv", import_csv, "text/csv")},
    )
    print("Group import OK")

    # Login normal users
    tokens = {}
    for user in participants:
        token, user_id, _ = login(base_url, user["username"], "123456")
        tokens[user["id"]] = token
    print("Normal user login OK")

    # Create items by 20 creators
    creators = participants[: args.creator_count]
    participant_ids = [u["id"] for u in participants]
    assigned_counts = {uid: 0 for uid in participant_ids}
    created_items = []
    for idx, creator in enumerate(creators, start=1):
        num_participants = random.randint(args.min_participants, args.max_participants)
        num_participants = min(num_participants, len(participant_ids))
        selected = random.sample(participant_ids, num_participants)
        for uid in selected:
            assigned_counts[uid] += 1

        deadline = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        title = f"Sim Item {run_id}-{idx:02d}"
        item = create_item(
            base_url,
            tokens[creator["id"]],
            creator["id"],
            title,
            "Simulation item description",
            deadline,
            selected,
            with_attachment=(idx % 5 == 0),
        )
        created_items.append(item)

        # Check progress right after creation
        item_detail = api_request("GET", base_url, f"/api/items/{item['id']}", token=tokens[creator["id"]]).json()
        feedbacks = item_detail.get("feedbacks", [])
        done_count = sum(1 for f in feedbacks if f.get("status") in ("done", "completed"))
        print(f"Item {item['id']} progress: {done_count}/{len(feedbacks)}")

    # Ensure all users have at least one assignment
    missing = [uid for uid, count in assigned_counts.items() if count == 0]
    if missing:
        creator = creators[0]
        selected = missing[:]
        while len(selected) < args.min_participants:
            selected.append(random.choice(participant_ids))
        deadline = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
        item = create_item(
            base_url,
            tokens[creator["id"]],
            creator["id"],
            f"Coverage Item {run_id}",
            "Ensure every user has at least one assignment",
            deadline,
            selected,
            with_attachment=True,
        )
        created_items.append(item)
        print(f"Coverage item created for {len(missing)} users")

    # All users process feedback randomly
    feedback_updates = 0
    for user in participants:
        token = tokens[user["id"]]
        todos = api_request("GET", base_url, "/api/todos", token=token).json()
        for todo in todos:
            if random.random() > args.feedback_rate:
                continue
            content = f"Feedback from {user['username']} at {datetime.now().isoformat()}"
            fb_res = api_request(
                "POST",
                base_url,
                "/api/feedbacks",
                token=token,
                json={"item_user_id": todo["item_user_id"], "content": content},
            ).json()

            # Update feedback multiple times for a subset
            if random.random() < args.update_rate:
                for i in range(2):
                    new_content = f"{content} (update {i + 1})"
                    api_request(
                        "PUT",
                        base_url,
                        f"/api/feedbacks/{fb_res['id']}",
                        token=token,
                        json={"content": new_content},
                    )
                    feedback_updates += 1
    print(f"Feedback submission done. Updates performed: {feedback_updates}")

    # 20 users check their views and search
    for user in creators:
        token = tokens[user["id"]]
        api_request("GET", base_url, "/api/items?scope=mine_created", token=token)
        api_request("GET", base_url, "/api/items?scope=mine_assigned", token=token)
        api_request(
            "GET",
            base_url,
            f"/api/items?scope=mine_assigned&title_like={run_id}",
            token=token,
        )
        api_request(
            "GET",
            base_url,
            "/api/items?scope=mine_assigned&status=finished",
            token=token,
        )
    print("User view/search checks OK")

    # Stats summary (after feedback)
    stats = api_request("GET", base_url, "/api/items/stats/summary", token=admin_token).json()
    print(f"Stats summary OK: total_items={stats.get('total_items')}, completion_rate={stats.get('completion_rate')}")

    # Export users (after feedback)
    export_res = api_request("GET", base_url, "/api/users/export", token=admin_token)
    export_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(export_dir, exist_ok=True)
    export_path = os.path.join(export_dir, f"users_export_{run_id}.csv")
    with open(export_path, "wb") as f:
        f.write(export_res.content)
    print(f"Export users OK -> {export_path}")

    # Operation logs (after feedback)
    logs = api_request("GET", base_url, "/api/operation_logs?limit=20", token=admin_token).json()
    print(f"Operation logs OK (latest {len(logs)})")

    print("Simulation completed successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Simulation failed: {exc}", file=sys.stderr)
        sys.exit(1)

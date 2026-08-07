from datetime import datetime, timedelta, timezone
import bcrypt
import json
from backend import models

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def login_headers(client, username: str, password: str):
    res = client.post("/api/login", json={"username": username, "password": password})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, res.json()

def test_api_ping(client, db):
    hashed_pw = get_password_hash("password123")
    user = models.User(username="pinguser", name="测试用户", password_hash=hashed_pw, role="feedbacker")
    db.add(user)
    db.commit()

    response = client.post("/api/login", json={"username": "pinguser", "password": "password123"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/items", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "items" in data and "total" in data
    assert data["items"] == []

def test_create_user_and_login(client, db):
    # 手动创建一个测试用户
    hashed_pw = get_password_hash("password123")
    user = models.User(username="testuser", name="测试用户", password_hash=hashed_pw, role="feedbacker")
    db.add(user)
    db.commit()

    # 测试登录
    response = client.post("/api/login", json={"username": "testuser", "password": "password123"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "feedbacker"

def test_item_workflow(client, db):
    # 1. 创建用户
    hashed_pw = get_password_hash("123")
    u1 = models.User(username="u1", name="用户1", password_hash=hashed_pw, role="feedbacker")
    u2 = models.User(username="admin", name="管理", password_hash=hashed_pw, role="admin")
    db.add_all([u1, u2])
    db.commit()
    
    # 2. 登录 admin
    headers, _ = login_headers(client, "admin", "123")
    
    # 3. 创建事项
    # 注意：/api/items 接口接收 Form Data，而不是 JSON，因为涉及到文件上传
    # 并且 deadline 格式需要是 "%Y-%m-%d %H:%M:%S"
    deadline = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    
    # user_ids 需要作为 JSON 字符串传递
    # 使用 data=... 发送 form-data
    item_data = {
        "title": "测试任务",
        "description": "内容",
        "deadline": deadline,
        "must_feedback": True,
        "creator_id": u2.id,
        "user_ids": json.dumps([u1.id])
    }
    
    # client.post 使用 data=... 时默认 Content-Type: application/x-www-form-urlencoded
    # 如果要模拟 multipart/form-data（虽然这里没有文件），通常也可以。
    # TestClient 会自动处理。如果后端用了 Form(...)，它既接受 urlencoded 也接受 multipart
    # 但由于后端有 File(...) 参数，最好明确一下，或者 TestClient 足够智能
    # 这里的关键是不能用 json=...
    res = client.post("/api/items", data=item_data, headers=headers)
    assert res.status_code == 200
    item_id = res.json()["id"]

    # 4. 检查待办事项 (用户1登录)
    u1_headers, u1_login = login_headers(client, "u1", "123")
    u1_id = u1_login["user_id"]
    
    res = client.get(f"/api/todos?user_id={u1_id}", headers=u1_headers)
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["title"] == "测试任务"

    # 5. 提交反馈
    # 获取 item_user_id
    iu = db.query(models.ItemUser).filter_by(item_id=item_id, user_id=u1_id).first()
    assert iu is not None
    
    feedback_payload = {
        "item_user_id": iu.id,
        "content": "反馈完成"
    }
    res = client.post("/api/feedbacks", json=feedback_payload, headers=u1_headers)
    assert res.status_code == 200
    
    # 6. 验证状态更新
    db.refresh(iu)
    assert iu.feedback_status == "done"
    assert iu.last_feedback_time is not None

def test_users_endpoint_requires_admin(client, db):
    hashed_pw = get_password_hash("123")
    admin = models.User(username="admin2", name="管理员", password_hash=hashed_pw, role="admin")
    normal = models.User(username="normal2", name="普通用户", password_hash=hashed_pw, role="feedbacker")
    db.add_all([admin, normal])
    db.commit()

    normal_headers, _ = login_headers(client, "normal2", "123")
    admin_headers, _ = login_headers(client, "admin2", "123")

    res = client.get("/api/users", headers=normal_headers)
    assert res.status_code == 403

    res = client.get("/api/users", headers=admin_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # 普通用户可以读取用于事项指派/私有分组的安全用户目录，但不能管理用户。
    res = client.get("/api/users/assignable", headers=normal_headers)
    assert res.status_code == 200
    assert {user["username"] for user in res.json()} == {"admin2", "normal2"}

def test_todo_scope_and_feedback_authorization(client, db):
    hashed_pw = get_password_hash("123")
    admin = models.User(username="admin3", name="管理员", password_hash=hashed_pw, role="admin")
    u1 = models.User(username="u1x", name="用户1", password_hash=hashed_pw, role="feedbacker")
    u2 = models.User(username="u2x", name="用户2", password_hash=hashed_pw, role="feedbacker")
    db.add_all([admin, u1, u2])
    db.commit()

    admin_headers, _ = login_headers(client, "admin3", "123")
    u1_headers, u1_login = login_headers(client, "u1x", "123")
    u2_headers, _ = login_headers(client, "u2x", "123")

    deadline = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    item_data = {
        "title": "权限测试任务",
        "description": "内容",
        "deadline": deadline,
        "must_feedback": True,
        "creator_id": admin.id,
        "user_ids": json.dumps([u1.id])
    }
    create_res = client.post("/api/items", data=item_data, headers=admin_headers)
    assert create_res.status_code == 200
    item_id = create_res.json()["id"]

    # 非管理员不能查看其他人的待办
    res = client.get(f"/api/todos?user_id={u1_login['user_id']}", headers=u2_headers)
    assert res.status_code == 403

    iu = db.query(models.ItemUser).filter_by(item_id=item_id, user_id=u1.id).first()
    assert iu is not None

    # 非管理员不能代他人提交反馈
    res = client.post("/api/feedbacks", json={"item_user_id": iu.id, "content": "代提交"}, headers=u2_headers)
    assert res.status_code == 403

    # 本人可以提交
    res = client.post("/api/feedbacks", json={"item_user_id": iu.id, "content": "本人提交"}, headers=u1_headers)
    assert res.status_code == 200
    assert res.json()["content"] == "本人提交"

def test_personal_groups_are_visible_only_to_owner_and_admin(client, db):
    hashed_pw = get_password_hash("123")
    admin = models.User(username="admin_group", name="管理员", password_hash=hashed_pw, role="admin")
    owner = models.User(username="owner_group", name="分组创建者", password_hash=hashed_pw, role="feedbacker")
    other = models.User(username="other_group", name="其他用户", password_hash=hashed_pw, role="feedbacker")
    db.add_all([admin, owner, other])
    db.commit()

    owner_headers, _ = login_headers(client, "owner_group", "123")
    other_headers, _ = login_headers(client, "other_group", "123")
    admin_headers, _ = login_headers(client, "admin_group", "123")

    create_res = client.post("/api/groups", json={
        "name": "创建者的私有分组",
        "description": "仅创建者与管理员可见",
        "is_org": False,
        "user_ids": [other.id],
    }, headers=owner_headers)
    assert create_res.status_code == 200
    group_id = create_res.json()["id"]

    owner_groups = client.get("/api/groups", headers=owner_headers).json()
    assert group_id in {group["id"] for group in owner_groups}

    other_groups = client.get("/api/groups", headers=other_headers).json()
    assert group_id not in {group["id"] for group in other_groups}

    admin_groups = client.get("/api/groups", headers=admin_headers).json()
    assert group_id in {group["id"] for group in admin_groups}

def test_create_item_deduplicates_assignments(client, db):
    hashed_pw = get_password_hash("123")
    admin = models.User(username="admin4", name="管理员", password_hash=hashed_pw, role="admin")
    u1 = models.User(username="u1d", name="用户1", password_hash=hashed_pw, role="feedbacker")
    db.add_all([admin, u1])
    db.commit()

    admin_headers, _ = login_headers(client, "admin4", "123")
    deadline = (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
    item_data = {
        "title": "去重测试任务",
        "description": "内容",
        "deadline": deadline,
        "must_feedback": True,
        "creator_id": admin.id,
        "user_ids": json.dumps([u1.id, u1.id, u1.id]),
    }
    res = client.post("/api/items", data=item_data, headers=admin_headers)
    assert res.status_code == 200
    item_id = res.json()["id"]

    assigned_count = db.query(models.ItemUser).filter(models.ItemUser.item_id == item_id).count()
    assert assigned_count == 1

def test_export_item_endpoint(client, db):
    hashed_pw = get_password_hash("123")
    admin = models.User(username="admin5", name="管理员", password_hash=hashed_pw, role="admin")
    creator = models.User(username="creator5", name="发起人", password_hash=hashed_pw, role="creator")
    other = models.User(username="other5", name="其他人", password_hash=hashed_pw, role="feedbacker")
    db.add_all([admin, creator, other])
    db.commit()

    creator_headers, _ = login_headers(client, "creator5", "123")
    admin_headers, _ = login_headers(client, "admin5", "123")
    other_headers, _ = login_headers(client, "other5", "123")

    deadline = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
    item_data = {
        "title": "导出测试任务",
        "description": "内容",
        "deadline": deadline,
        "must_feedback": True,
        "creator_id": creator.id,
        "user_ids": json.dumps([other.id]),
    }
    create_res = client.post("/api/items", data=item_data, headers=creator_headers)
    assert create_res.status_code == 200
    item_id = create_res.json()["id"]

    # 非管理员且非发起人不可导出
    deny_res = client.get(f"/api/export/item/{item_id}", headers=other_headers)
    assert deny_res.status_code == 403

    # 发起人可导出
    ok_res = client.get(f"/api/export/item/{item_id}", headers=creator_headers)
    assert ok_res.status_code == 200
    assert "item_id,title,status" in ok_res.text

    # 管理员可导出
    admin_res = client.get(f"/api/export/item/{item_id}", headers=admin_headers)
    assert admin_res.status_code == 200

def test_non_admin_scope_all_does_not_leak_others_items(client, db):
    """
    权限回归：非管理员即使显式传 scope=all，也只能看到「自己发起或自己参与」的事项，
    不能绕过前端限制查看他人事项；统计接口同理。
    """
    hashed_pw = get_password_hash("123")
    admin = models.User(username="admin_sa", name="管理员", password_hash=hashed_pw, role="admin")
    u1 = models.User(username="u1_sa", name="用户一", password_hash=hashed_pw, role="feedbacker")
    u2 = models.User(username="u2_sa", name="用户二", password_hash=hashed_pw, role="feedbacker")
    db.add_all([admin, u1, u2])
    db.commit()

    admin_headers, _ = login_headers(client, "admin_sa", "123")
    u1_headers, _ = login_headers(client, "u1_sa", "123")
    u2_headers, _ = login_headers(client, "u2_sa", "123")

    deadline = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

    # admin 创建事项 A，分配给 u1
    res = client.post("/api/items", data={
        "title": "事项A-共享给u1",
        "description": "内容",
        "deadline": deadline,
        "must_feedback": True,
        "creator_id": admin.id,
        "user_ids": json.dumps([u1.id]),
    }, headers=admin_headers)
    assert res.status_code == 200

    # u2 创建事项 C（仅 u2 自己相关），u1 不应看到
    res = client.post("/api/items", data={
        "title": "事项C-仅u2相关",
        "description": "内容",
        "deadline": deadline,
        "must_feedback": True,
        "creator_id": u2.id,
        "user_ids": json.dumps([u2.id]),
    }, headers=u2_headers)
    assert res.status_code == 200

    # u1 请求 scope=all：只能看到自己相关的事项 A，看不到 u2 的 C
    res = client.get("/api/items?scope=all&limit=100", headers=u1_headers)
    assert res.status_code == 200
    titles = [it["title"] for it in res.json()["items"]]
    assert "事项A-共享给u1" in titles
    assert "事项C-仅u2相关" not in titles

    # u1 请求统计 scope=all：total_items 不应包含 u2 的事项
    res = client.get("/api/items/stats/summary?scope=all", headers=u1_headers)
    assert res.status_code == 200
    assert res.json()["total_items"] == 1

    # 管理员仍可看到全部
    res = client.get("/api/items?scope=all&limit=100", headers=admin_headers)
    assert res.status_code == 200
    assert len(res.json()["items"]) == 2

def test_invalid_query_params_return_4xx(client, db):
    """非法日期参数应返回 4xx 而不是 500。"""
    hashed_pw = get_password_hash("123")
    user = models.User(username="param_user", name="参数用户", password_hash=hashed_pw, role="feedbacker")
    db.add(user)
    db.commit()

    headers, _ = login_headers(client, "param_user", "123")

    res = client.get("/api/items?created_from=not-a-date", headers=headers)
    assert res.status_code in (400, 422)

    deadline = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    res = client.post("/api/items", data={
        "title": "非法截止时间测试",
        "deadline": "bad-deadline",
        "must_feedback": True,
        "creator_id": user.id,
        "user_ids": json.dumps([user.id]),
    }, headers=headers)
    assert res.status_code == 400

    res = client.post("/api/items", data={
        "title": "非法参与人列表测试",
        "deadline": deadline,
        "must_feedback": True,
        "creator_id": user.id,
        "user_ids": "not-json",
    }, headers=headers)
    assert res.status_code == 400

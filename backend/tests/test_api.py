from datetime import datetime, timedelta, timezone
import bcrypt
from backend import models

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def test_api_ping(client):
    response = client.get("/api/items")
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
    login_res = client.post("/api/login", json={"username": "admin", "password": "123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. 创建事项
    # 注意：/api/items 接口接收 Form Data，而不是 JSON，因为涉及到文件上传
    # 并且 deadline 格式需要是 "%Y-%m-%d %H:%M:%S"
    deadline = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    
    # user_ids 需要作为 JSON 字符串传递
    import json
    
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
    login_res_u1 = client.post("/api/login", json={"username": "u1", "password": "123"})
    u1_id = login_res_u1.json()["user_id"]
    
    res = client.get(f"/api/todos?user_id={u1_id}")
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
    res = client.post("/api/feedbacks", json=feedback_payload)
    assert res.status_code == 200
    
    # 6. 验证状态更新
    db.refresh(iu)
    assert iu.feedback_status == "done"
    assert iu.last_feedback_time is not None

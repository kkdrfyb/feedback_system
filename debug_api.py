from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal, Base, engine
from backend import models
from datetime import datetime, timedelta, timezone
import bcrypt

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# 重置数据库
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

client = TestClient(app)
db = SessionLocal()

# 创建用户
hashed_pw = get_password_hash("123")
u1 = models.User(username="u1", name="用户1", password_hash=hashed_pw, role="feedbacker")
u2 = models.User(username="admin", name="管理", password_hash=hashed_pw, role="admin")
db.add_all([u1, u2])
db.commit()
db.refresh(u1)
db.refresh(u2)

# 登录
login_res = client.post("/api/login", json={"username": "admin", "password": "123"})
if login_res.status_code != 200:
    print(f"Login failed: {login_res.status_code}, {login_res.json()}")
    exit()

token = login_res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

deadline = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
item_payload = {
    "title": "测试任务",
    "description": "内容",
    "deadline": deadline,
    "creator_id": u2.id,
    "user_ids": [u1.id]
}

print("Sending payload:", item_payload)
res = client.post("/api/items", json=item_payload, headers=headers)
print(f"Status: {res.status_code}")
print(f"Response: {res.json()}")

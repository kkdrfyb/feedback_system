import random
from datetime import datetime, timedelta, timezone
import faker
from sqlalchemy.orm import Session
from backend.database import SessionLocal, engine, Base
from backend import models
import bcrypt

# 初始化 Faker
fake = faker.Faker('zh_CN')

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_simulation_data():
    db = SessionLocal()
    try:
        print("开始生成模拟数据...")
        
        # 1. 创建 4 个分组
        groups = ["研发部", "市场部", "运营部", "人事部"]
        group_objs = []
        # 检查是否已存在，不存在则创建
        for g_name in groups:
            # 这里我们不走 Group 模型关联，因为 User 模型直接有 group 字段
            # 但为了完整性，如果 User.group 是字符串，我们直接用字符串即可
            # User 模型定义：group = Column(String, nullable=True)
            pass

        # 2. 增加 200 个实际用户
        print("正在创建 200 个用户...")
        users = []
        # 预计算密码哈希以提高速度
        default_hash = get_password_hash("123456")
        
        # 获取当前最大的 user id 以避免 username 冲突（虽然 username 是 unique）
        # 简单起见，用随机后缀
        
        for i in range(200):
            group_name = random.choice(groups)
            username = f"user_{fake.pystr(min_chars=5, max_chars=8)}_{i}"
            user = models.User(
                username=username,
                name=fake.name(),
                password_hash=default_hash,
                role="feedbacker",
                group=group_name
            )
            users.append(user)
        
        db.add_all(users)
        db.commit()
        
        # 获取所有用户的 ID，包括刚刚创建的
        all_user_ids = [u.id for u in db.query(models.User).all()]
        # 获取管理员 ID 用于创建任务 (假设 id 1 或 2 是管理员，或者随机选一个)
        creator_id = all_user_ids[0] if all_user_ids else 1
        
        # 3. 创建 100 个任务
        print("正在创建 100 个任务...")
        items = []
        
        # 任务完成情况配置
        # 30% 完全完成
        # 40% 未完成
        # 30% 逾期未完成
        
        for i in range(100):
            rand_val = random.random()
            
            if rand_val < 0.3:
                # 完全完成
                is_finished = True
                is_overdue = False
            elif rand_val < 0.7:
                # 进行中/未完成
                is_finished = False
                is_overdue = False
            else:
                # 逾期
                is_finished = False
                is_overdue = True
            
            # 设定截止时间
            if is_overdue:
                deadline = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 10))
            else:
                deadline = datetime.now(timezone.utc) + timedelta(days=random.randint(5, 30))
            
            item = models.Item(
                title=f"模拟任务-{i+1}-{fake.sentence(nb_words=5)}",
                description=fake.text(),
                status="finished" if is_finished else "ongoing",
                must_feedback=True,
                deadline=deadline,
                creator_id=creator_id
            )
            db.add(item)
            db.flush() # 获取 item.id
            
            # 4. 分配用户 (20-50人)
            num_assignees = random.randint(20, 50)
            assignees = random.sample(all_user_ids, min(len(all_user_ids), num_assignees))
            
            item_users = []
            feedbacks = []
            
            for uid in assignees:
                feedback_status = "pending"
                last_feedback_time = None
                
                # 决定该用户是否反馈
                has_feedback = False
                if is_finished:
                    has_feedback = True
                else:
                    # 对于未完成或逾期的任务，随机部分人反馈
                    # 比如 20% - 80% 的人反馈了
                    if random.random() < random.uniform(0.2, 0.8):
                        has_feedback = True
                
                if has_feedback:
                    feedback_status = "done"
                    # 反馈时间：创建时间之后，截止时间之前（如果是正常反馈）
                    # 简单起见，反馈时间设为现在
                    last_feedback_time = datetime.now(timezone.utc)
                
                iu = models.ItemUser(
                    item_id=item.id,
                    user_id=uid,
                    feedback_status=feedback_status,
                    last_feedback_time=last_feedback_time
                )
                db.add(iu)
                db.flush() # 获取 iu.id 用于创建 Feedback
                
                if has_feedback:
                    fb = models.Feedback(
                        item_user_id=iu.id,
                        content=fake.sentence(),
                        created_at=last_feedback_time
                    )
                    feedbacks.append(fb)
            
            db.add_all(feedbacks)
        
        db.commit()
        print("模拟数据生成完成！")
        
        # 统计结果
        total_users = db.query(models.User).count()
        total_items = db.query(models.Item).count()
        total_feedbacks = db.query(models.Feedback).count()
        print(f"当前系统状态: 用户={total_users}, 任务={total_items}, 反馈={total_feedbacks}")
        
    except Exception as e:
        print(f"发生错误: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # 安装 faker 如果没有
    import sys
    import subprocess
    try:
        import faker
    except ImportError:
        print("正在安装 faker...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "faker"])
        import faker
        
    create_simulation_data()

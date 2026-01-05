import random
from datetime import datetime, timedelta, timezone
from faker import Faker
from backend.database import SessionLocal, engine, Base
from backend import models
from backend.auth import get_password_hash
from sqlalchemy import text
import sys
import time

# 初始化 Faker
fake = Faker('zh_CN')

def init_db():
    print("Initializing database...")
    Base.metadata.create_all(bind=engine)
    print("Database initialized.")

def create_users(db, target_count=1000):
    print(f"Checking users... Target: {target_count}")
    current_count = db.query(models.User).count()
    if current_count >= target_count:
        print(f"Already have {current_count} users. Skipping user creation.")
        return [u.id for u in db.query(models.User).with_entities(models.User.id).all()]

    needed = target_count - current_count
    print(f"Creating {needed} users...")
    
    groups = ["市场部", "运营部", "人事部", "研发部"]
    default_hash = get_password_hash("123456")
    
    # 批量创建用户
    batch_size = 500
    new_users = []
    
    # 获取现有最大的 ID 以避免冲突（虽然自增主键会自动处理，但为了 username 唯一性）
    # 简单起见，使用 timestamp 后缀
    
    start_time = time.time()
    
    created_ids = []
    
    for i in range(needed):
        group_name = random.choice(groups)
        username = f"user_{int(start_time)}_{i}"
        user = models.User(
            username=username,
            name=fake.name(),
            password_hash=default_hash,
            role="feedbacker",
            group=group_name
        )
        new_users.append(user)
        
        if len(new_users) >= batch_size:
            db.bulk_save_objects(new_users)
            db.commit()
            new_users = []
            print(f"Created {i + 1} / {needed} users...")

    if new_users:
        db.bulk_save_objects(new_users)
        db.commit()
    
    print("User creation completed.")
    return [u.id for u in db.query(models.User).with_entities(models.User.id).all()]

def simulate_activity(db, user_ids, days=180):
    print(f"Starting simulation for {days} days...")
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    total_items = 0
    total_feedbacks = 0
    
    for day in range(days):
        current_date = start_date + timedelta(days=day)
        print(f"Simulating Day {day + 1}/{days} ({current_date.date()})...")
        
        # 1. 每天 200 个用户创建任务
        creators = random.sample(user_ids, 200)
        items_to_create = []
        
        for creator_id in creators:
            deadline = current_date + timedelta(days=3)
            # 随机决定任务是否已经结束 (如果是过去的日期)
            # 假设 70% 任务在 3 天后结束
            # 这里我们先只设置 created_at，后面再统一更新状态
            
            item = models.Item(
                title=fake.sentence(nb_words=6),
                description=fake.text(max_nb_chars=100),
                status="ongoing", # 稍后更新
                must_feedback=True,
                deadline=deadline,
                creator_id=creator_id,
                created_at=current_date,
                attachments="[]"
            )
            items_to_create.append(item)
        
        # 批量保存 Items 以获取 IDs
        # bulk_save_objects 不会返回 IDs，所以我们需要 add_all + flush
        # 为了性能，我们分批处理，比如 200 个一次
        
        db.add_all(items_to_create)
        db.flush() # 获取 IDs
        
        # 2. 为每个任务分配 30-50 个用户
        item_users_to_create = []
        feedbacks_to_create = []
        
        for item in items_to_create:
            # 随机 30-50 人
            num_assignees = random.randint(30, 50)
            assignees = random.sample(user_ids, num_assignees)
            
            # 确定任务最终状态
            # 如果截止日期已过：
            is_past_deadline = (datetime.now(timezone.utc) > item.deadline)
            
            # 假设 80% 的任务最终会完成
            item_finished = random.random() < 0.8
            
            if is_past_deadline:
                 item.status = "finished" if item_finished else "ongoing"
            
            for user_id in assignees:
                # 决定该用户是否反馈
                # 90% 的用户会反馈
                has_feedback = random.random() < 0.9
                feedback_status = "pending"
                last_feedback_time = None
                
                if has_feedback:
                    feedback_status = "done"
                    # 反馈时间在创建后 0-3 天内
                    feedback_delay = random.uniform(0, 3) * 24 * 3600
                    feedback_time = item.created_at + timedelta(seconds=feedback_delay)
                    if feedback_time > datetime.now(timezone.utc):
                        feedback_time = datetime.now(timezone.utc)
                    last_feedback_time = feedback_time
                
                item_user = models.ItemUser(
                    item_id=item.id,
                    user_id=user_id,
                    feedback_status=feedback_status,
                    last_feedback_time=last_feedback_time
                )
                item_users_to_create.append(item_user)
        
        db.add_all(item_users_to_create)
        db.flush() # 获取 ItemUser IDs
        
        # 3. 创建 Feedback 内容
        for iu in item_users_to_create:
            if iu.feedback_status == "done":
                fb = models.Feedback(
                    item_user_id=iu.id,
                    content=fake.sentence(),
                    created_at=iu.last_feedback_time,
                    updated_at=iu.last_feedback_time
                )
                feedbacks_to_create.append(fb)
        
        if feedbacks_to_create:
            db.bulk_save_objects(feedbacks_to_create)
            
        db.commit()
        
        total_items += len(items_to_create)
        total_feedbacks += len(feedbacks_to_create)
        
        # 清理 session 以释放内存
        db.expire_all()

    print(f"Simulation completed. Total Items: {total_items}, Total Feedbacks: {total_feedbacks}")

def main():
    db = SessionLocal()
    try:
        init_db()
        user_ids = create_users(db, target_count=1000)
        simulate_activity(db, user_ids, days=180)
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()

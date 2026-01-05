import sys
import os
from datetime import datetime, timezone

# 添加后端目录到路径以便导入项目模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from database import SessionLocal, engine, Base
    import models
    from auth import get_password_hash
except ImportError:
    from .database import SessionLocal, engine, Base
    from . import models
    from .auth import get_password_hash

def init_users():
    print("正在初始化数据库表...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 检查是否已存在大量用户
        count = db.query(models.User).count()
        if count >= 300:
            print(f"数据库中已有 {count} 个用户，跳过初始化。")
            return

        print(f"正在生成 300 个用户 (当前已有 {count} 个)...")
        
        # 1. 创建管理员 (如果不存在)
        admin = db.query(models.User).filter_by(username="admin").first()
        if not admin:
            admin = models.User(
                username="admin",
                name="超级管理员",
                password_hash=get_password_hash("123"),
                role="admin",
                group="管理部"
            )
            db.add(admin)

        # 2. 批量创建普通用户
        batch_size = 50
        for i in range(1, 301 - count):
            username = f"user{i:03d}"
            # 避免重复
            if db.query(models.User).filter_by(username=username).first():
                continue
                
            user = models.User(
                username=username,
                name=f"员工{i:03d}",
                password_hash=get_password_hash("admin"),
                role="feedbacker",
                group=f"小组{ (i // 50) + 1 }"
            )
            db.add(user)
            
            if i % batch_size == 0:
                db.commit()
                print(f"已创建 {i + count} 个用户...")
        
        db.commit()
        print("初始化完成！共计 300 个测试用户已就绪。所有初始密码均为: 123")

    finally:
        db.close()

if __name__ == "__main__":
    init_users()

import sys
import os

# 添加后端目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from database import SessionLocal, engine, Base
    import models
    from auth import get_password_hash
except ImportError:
    from .database import SessionLocal, engine, Base
    from . import models
    from .auth import get_password_hash

def reset_and_init_admin():
    print("注意：正在重置所有数据（保留管理员）...")
    db = SessionLocal()
    try:
        # 1. 清理大部分表
        # 注意逻辑顺序，由于有外键约束，建议直接删除并重新创建表，或者按顺序 delete
        # 这里为了彻底清理，我们采用 recreate 方式
        print("正在重建数据库表结构...")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        
        # 2. 创建管理员
        print("正在创建默认管理员 admin/admin ...")
        admin = models.User(
            username="admin",
            name="超级管理员",
            password_hash=get_password_hash("admin"),
            role="admin",
            group="管理部"
        )
        db.add(admin)
        db.commit()
        print("重置成功！当前仅存 admin 账号。")
    except Exception as e:
        print(f"发生错误: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_and_init_admin()

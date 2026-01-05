import csv
import sys
import os
from datetime import datetime, timezone

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

# 在import_from_csv函数开头添加
print("脚本连接的数据库：", engine.url)

def import_from_csv(file_path):
    if not os.path.exists(file_path):
        print(f"错误: 找不到文件 {file_path}")
        return

    print(f"正在从 {file_path} 导入用户...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        with open(file_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            success_count = 0
            skip_count = 0
            print("csv解析到的表头",reader.fieldnames)
            
            for row in reader:
                username = row.get('username')
                print("当前数据",row)
                if not username:
                    print(f'跳过{row}，因为username为空')
                    continue
                
                # 检查重复
                if db.query(models.User).filter_by(username=username).first():
                    skip_count += 1
                    continue
                
                user = models.User(
                    username=username,
                    name=row.get('name', username),
                    password_hash=get_password_hash(row.get('password', '123')),
                    role=row.get('role', 'feedbacker'),
                    group=row.get('group', '')
                )
                db.add(user)
                success_count += 1
                
                if success_count % 50 == 0:
                    db.commit()
                    print(f"已处理 {success_count} 个...")

            db.commit()
            print(f"导入完成！成功: {success_count}, 跳过(已存在): {skip_count}")

    except Exception as e:
        print(f"发生错误: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    target_file = sys.argv[1] if len(sys.argv) > 1 else "users_template.csv"
    import_from_csv(target_file)

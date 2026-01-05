from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import csv
import io
try:
    from ..database import get_db
    from .. import models, schemas
    from ..auth import get_password_hash
except (ImportError, ValueError):
    from database import get_db
    import models, schemas
    from auth import get_password_hash

router = APIRouter(tags=["groups"])

@router.post("/groups/sync_org")
def sync_org_groups(db: Session = Depends(get_db)):
    names = [n for (n,) in db.query(models.User.group).distinct().all() if n]
    created = 0
    for name in names:
        g = db.query(models.Group).filter(models.Group.name == name).first()
        if not g:
            g = models.Group(name=name, is_org=True)
            db.add(g)
            db.flush()
            created += 1
        users = db.query(models.User).filter(models.User.group == name).all()
        g.users = users
    db.commit()
    return {"created": created, "total_org_groups": db.query(models.Group).filter(models.Group.is_org == True).count()}

@router.post("/groups/import")
async def import_groups(
    file: UploadFile = File(...),
    owner_id: int = None,
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    content = await file.read()
    decoded = content.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(decoded))
    
    stats = {"groups_created": 0, "users_created": 0, "rows_processed": 0}
    
    # 辅助缓存
    group_cache = {} # name -> model
    
    for row in reader:
        stats["rows_processed"] += 1
        username = row.get('username')
        user_name = row.get('name', username)
        password = row.get('password', 'admin') # 默认密码改为 admin
        role = row.get('role', 'feedbacker')
        group_name = row.get('group') or row.get('group_name')
        
        if not username or not group_name:
            continue
            
        # 1. 获取或创建分组
        if group_name not in group_cache:
            db_group = db.query(models.Group).filter(models.Group.name == group_name).first()
            if not db_group:
                db_group = models.Group(
                    name=group_name,
                    is_org=True,
                    owner_id=owner_id
                )
                db.add(db_group)
                db.flush()
                stats["groups_created"] += 1
            group_cache[group_name] = db_group
        else:
            db_group = group_cache[group_name]
            
        # 2. 获取或创建用户
        db_user = db.query(models.User).filter(models.User.username == username).first()
        if not db_user:
            db_user = models.User(
                username=username,
                name=user_name,
                password_hash=get_password_hash(password),
                role=role,
                group=group_name
            )
            db.add(db_user)
            db.flush()
            stats["users_created"] += 1
            
        # 3. 关联用户到分组
        if db_user not in db_group.users:
            db_group.users.append(db_user)
            
    db.commit()
    return stats

@router.get("/groups", response_model=List[schemas.Group])
def get_groups(user_id: int, role: str, db: Session = Depends(get_db)):
    if role == "admin":
        groups = db.query(models.Group).all()
    else:
        # 职员可以看到公开组（is_org=True）和自己拥有的组
        groups = db.query(models.Group).filter(
            (models.Group.is_org == True) | (models.Group.owner_id == user_id)
        ).all()
    
    # 填充 user_ids
    result = []
    for g in groups:
        g_data = schemas.Group.model_validate(g)
        g_data.user_ids = [u.id for u in g.users]
        result.append(g_data)
    return result

@router.post("/groups", response_model=schemas.Group)
def create_group(group: schemas.GroupCreate, owner_id: int, role: str, db: Session = Depends(get_db)):
    # 权限检查：非管理员不能创建公开组
    if not role == "admin" and group.is_org:
        group.is_org = False
        
    db_group = models.Group(
        name=group.name,
        description=group.description,
        is_org=group.is_org,
        owner_id=owner_id
    )
    
    if group.user_ids:
        users = db.query(models.User).filter(models.User.id.in_(group.user_ids)).all()
        db_group.users = users
        
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    
    res = schemas.Group.model_validate(db_group)
    res.user_ids = [u.id for u in db_group.users]
    return res

@router.put("/groups/{group_id}", response_model=schemas.Group)
def update_group(group_id: int, group: schemas.GroupUpdate, user_id: int, role: str, db: Session = Depends(get_db)):
    db_group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not db_group:
        raise HTTPException(status_code=404, detail="Group not found")
        
    # 权限检查
    if role != "admin" and db_group.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this group")
        
    if group.name is not None: db_group.name = group.name
    if group.description is not None: db_group.description = group.description
    if role == "admin" and group.is_org is not None: db_group.is_org = group.is_org
    
    if group.user_ids is not None:
        users = db.query(models.User).filter(models.User.id.in_(group.user_ids)).all()
        db_group.users = users
        
    db.commit()
    db.refresh(db_group)
    
    res = schemas.Group.model_validate(db_group)
    res.user_ids = [u.id for u in db_group.users]
    return res

@router.delete("/groups/{group_id}")
def delete_group(group_id: int, user_id: int, role: str, db: Session = Depends(get_db)):
    db_group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not db_group:
        raise HTTPException(status_code=404, detail="Group not found")
        
    # 权限检查
    if role != "admin" and db_group.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this group")
        
    db.delete(db_group)
    db.commit()
    return {"message": "Group deleted"}

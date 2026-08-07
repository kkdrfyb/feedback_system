from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
import bcrypt
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
import os
import csv
import io
from fastapi.responses import StreamingResponse
try:
    from .database import get_db
    from . import models, schemas
except (ImportError, ValueError):
    from database import get_db
    import models, schemas

# Use env in deployments; keep a local fallback for dev convenience.
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def authenticate_user(db: Session, username: str, password: str):
    user = db.query(models.User).filter(models.User.username==username).first()
    if not user: return False
    if not verify_password(password, user.password_hash): return False
    return user

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_admin(current_user: models.User):
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privilege required")

@router.post("/login")
def login(login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = jwt.encode({"sub": user.username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)
    log = models.OperationLog(user_id=user.id, action="Login", target_id=str(user.id))
    db.add(log); db.commit()
    return {"access_token": token, "token_type": "bearer", "role": user.role, "user_id": user.id, "name": user.name}

@router.get("/users", response_model=list[schemas.User])
def list_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    require_admin(current_user)
    return db.query(models.User).all()

@router.get("/users/assignable", response_model=list[schemas.User])
def list_assignable_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """供事项参与人和私有分组成员选择使用，不授予用户管理权限。"""
    return db.query(models.User).order_by(models.User.name, models.User.id).all()

@router.post("/users", response_model=schemas.User)
def create_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    require_admin(current_user)
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(user.password)
    new_user = models.User(
        username=user.username,
        name=user.name,
        password_hash=hashed_password,
        role=user.role,
        group=user.group
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    require_admin(current_user)
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete current login user")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    has_created_items = db.query(models.Item).filter(models.Item.creator_id == user_id).first()
    if has_created_items:
        raise HTTPException(status_code=400, detail="User owns items; transfer/delete items first")

    has_assignments = db.query(models.ItemUser).filter(models.ItemUser.user_id == user_id).first()
    if has_assignments:
        raise HTTPException(status_code=400, detail="User has item assignments; clear assignments first")

    # Drop group memberships before deleting user.
    db.execute(models.group_users.delete().where(models.group_users.c.user_id == user_id))
    db.delete(user)
    db.commit()
    return {"detail": "User deleted"}

@router.get("/users/export")
def export_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    require_admin(current_user)

    users = db.query(models.User).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Username", "Name", "Role", "Group"])

    for user in users:
        writer.writerow([
            user.id,
            user.username,
            user.name,
            user.role,
            user.group, 
        ])

    output.seek(0)

    response = StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv"
    )
    response.headers["Content-Disposition"] = "attachment; filename=users_export.csv"
    return response

@router.get("/operation_logs")
def get_operation_logs(
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    require_admin(current_user)

    from sqlalchemy import desc
    logs = db.query(models.OperationLog, models.User)\
        .join(models.User, models.OperationLog.user_id == models.User.id)\
        .order_by(desc(models.OperationLog.timestamp)).limit(limit).all()
    result = []
    for log, user in logs:
        result.append({
            "timestamp": log.timestamp,
            "user_name": user.name,
            "action": log.action,
            "target_id": log.target_id
        })
    return result

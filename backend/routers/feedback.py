from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
try:
    from .. import models, schemas
    from ..database import get_db
    from ..auth import get_current_user
except (ImportError, ValueError):
    import models, schemas
    from database import get_db
    from auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])

@router.get("/items/{item_id}/feedbacks")
def get_item_feedbacks(item_id: int, db: Session = Depends(get_db)):
    results = db.query(models.ItemUser, models.User, models.Feedback)\
        .join(models.User, models.ItemUser.user_id == models.User.id)\
        .outerjoin(models.Feedback, models.Feedback.item_user_id == models.ItemUser.id)\
        .filter(models.ItemUser.item_id == item_id)\
        .all()
    feedbacks = []
    for iu, user, fb in results:
        feedbacks.append({
            "item_user_id": iu.id,
            "user_id": user.id,
            "user_name": user.name,
            "content": fb.content if fb else None,
            "status": iu.feedback_status,
            "last_feedback_time": iu.last_feedback_time,
            "created_at": fb.created_at if fb else None,
            "updated_at": fb.updated_at if fb else None
        })
    return {"item_id": item_id, "feedbacks": feedbacks}

@router.post("/items/{item_id}/feedbacks", response_model=schemas.Feedback)
def create_item_feedback(
    item_id: int,
    payload: schemas.FeedbackForItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    user_id = payload.user_id or current_user.id
    item_user = db.query(models.ItemUser)\
        .filter(models.ItemUser.item_id == item_id, models.ItemUser.user_id == user_id)\
        .first()
    if not item_user:
        raise HTTPException(status_code=404, detail="Item assignment not found")
    feedback = schemas.FeedbackCreate(item_user_id=item_user.id, content=payload.content)
    return create_feedback(feedback, db)

@router.get("/feedbacks", response_model=List[schemas.Feedback])
def get_feedbacks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # 反馈列表简单分页
    return db.query(models.Feedback).offset(skip).limit(limit).all()

@router.post("/feedbacks", response_model=schemas.Feedback)
def create_feedback(feedback: schemas.FeedbackCreate, db: Session = Depends(get_db)):
    """
    提交反馈
    逻辑：
    1. 创建 Feedback 记录
    2. 更新 ItemUser 状态为 'done'
    3. [自动完成检测]: 检查该事项下是否所有 Assigned Users 都已反馈，若是，则将 Item.status 更新为 'finished'
    """
    db_feedback = models.Feedback(**feedback.model_dump())
    db.add(db_feedback)
    # 更新 ItemUser 状态
    item_user = db.query(models.ItemUser).filter(models.ItemUser.id == feedback.item_user_id).first()
    if item_user:
        item_user.feedback_status = "done"
        item_user.last_feedback_time = datetime.now(timezone.utc)
        
        # Check if all users have finished feedback for this item
        item_id = item_user.item_id
        all_item_users = db.query(models.ItemUser).filter(models.ItemUser.item_id == item_id).all()
        if all(u.feedback_status == "done" for u in all_item_users):
            item = db.query(models.Item).filter(models.Item.id == item_id).first()
            if item:
                item.status = "finished"

    db.commit()
    db.refresh(db_feedback)
    return db_feedback

@router.put("/feedbacks/{feedback_id}", response_model=schemas.Feedback)
def update_feedback(feedback_id: int, payload: schemas.FeedbackBase, db: Session = Depends(get_db)):
    db_feedback = db.query(models.Feedback).filter(models.Feedback.id == feedback_id).first()
    if not db_feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    db_feedback.content = payload.content
    db_feedback.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback

@router.get("/todos", response_model=List[schemas.TodoItem])
def get_todos(
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 获取待办事项并附带 item_user_id
    target_user_id = user_id or current_user.id
    item_users = db.query(models.ItemUser).filter(
        models.ItemUser.user_id == target_user_id,
        models.ItemUser.feedback_status == "pending"
    ).all()
    results = []
    for iu in item_users:
        item = db.query(models.Item).filter(models.Item.id == iu.item_id).first()
        if item:
            # 转换为 TodoItem，并注入 item_user_id
            todo_data = schemas.Item.model_validate(item).model_dump()
            todo_data["item_user_id"] = iu.id
            todo = schemas.TodoItem(**todo_data)
            results.append(todo)
    return results

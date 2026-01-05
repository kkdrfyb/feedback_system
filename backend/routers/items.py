from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import os
import shutil
try:
    from .. import models, schemas
    from ..database import get_db
except (ImportError, ValueError):
    import models, schemas
    from database import get_db

router = APIRouter()

"""
Items Router
处理事项相关的核心业务逻辑：
- 列表查询与详情获取
- 事项创建（包含文件上传）
- 统计数据聚合 (Dashboard & Stats)
"""

@router.get("/items", response_model=schemas.PaginatedItems)
def read_items(
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    scope: str = "all",
    user_id: Optional[int] = None,
    role: Optional[str] = None,
    creator_id: Optional[int] = None,
    creator_name: Optional[str] = None,
    participant_id: Optional[int] = None,
    participant_name: Optional[str] = None,
    title_like: Optional[str] = None,
    status: Optional[str] = None,
    created_from: Optional[str] = None,
    created_to: Optional[str] = None,
    deadline_from: Optional[str] = None,
    deadline_to: Optional[str] = None,
    db: Session = Depends(get_db)
):
    # 作用域过滤与综合搜索
    # - scope: all | mine_created | mine_assigned
    # - 支持发起人/参与人（ID 或名称模糊）、标题、状态、发起/截止日期范围
    # - 服务端分页与排序（title/created_at/deadline/status）
    query = db.query(models.Item)
    if role != "admin":
        if scope == "mine_created" and user_id is not None:
            query = query.filter(models.Item.creator_id == user_id)
        elif scope == "mine_assigned" and user_id is not None:
            subq = db.query(models.ItemUser.item_id).filter(models.ItemUser.user_id == user_id).subquery()
            query = query.filter(models.Item.id.in_(subq))
    else:
        if scope == "mine_created" and user_id is not None:
            query = query.filter(models.Item.creator_id == user_id)
        elif scope == "mine_assigned" and user_id is not None:
            subq = db.query(models.ItemUser.item_id).filter(models.ItemUser.user_id == user_id).subquery()
            query = query.filter(models.Item.id.in_(subq))
    if creator_id is not None:
        query = query.filter(models.Item.creator_id == creator_id)
    if creator_name:
        ids = [u.id for u in db.query(models.User).filter(models.User.name.like(f"%{creator_name}%")).all()]
        if ids:
            query = query.filter(models.Item.creator_id.in_(ids))
        else:
            query = query.filter(models.Item.creator_id == -1)
    if participant_id is not None:
        subq = db.query(models.ItemUser.item_id).filter(models.ItemUser.user_id == participant_id).subquery()
        query = query.filter(models.Item.id.in_(subq))
    if participant_name:
        ids = [u.id for u in db.query(models.User).filter(models.User.name.like(f"%{participant_name}%")).all()]
        if ids:
            subq = db.query(models.ItemUser.item_id).filter(models.ItemUser.user_id.in_(ids)).subquery()
            query = query.filter(models.Item.id.in_(subq))
        else:
            query = query.filter(models.Item.id == -1)
    if title_like:
        query = query.filter(models.Item.title.like(f"%{title_like}%"))
    if status:
        query = query.filter(models.Item.status == status)
    from datetime import datetime
    if created_from:
        dt = datetime.strptime(created_from, "%Y-%m-%d")
        query = query.filter(models.Item.created_at >= dt)
    if created_to:
        dt = datetime.strptime(created_to, "%Y-%m-%d")
        query = query.filter(models.Item.created_at <= dt)
    if deadline_from:
        dt = datetime.strptime(deadline_from, "%Y-%m-%d")
        query = query.filter(models.Item.deadline >= dt)
    if deadline_to:
        dt = datetime.strptime(deadline_to, "%Y-%m-%d")
        query = query.filter(models.Item.deadline <= dt)
    # 统计总数用于分页 total
    total = query.count()
    if sort_by == "title":
        if sort_order == "asc":
            query = query.order_by(models.Item.title.asc())
        else:
            query = query.order_by(models.Item.title.desc())
    elif sort_by == "deadline":
        if sort_order == "asc":
            query = query.order_by(models.Item.deadline.asc())
        else:
            query = query.order_by(models.Item.deadline.desc())
    elif sort_by == "status":
        if sort_order == "asc":
            query = query.order_by(models.Item.status.asc())
        else:
            query = query.order_by(models.Item.status.desc())
    else:
        if sort_order == "asc":
            query = query.order_by(models.Item.created_at.asc())
        else:
            query = query.order_by(models.Item.created_at.desc())
    # 分页查询
    items = query.offset(skip).limit(limit).all()
    return {"items": items, "total": total}

@router.get("/items/{item_id}")
def read_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    # Get all participants (ItemUser) + User info + Feedback content (if any)
    results = db.query(models.ItemUser, models.User, models.Feedback)\
        .join(models.User, models.ItemUser.user_id == models.User.id)\
        .outerjoin(models.Feedback, models.Feedback.item_user_id == models.ItemUser.id)\
        .filter(models.ItemUser.item_id == item_id)\
        .all()
        
    participants = []
    for iu, user, fb in results:
        participants.append({
            "user_id": user.id,
            "user_name": user.name,
            "status": iu.feedback_status,
            "content": fb.content if fb else None,
            "last_feedback_time": iu.last_feedback_time,
            "created_at": fb.created_at if fb else None # Also return feedback creation time
        })
        
    return {"item": item, "feedbacks": participants}

@router.post("/items", response_model=schemas.Item)
async def create_item(
    title: str = Form(...),
    description: str = Form(None),
    deadline: str = Form(...),
    must_feedback: bool = Form(True),
    creator_id: int = Form(...),
    user_ids: str = Form(...), 
    files: List[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    # 处理文件上传
    attachment_list = []
    if files:
        for file in files:
            if not file.filename: continue
            file_path = f"uploads/{file.filename}"
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            attachment_list.append({"name": file.filename, "path": f"/api/{file_path}"})
    
    # 解析 user_ids
    u_ids = json.loads(user_ids)
    
    db_item = models.Item(
        title=title,
        description=description,
        deadline=models.datetime.strptime(deadline, "%Y-%m-%d %H:%M:%S"),
        must_feedback=must_feedback,
        creator_id=creator_id,
        status="ongoing",
        attachments=json.dumps(attachment_list) if attachment_list else None
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    
    for uid in u_ids:
        db_item_user = models.ItemUser(item_id=db_item.id, user_id=uid)
        db.add(db_item_user)
    db.commit()
    db.add(models.OperationLog(user_id=creator_id, action="Create Item", target_id=str(db_item.id))); db.commit()
    return db_item

@router.put("/items/{item_id}", response_model=schemas.Item)
def update_item(item_id: int, item: schemas.ItemCreate, db: Session = Depends(get_db)):
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    for key, value in item.model_dump(exclude={'user_ids'}).items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    iu_ids = [iu.id for iu in db.query(models.ItemUser.id).filter(models.ItemUser.item_id == item_id).all()]
    if iu_ids:
        db.query(models.Feedback).filter(models.Feedback.item_user_id.in_(iu_ids)).delete(synchronize_session=False)
    db.query(models.ItemUser).filter(models.ItemUser.item_id == item_id).delete(synchronize_session=False)
    db.query(models.Item).filter(models.Item.id == item_id).delete()
    db.commit()
    db.add(models.OperationLog(user_id=db_item.creator_id, action="Delete Item", target_id=str(item_id))); db.commit()
    return {"detail": "Item deleted"}

@router.get("/items/stats/summary")
def get_stats_summary(
    scope: str = "all",
    user_id: Optional[int] = None,
    role: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取统计概览数据
    包含：
    1. 基础计数 (Total Items, Feedbacks)
    2. 总体响应率 (Completion Rate)
    3. 近期事项反馈率对比 (Top 7) - 用于 DataStats 图表
    4. 部门/分组响应速率排行 - 用于 DataStats 排行榜
    说明：
    - 为兼容历史数据，ItemUser.feedback_status 同时接受 "done" 与 "completed" 表示已反馈
    - 所有聚合在 SQL 层完成，保证大数据下的性能
    """
    base_query = db.query(models.Item)
    if role != "admin":
        if scope == "mine_created" and user_id is not None:
            base_query = base_query.filter(models.Item.creator_id == user_id)
        elif scope == "mine_assigned" and user_id is not None:
            subq = db.query(models.ItemUser.item_id).filter(models.ItemUser.user_id == user_id).subquery()
            base_query = base_query.filter(models.Item.id.in_(subq))
    else:
        if scope == "mine_created" and user_id is not None:
            base_query = base_query.filter(models.Item.creator_id == user_id)
        elif scope == "mine_assigned" and user_id is not None:
            subq = db.query(models.ItemUser.item_id).filter(models.ItemUser.user_id == user_id).subquery()
            base_query = base_query.filter(models.Item.id.in_(subq))
    total_items = base_query.count()
    
    # Total Feedbacks (Completed)
    # Join ItemUser where feedback_status = 'done'
    # Actually Feedback table stores content, ItemUser stores status.
    # Let's count Feedback rows for "Total Feedback Count" (responses)
    from sqlalchemy import func, case
    items_subq = base_query.with_entities(models.Item.id).subquery()
    # 总反馈条数（仅限当前作用域内的事项）
    total_feedback_count = db.query(models.Feedback)\
        .join(models.ItemUser, models.Feedback.item_user_id == models.ItemUser.id)\
        .filter(models.ItemUser.item_id.in_(items_subq)).count()
    total_assignments = db.query(models.ItemUser).filter(models.ItemUser.item_id.in_(items_subq)).count()
    completed_assignments = db.query(models.ItemUser).filter(
        models.ItemUser.item_id.in_(items_subq),
        models.ItemUser.feedback_status.in_(["done", "completed"])
    ).count()
    completion_rate = 0
    if total_assignments > 0:
        completion_rate = int((completed_assignments / total_assignments) * 100)
    # 最近事项（作用域内 TOP 7）
    recent_items = base_query.order_by(models.Item.created_at.desc()).limit(7).all()
    item_comparison = []
    for item in recent_items:
        # Count feedbacks
        i_total = db.query(models.ItemUser).filter(models.ItemUser.item_id == item.id).count()
        i_done = db.query(models.ItemUser).filter(
            models.ItemUser.item_id == item.id, 
            models.ItemUser.feedback_status.in_(["done", "completed"])
        ).count()
        # Calculate percentage
        rate = 0
        if i_total > 0:
            rate = int((i_done / i_total) * 100)
        item_comparison.append({
            "id": item.id,
            "title": item.title,
            "rate": rate,
            "total": i_total,
            "done": i_done
        })
        
    # 2. Department Response Rate Ranking
    # Group by User.group
    # Optimized using SQL Group By
    stmt = db.query(
        models.User.group,
        func.count(models.ItemUser.id).label("total"),
        func.sum(
            case(
                (models.ItemUser.feedback_status.in_(["done", "completed"]), 1), 
                else_=0
            )
        ).label("done_count")
    ).join(models.User, models.ItemUser.user_id == models.User.id)\
    .filter(models.ItemUser.item_id.in_(items_subq))\
    .group_by(models.User.group).all()
    
    dept_ranking = []
    for group_name, total, done_count in stmt:
        if not group_name:
            group_name = "未分组"
        
        # Ensure done_count is int (might be None if no rows)
        if done_count is None: done_count = 0
        
        rate = 0
        if total > 0:
            rate = int((done_count / total) * 100)
            
        dept_ranking.append({
            "name": group_name,
            "rate": rate,
            "total": total,
            "done": done_count
        })
    
    # Sort decl ranking by rate desc
    dept_ranking.sort(key=lambda x: x['rate'], reverse=True)

    return {
        "total_items": total_items,
        "total_feedbacks": total_feedback_count, # Number of feedback entries
        "completion_rate": f"{completion_rate}%",
        "item_comparison": item_comparison, # New field
        "dept_ranking": dept_ranking # New field
    }

@router.get("/items/export/excel")
def export_items_csv(db: Session = Depends(get_db)):
    # This endpoint was missing but referenced in client check
    # But wait, client implements export locally now. 
    # Just in case, let's leave it or remove if unused. 
    # The user asked for "Export User List" which is handled client side now. 
    # The previous "Export Excel" on Stats page was client side too. 
    # So this might not be needed, but good to have if client fails.
    pass

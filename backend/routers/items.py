from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import or_, select
from typing import List, Optional
from datetime import datetime, date, time
import json
import os
import shutil
import re
import uuid
import csv
import io
from fastapi.responses import StreamingResponse
try:
    from .. import models, schemas
    from ..database import get_db
    from ..auth import get_current_user
    from ..enums import ItemStatus, FeedbackStatus
except (ImportError, ValueError):
    import models, schemas
    from database import get_db
    from auth import get_current_user
    from enums import ItemStatus, FeedbackStatus

router = APIRouter(dependencies=[Depends(get_current_user)])
SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]")
# 统一上传目录（项目根目录 uploads/），不随启动目录变化
UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "uploads"))

"""
Items Router
处理事项相关的核心业务逻辑：
- 列表查询与详情获取
- 事项创建（包含文件上传）
- 统计数据聚合 (Dashboard & Stats)
"""

def _sanitize_filename(filename: str) -> str:
    name = os.path.basename(filename or "").strip()
    if not name:
        name = "file"
    safe = SAFE_FILENAME_RE.sub("_", name)
    return safe[:128]

def _can_view_item(db: Session, item_id: int, current_user: models.User) -> bool:
    if current_user.role == "admin":
        return True
    is_creator = db.query(models.Item).filter(
        models.Item.id == item_id,
        models.Item.creator_id == current_user.id
    ).first()
    if is_creator:
        return True
    is_participant = db.query(models.ItemUser).filter(
        models.ItemUser.item_id == item_id,
        models.ItemUser.user_id == current_user.id
    ).first()
    return bool(is_participant)

def _apply_scope_filter(query, scope: str, user_id: int, is_admin: bool):
    """
    服务端强制作用域过滤（授权边界，不信任前端传入的 scope）：
    - mine_created: 我发起的事项
    - mine_assigned: 我参与的事项
    - 其他（含 all）:
        - admin 不过滤（全量）
        - 非 admin 仅返回「我发起或我参与」的事项，防止通过 scope=all 越权查看他人事项
    """
    if scope == "mine_created":
        return query.filter(models.Item.creator_id == user_id)
    if scope == "mine_assigned":
        subq = select(models.ItemUser.item_id).where(
            models.ItemUser.user_id == user_id
        )
        return query.filter(models.Item.id.in_(subq))
    if not is_admin:
        subq = select(models.ItemUser.item_id).where(
            models.ItemUser.user_id == user_id
        )
        return query.filter(
            or_(models.Item.creator_id == user_id, models.Item.id.in_(subq))
        )
    return query

@router.get("/items", response_model=schemas.PaginatedItems)
def read_items(
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    scope: str = "all",
    creator_id: Optional[int] = None,
    creator_name: Optional[str] = None,
    participant_id: Optional[int] = None,
    participant_name: Optional[str] = None,
    title_like: Optional[str] = None,
    status: Optional[str] = None,
    created_from: Optional[date] = None,
    created_to: Optional[date] = None,
    deadline_from: Optional[date] = None,
    deadline_to: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # 作用域过滤与综合搜索
    # - scope: all | mine_created | mine_assigned
    # - 支持发起人/参与人（ID 或名称模糊）、标题、状态、发起/截止日期范围
    # - 服务端分页与排序（title/created_at/deadline/status）
    # - 非管理员强制限定在「我发起或我参与」范围内，scope=all 不会越权
    query = db.query(models.Item)
    query = _apply_scope_filter(
        query, scope, current_user.id, current_user.role == "admin"
    )
    if creator_id is not None:
        query = query.filter(models.Item.creator_id == creator_id)
    if creator_name:
        ids = [u.id for u in db.query(models.User).filter(models.User.name.like(f"%{creator_name}%")).all()]
        if ids:
            query = query.filter(models.Item.creator_id.in_(ids))
        else:
            query = query.filter(models.Item.creator_id == -1)
    if participant_id is not None:
        subq = select(models.ItemUser.item_id).where(
            models.ItemUser.user_id == participant_id
        )
        query = query.filter(models.Item.id.in_(subq))
    if participant_name:
        ids = [u.id for u in db.query(models.User).filter(models.User.name.like(f"%{participant_name}%")).all()]
        if ids:
            subq = select(models.ItemUser.item_id).where(
                models.ItemUser.user_id.in_(ids)
            )
            query = query.filter(models.Item.id.in_(subq))
        else:
            query = query.filter(models.Item.id == -1)
    if title_like:
        query = query.filter(models.Item.title.like(f"%{title_like}%"))
    if status:
        query = query.filter(models.Item.status == status)
    if created_from:
        query = query.filter(models.Item.created_at >= datetime.combine(created_from, time.min))
    if created_to:
        query = query.filter(models.Item.created_at <= datetime.combine(created_to, time.max))
    if deadline_from:
        query = query.filter(models.Item.deadline >= datetime.combine(deadline_from, time.min))
    if deadline_to:
        query = query.filter(models.Item.deadline <= datetime.combine(deadline_to, time.max))
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
def read_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not _can_view_item(db, item_id, current_user):
        raise HTTPException(status_code=403, detail="Not authorized to view this item")
        
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
        
    item_data = schemas.Item.model_validate(item).model_dump()
    return {"item": item_data, "feedbacks": participants}

@router.post("/items", response_model=schemas.Item)
async def create_item(
    title: str = Form(...),
    description: str = Form(None),
    deadline: str = Form(...),
    must_feedback: bool = Form(True),
    creator_id: int = Form(...),
    user_ids: str = Form(...), 
    files: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "admin":
        creator_id = current_user.id
    elif creator_id is None:
        creator_id = current_user.id

    if current_user.role != "admin" and creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to create item for other users")
    # 处理文件上传
    attachment_list = []
    if files:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        for file in files:
            if not file.filename: continue
            safe_name = _sanitize_filename(file.filename)
            stored_name = f"{uuid.uuid4().hex}_{safe_name}"
            file_path = os.path.join(UPLOAD_DIR, stored_name)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            attachment_list.append({"name": safe_name, "path": f"/uploads/{stored_name}"})
    
    # 解析 user_ids
    try:
        u_ids = json.loads(user_ids)
        u_ids = sorted(set(int(uid) for uid in u_ids))
    except (ValueError, TypeError, json.JSONDecodeError):
        raise HTTPException(status_code=400, detail="user_ids 格式错误，应为 JSON 数组")
    
    try:
        deadline_dt = datetime.strptime(deadline, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise HTTPException(status_code=400, detail="deadline 格式错误，应为 YYYY-MM-DD HH:MM:SS")
    
    db_item = models.Item(
        title=title,
        description=description,
        deadline=deadline_dt,
        must_feedback=must_feedback,
        creator_id=creator_id,
        status=ItemStatus.ongoing.value,
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
def update_item(
    item_id: int,
    item: schemas.ItemUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    if current_user.role != "admin" and db_item.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this item")

    update_data = item.model_dump(exclude_unset=True, exclude={"user_ids"})
    if "attachments" in update_data:
        update_data["attachments"] = json.dumps(update_data["attachments"]) if update_data["attachments"] else None
    for key, value in update_data.items():
        setattr(db_item, key, value)
    if item.user_ids is not None:
        existing = db.query(models.ItemUser).filter(models.ItemUser.item_id == item_id).all()
        existing_user_ids = {iu.user_id for iu in existing}
        new_user_ids = set(item.user_ids)
        to_add = new_user_ids - existing_user_ids
        to_remove = existing_user_ids - new_user_ids

        for user_id in to_add:
            db.add(models.ItemUser(item_id=item_id, user_id=user_id))

        if to_remove:
            remove_item_users = db.query(models.ItemUser).filter(
                models.ItemUser.item_id == item_id,
                models.ItemUser.user_id.in_(to_remove)
            ).all()
            remove_ids = [iu.id for iu in remove_item_users]
            if remove_ids:
                db.query(models.Feedback).filter(
                    models.Feedback.item_user_id.in_(remove_ids)
                ).delete(synchronize_session=False)
                db.query(models.ItemUser).filter(
                    models.ItemUser.id.in_(remove_ids)
                ).delete(synchronize_session=False)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/items/{item_id}")
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    if current_user.role != "admin" and db_item.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this item")

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
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
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
    base_query = _apply_scope_filter(
        base_query, scope, current_user.id, current_user.role == "admin"
    )
    total_items = base_query.count()
    
    # Total Feedbacks (Completed)
    # Join ItemUser where feedback_status = 'done'
    # Actually Feedback table stores content, ItemUser stores status.
    # Let's count Feedback rows for "Total Feedback Count" (responses)
    from sqlalchemy import func, case
    items_subq = base_query.with_entities(models.Item.id).subquery()
    items_id_select = select(items_subq.c.id)
    # 总反馈条数（仅限当前作用域内的事项）
    total_feedback_count = db.query(models.Feedback)\
        .join(models.ItemUser, models.Feedback.item_user_id == models.ItemUser.id)\
        .filter(models.ItemUser.item_id.in_(items_id_select)).count()
    total_assignments = db.query(models.ItemUser).filter(models.ItemUser.item_id.in_(items_id_select)).count()
    completed_assignments = db.query(models.ItemUser).filter(
        models.ItemUser.item_id.in_(items_id_select),
        models.ItemUser.feedback_status.in_([FeedbackStatus.done.value, FeedbackStatus.completed.value])
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
            models.ItemUser.feedback_status.in_([FeedbackStatus.done.value, FeedbackStatus.completed.value])
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
                (models.ItemUser.feedback_status.in_([FeedbackStatus.done.value, FeedbackStatus.completed.value]), 1), 
                else_=0
            )
        ).label("done_count")
    ).join(models.User, models.ItemUser.user_id == models.User.id)\
    .filter(models.ItemUser.item_id.in_(items_id_select))\
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
def export_items_csv(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privilege required")

    items = db.query(models.Item).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Title", "Status", "CreatorID", "Deadline", "CreatedAt"])
    for item in items:
        writer.writerow([item.id, item.title, item.status, item.creator_id, item.deadline, item.created_at])
    output.seek(0)

    response = StreamingResponse(iter([output.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=items_export.csv"
    return response

@router.get("/export/item/{item_id}")
def export_item_data(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if current_user.role != "admin" and item.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to export this item")

    rows = db.query(models.ItemUser, models.User, models.Feedback)\
        .join(models.User, models.ItemUser.user_id == models.User.id)\
        .outerjoin(models.Feedback, models.Feedback.item_user_id == models.ItemUser.id)\
        .filter(models.ItemUser.item_id == item_id)\
        .all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "item_id",
        "title",
        "status",
        "deadline",
        "creator_id",
        "participant_user_id",
        "participant_name",
        "feedback_status",
        "last_feedback_time",
        "feedback_content",
        "feedback_created_at",
        "feedback_updated_at",
    ])

    if not rows:
        writer.writerow([item.id, item.title, item.status, item.deadline, item.creator_id, "", "", "", "", "", "", ""])
    else:
        for iu, user, fb in rows:
            writer.writerow([
                item.id,
                item.title,
                item.status,
                item.deadline,
                item.creator_id,
                user.id,
                user.name,
                iu.feedback_status,
                iu.last_feedback_time,
                fb.content if fb else "",
                fb.created_at if fb else "",
                fb.updated_at if fb else "",
            ])

    output.seek(0)
    response = StreamingResponse(iter([output.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=item_{item_id}_export.csv"
    return response

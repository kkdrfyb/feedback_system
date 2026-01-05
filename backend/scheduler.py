from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta, timezone
try:
    from .database import get_db
    from . import models
except (ImportError, ValueError):
    from database import get_db
    import models

def check_pending_feedback():
    db = next(get_db())
    now = datetime.now(timezone.utc)
    pending_items = db.query(models.ItemUser)\
        .join(models.Item)\
        .filter(models.ItemUser.feedback_status=="pending")\
        .filter(models.Item.deadline <= now + timedelta(hours=24))\
        .all()
    for pi in pending_items:
        print(f"提醒: 用户 {pi.user_id} 在事项 {pi.item_id} 前24小时未反馈")

scheduler = BackgroundScheduler()
scheduler.add_job(check_pending_feedback, "interval", minutes=60)

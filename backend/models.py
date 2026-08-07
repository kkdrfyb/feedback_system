from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
try:
    from .database import Base
    from .enums import UserRole, ItemStatus, FeedbackStatus
except (ImportError, ValueError):
    from database import Base
    from enums import UserRole, ItemStatus, FeedbackStatus
from datetime import datetime, timezone

# 辅助表用于用户和自定义分组的多对多关系
group_users = Table(
    "group_users",
    Base.metadata,
    Column("group_id", Integer, ForeignKey("groups.id"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
)

class User(Base):
    """
    用户模型 (Users)
    - role: 角色权限 (admin/creator/feedbacker)
    - group: 所属分组/部门
    """
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(
        Enum(UserRole, name="user_role", native_enum=False),
        default=UserRole.feedbacker,
        nullable=False
    )  # admin / creator / feedbacker
    group = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Item(Base):
    """
    事项模型 (Items)
    - status: 'ongoing' / 'finished'
    - attachments: JSON 存储的附件列表
    """
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    status = Column(
        Enum(ItemStatus, name="item_status", native_enum=False),
        default=ItemStatus.ongoing,
        nullable=False
    )
    must_feedback = Column(Boolean, default=True)
    deadline = Column(DateTime)
    creator_id = Column(Integer, ForeignKey("users.id"))
    attachments = Column(String, nullable=True) # 存储 JSON 字符串: [{"name": "file.pdf", "path": "/uploads/xxx"}]
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class ItemUser(Base):
    __tablename__ = "item_users"
    __table_args__ = (
        UniqueConstraint("item_id", "user_id", name="uq_item_user_item_user"),
    )
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    feedback_status = Column(
        Enum(FeedbackStatus, name="feedback_status", native_enum=False),
        default=FeedbackStatus.pending,
        nullable=False
    )
    last_feedback_time = Column(DateTime, nullable=True)

class Feedback(Base):
    __tablename__ = "feedbacks"
    __table_args__ = (
        UniqueConstraint("item_user_id", name="uq_feedback_item_user"),
    )
    id = Column(Integer, primary_key=True, index=True)
    item_user_id = Column(Integer, ForeignKey("item_users.id"))
    content = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True) # 注意：名称在同个 owner 内应该是唯一的，这里简化
    description = Column(String, nullable=True)
    is_org = Column(Boolean, default=False) # 是否是组织机构分组（管理员创建）
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True) # 发起人/创建者
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # 关联的用户
    users = relationship("User", secondary=group_users)

class OperationLog(Base):
    __tablename__ = "operation_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String)  # e.g., "Login", "Create Item", "Delete User"
    target_id = Column(String, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Spreadsheet(Base):
    """Excel 在线表格任务 — 上传模板后网页填写、自动保存、导出汇总"""
    __tablename__ = "spreadsheets"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    columns = Column(String, nullable=True)  # JSON: [{"key":"c0","label":"事项","width":200}, ...]
    owner_column = Column(String, nullable=True)  # 标识「负责人」的列 key，用于行级权限
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SpreadsheetRow(Base):
    """表格的一行数据，data 为 JSON 字段映射"""
    __tablename__ = "spreadsheet_rows"
    id = Column(Integer, primary_key=True, index=True)
    spreadsheet_id = Column(Integer, ForeignKey("spreadsheets.id"), nullable=False)
    row_index = Column(Integer, nullable=False)
    data = Column(String, nullable=True)  # JSON: {"c0":"值","c1":"值",...}
    last_edited_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    last_edited_at = Column(DateTime, nullable=True)

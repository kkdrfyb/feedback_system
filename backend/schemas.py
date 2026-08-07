from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime
from typing import Optional, List, Any
import json
try:
    from .enums import UserRole, ItemStatus
except (ImportError, ValueError):
    from enums import UserRole, ItemStatus

class UserBase(BaseModel):
    name: str
    role: UserRole
    group: Optional[str] = None

class UserCreate(UserBase):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class User(UserBase):
    id: int
    username: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ItemBase(BaseModel):
    title: str
    description: Optional[str] = ""
    must_feedback: bool = True
    deadline: datetime
    attachments: Optional[List[Any]] = None

    @field_validator("attachments", mode="before")
    @classmethod
    def parse_attachments(cls, value):
        if value is None or value == "":
            return None
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return value

class ItemCreate(ItemBase):
    creator_id: int
    user_ids: List[int] = []

class Item(ItemBase):
    id: int
    status: ItemStatus
    creator_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    must_feedback: Optional[bool] = None
    deadline: Optional[datetime] = None
    status: Optional[ItemStatus] = None
    attachments: Optional[List[Any]] = None
    user_ids: Optional[List[int]] = None

class TodoItem(Item):
    item_user_id: int
 
class PaginatedItems(BaseModel):
    items: List[Item]
    total: int

class FeedbackBase(BaseModel):
    content: str

class FeedbackForItemCreate(FeedbackBase):
    user_id: Optional[int] = None

class FeedbackCreate(FeedbackBase):
    item_user_id: int

class Feedback(FeedbackBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class GroupBase(BaseModel):
    name: str
    description: Optional[str] = ""
    is_org: bool = False

class GroupCreate(GroupBase):
    user_ids: List[int] = []

class GroupUpdate(GroupBase):
    user_ids: Optional[List[int]] = None

class Group(GroupBase):
    id: int
    owner_id: Optional[int] = None
    created_at: datetime
    user_ids: List[int] = []
    
    @classmethod
    def model_validate_orm(cls, obj):
        # 自定义验证以从关系中提取 user_ids
        instance = cls.model_validate(obj)
        instance.user_ids = [u.id for u in obj.users]
        return instance
    
    model_config = ConfigDict(from_attributes=True)

class OperationLog(BaseModel):
    id: int
    user_id: int
    action: str
    target_id: Optional[str] = None
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)


# ------ Spreadsheet schemas ------

class SpreadsheetColumn(BaseModel):
    key: str
    label: str
    width: int = 150


class SpreadsheetCreate(BaseModel):
    title: str
    description: Optional[str] = None


class SpreadsheetRowOut(BaseModel):
    id: int
    row_index: int
    data: Optional[dict] = None
    last_edited_by: Optional[int] = None
    last_edited_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

    @field_validator("data", mode="before")
    @classmethod
    def parse_data(cls, value):
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return value


class SpreadsheetOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    creator_id: int
    columns: Optional[List[SpreadsheetColumn]] = None
    owner_column: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    rows: List[SpreadsheetRowOut] = []
    model_config = ConfigDict(from_attributes=True)

    @field_validator("columns", mode="before")
    @classmethod
    def parse_columns(cls, value):
        if value is None:
            return None
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return value


class CellUpdate(BaseModel):
    """更新单个单元格"""
    row_id: int
    key: str
    value: Optional[str] = None

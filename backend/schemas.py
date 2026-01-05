from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List

class UserBase(BaseModel):
    name: str
    role: str
    group: Optional[str] = None

class UserCreate(UserBase):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class User(UserBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ItemBase(BaseModel):
    title: str
    description: Optional[str] = ""
    must_feedback: bool = True
    deadline: datetime

class ItemCreate(ItemBase):
    creator_id: int
    user_ids: List[int] = []

class Item(ItemBase):
    id: int
    status: str
    creator_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TodoItem(Item):
    item_user_id: int
 
class PaginatedItems(BaseModel):
    items: List[Item]
    total: int

class FeedbackBase(BaseModel):
    content: str

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

from enum import Enum


class UserRole(str, Enum):
    admin = "admin"
    creator = "creator"
    feedbacker = "feedbacker"


class ItemStatus(str, Enum):
    ongoing = "ongoing"
    finished = "finished"


class FeedbackStatus(str, Enum):
    pending = "pending"
    done = "done"
    completed = "completed"

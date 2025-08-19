# from pydantic import BaseModel

# class TaskCreate(BaseModel):
#     bucketId: str
#     title: str

# app/models.py
from pydantic import BaseModel, Field
from typing import Optional

class TaskCreate(BaseModel):
    bucketId: str
    title: str

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    percentComplete: Optional[int] = Field(None, ge=0, le=100)
    dueDateTime: Optional[str] = None   # ISO8601
    bucketId: Optional[str] = None

class PlanCreate(BaseModel):
    groupId: str
    title: str

class BucketCreate(BaseModel):
    name: str
    orderHint: Optional[str] = None  # Planner uses lexicographic hints; we'll default if missing

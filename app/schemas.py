from pydantic import BaseModel, Field
from app.models import StatusEnum


class RequestCreate(BaseModel):
    requester_id: int
    subject: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    category_id: int
    priority_id: int


class AssignPayload(BaseModel):
    assignee_id: int
    actor_id: int


class StatusPayload(BaseModel):
    status: StatusEnum
    actor_id: int


class ResolvePayload(BaseModel):
    resolution_details: str = Field(..., min_length=1)
    actor_id: int


class ClosePayload(BaseModel):
    actor_id: int


class CommentCreate(BaseModel):
    author_id: int
    comment: str = Field(..., min_length=1)
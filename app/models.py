import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey,
    Enum, Index, Boolean
)
from app.database import Base


class StatusEnum(str, enum.Enum):
    NEW = "NEW"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    ON_HOLD = "ON_HOLD"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    role = Column(String(20), nullable=False, default="employee")
    is_available = Column(Boolean, default=True)


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)


class Priority(Base):
    __tablename__ = "priorities"
    id = Column(Integer, primary_key=True)
    name = Column(String(20), unique=True, nullable=False)
    sla_hours = Column(Integer, nullable=False)


class ServiceRequest(Base):
    __tablename__ = "requests"
    id = Column(Integer, primary_key=True)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    priority_id = Column(Integer, ForeignKey("priorities.id"), nullable=False)
    status = Column(Enum(StatusEnum), default=StatusEnum.NEW, nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    resolution_details = Column(Text, nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        Index("ix_requests_status", "status"),
        Index("ix_requests_assignee", "assignee_id"),
        Index("ix_requests_priority", "priority_id"),
        Index("ix_requests_created", "created_at"),
    )


class RequestHistory(Base):
    __tablename__ = "request_history"
    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=False)
    event_type = Column(String(30), nullable=False)
    old_value = Column(String(200))
    new_value = Column(String(200))
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
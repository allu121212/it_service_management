from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.models import StatusEnum


VALID_TRANSITIONS = {
    StatusEnum.NEW: {StatusEnum.ASSIGNED, StatusEnum.ON_HOLD},
    StatusEnum.ASSIGNED: {StatusEnum.IN_PROGRESS, StatusEnum.ON_HOLD},
    StatusEnum.IN_PROGRESS: {StatusEnum.ON_HOLD, StatusEnum.RESOLVED},
    StatusEnum.ON_HOLD: {StatusEnum.IN_PROGRESS, StatusEnum.ASSIGNED},
    StatusEnum.RESOLVED: {StatusEnum.CLOSED},
    StatusEnum.CLOSED: set(),
}


def log_history(db, request_id, event_type, old_value=None, new_value=None, actor_id=None):
    h = models.RequestHistory(
        request_id=request_id,
        event_type=event_type,
        old_value=str(old_value) if old_value is not None else None,
        new_value=str(new_value) if new_value is not None else None,
        actor_id=actor_id,
    )
    db.add(h)


def create_request(db: Session, payload: schemas.RequestCreate):
    if not db.query(models.User).get(payload.requester_id):
        raise HTTPException(400, "Requester does not exist")
    if not db.query(models.Category).get(payload.category_id):
        raise HTTPException(400, "Category does not exist")
    if not db.query(models.Priority).get(payload.priority_id):
        raise HTTPException(400, "Priority does not exist")

    req = models.ServiceRequest(
        requester_id=payload.requester_id,
        subject=payload.subject.strip(),
        description=payload.description.strip(),
        category_id=payload.category_id,
        priority_id=payload.priority_id,
        status=StatusEnum.NEW,
    )
    db.add(req)
    db.flush()
    log_history(db, req.id, "CREATED", new_value="NEW", actor_id=payload.requester_id)
    db.commit()
    db.refresh(req)
    return req


def assign_request(db: Session, request_id: int, payload: schemas.AssignPayload):
    req = db.query(models.ServiceRequest).get(request_id)
    if not req:
        raise HTTPException(404, "Request not found")
    if req.status == StatusEnum.CLOSED:
        raise HTTPException(409, "A closed request cannot be modified")

    assignee = db.query(models.User).get(payload.assignee_id)
    if not assignee or assignee.role != "it_staff":
        raise HTTPException(400, "The selected IT team member is not available")
    if not assignee.is_available:
        raise HTTPException(400, "The selected IT team member is not available")

    old_assignee = req.assignee_id
    req.assignee_id = payload.assignee_id
    if req.status == StatusEnum.NEW:
        req.status = StatusEnum.ASSIGNED

    log_history(db, req.id, "ASSIGNMENT",
                old_value=old_assignee, new_value=payload.assignee_id,
                actor_id=payload.actor_id)
    db.commit()
    db.refresh(req)
    return req


def update_status(db: Session, request_id: int, payload: schemas.StatusPayload):
    req = db.query(models.ServiceRequest).get(request_id)
    if not req:
        raise HTTPException(404, "Request not found")
    if req.status == StatusEnum.CLOSED:
        raise HTTPException(409, "A closed request cannot be modified")

    new_status = payload.status
    if new_status not in VALID_TRANSITIONS[req.status]:
        raise HTTPException(
            400,
            f"Invalid status transition: {req.status.value} -> {new_status.value}"
        )

    if new_status == StatusEnum.RESOLVED:
        raise HTTPException(400, "Use /resolve endpoint to resolve with details")

    old = req.status
    req.status = new_status
    log_history(db, req.id, "STATUS_CHANGE",
                old_value=old.value, new_value=new_status.value,
                actor_id=payload.actor_id)
    db.commit()
    db.refresh(req)
    return req


def resolve_request(db: Session, request_id: int, payload: schemas.ResolvePayload):
    req = db.query(models.ServiceRequest).get(request_id)
    if not req:
        raise HTTPException(404, "Request not found")
    if req.status == StatusEnum.CLOSED:
        raise HTTPException(409, "A closed request cannot be modified")
    if req.status == StatusEnum.RESOLVED:
        raise HTTPException(409, "Request already resolved")
    if req.status not in (StatusEnum.IN_PROGRESS, StatusEnum.ON_HOLD):
        raise HTTPException(400, "Request must be IN_PROGRESS or ON_HOLD before resolving")

    req.status = StatusEnum.RESOLVED
    req.resolution_details = payload.resolution_details.strip()
    req.resolved_at = datetime.utcnow()
    req.resolved_by = payload.actor_id

    log_history(db, req.id, "RESOLVED",
                new_value=payload.resolution_details[:100],
                actor_id=payload.actor_id)
    db.commit()
    db.refresh(req)
    return req


def close_request(db: Session, request_id: int, payload: schemas.ClosePayload):
    req = db.query(models.ServiceRequest).get(request_id)
    if not req:
        raise HTTPException(404, "Request not found")
    if req.status != StatusEnum.RESOLVED:
        raise HTTPException(400, "Only resolved requests can be closed")
    if not req.resolution_details:
        raise HTTPException(400, "Resolution details are required before closing")

    req.status = StatusEnum.CLOSED
    req.closed_at = datetime.utcnow()
    log_history(db, req.id, "CLOSED", actor_id=payload.actor_id)
    db.commit()
    db.refresh(req)
    return req


def add_comment(db: Session, request_id: int, payload: schemas.CommentCreate):
    req = db.query(models.ServiceRequest).get(request_id)
    if not req:
        raise HTTPException(404, "Request not found")
    if not db.query(models.User).get(payload.author_id):
        raise HTTPException(400, "Author does not exist")

    c = models.Comment(
        request_id=request_id,
        author_id=payload.author_id,
        comment=payload.comment.strip(),
    )
    db.add(c)
    log_history(db, request_id, "COMMENT", new_value=payload.comment[:100],
                actor_id=payload.author_id)
    db.commit()
    db.refresh(c)
    return c
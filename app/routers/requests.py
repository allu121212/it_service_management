from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app import crud, schemas, models
from app.sla import calculate_sla

router = APIRouter(prefix="/api/requests", tags=["requests"])


def serialize(req, priority):
    sla = calculate_sla(req, priority.sla_hours)
    return {
        "id": req.id,
        "subject": req.subject,
        "description": req.description,
        "status": req.status.value,
        "requester_id": req.requester_id,
        "assignee_id": req.assignee_id,
        "category_id": req.category_id,
        "priority_id": req.priority_id,
        "created_at": req.created_at.isoformat(),
        "updated_at": req.updated_at.isoformat() if req.updated_at else None,
        "resolved_at": req.resolved_at.isoformat() if req.resolved_at else None,
        "closed_at": req.closed_at.isoformat() if req.closed_at else None,
        "resolution_details": req.resolution_details,
        "sla_state": sla["state"],
        "sla_deadline": sla["deadline"].isoformat(),
    }


@router.post("")
def create(payload: schemas.RequestCreate, db: Session = Depends(get_db)):
    req = crud.create_request(db, payload)
    p = db.query(models.Priority).get(req.priority_id)
    return serialize(req, p)


@router.get("")
def list_requests(
    status: Optional[str] = None,
    priority_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    unassigned: Optional[bool] = False,
    db: Session = Depends(get_db),
):
    q = db.query(models.ServiceRequest)
    if status:
        q = q.filter(models.ServiceRequest.status == status)
    if priority_id:
        q = q.filter(models.ServiceRequest.priority_id == priority_id)
    if assignee_id:
        q = q.filter(models.ServiceRequest.assignee_id == assignee_id)
    if unassigned:
        q = q.filter(models.ServiceRequest.assignee_id.is_(None))
    reqs = q.order_by(models.ServiceRequest.created_at.desc()).all()
    out = []
    for r in reqs:
        p = db.query(models.Priority).get(r.priority_id)
        out.append(serialize(r, p))
    return out


@router.get("/{request_id}")
def get_one(request_id: int, db: Session = Depends(get_db)):
    req = db.query(models.ServiceRequest).get(request_id)
    if not req:
        raise HTTPException(404, "Request not found")
    p = db.query(models.Priority).get(req.priority_id)
    history = db.query(models.RequestHistory).filter_by(request_id=request_id)\
        .order_by(models.RequestHistory.timestamp).all()
    comments = db.query(models.Comment).filter_by(request_id=request_id)\
        .order_by(models.Comment.created_at).all()
    return {
        **serialize(req, p),
        "history": [{"event": h.event_type, "old": h.old_value, "new": h.new_value,
                     "actor_id": h.actor_id, "at": h.timestamp.isoformat()} for h in history],
        "comments": [{"author_id": c.author_id, "comment": c.comment,
                      "at": c.created_at.isoformat()} for c in comments],
    }


@router.post("/{request_id}/assign")
def assign(request_id: int, payload: schemas.AssignPayload, db: Session = Depends(get_db)):
    req = crud.assign_request(db, request_id, payload)
    p = db.query(models.Priority).get(req.priority_id)
    return serialize(req, p)


@router.post("/{request_id}/status")
def update_status(request_id: int, payload: schemas.StatusPayload, db: Session = Depends(get_db)):
    req = crud.update_status(db, request_id, payload)
    p = db.query(models.Priority).get(req.priority_id)
    return serialize(req, p)


@router.post("/{request_id}/resolve")
def resolve(request_id: int, payload: schemas.ResolvePayload, db: Session = Depends(get_db)):
    req = crud.resolve_request(db, request_id, payload)
    p = db.query(models.Priority).get(req.priority_id)
    return serialize(req, p)


@router.post("/{request_id}/close")
def close(request_id: int, payload: schemas.ClosePayload, db: Session = Depends(get_db)):
    req = crud.close_request(db, request_id, payload)
    p = db.query(models.Priority).get(req.priority_id)
    return serialize(req, p)


@router.post("/{request_id}/comments")
def comment(request_id: int, payload: schemas.CommentCreate, db: Session = Depends(get_db)):
    c = crud.add_comment(db, request_id, payload)
    return {"id": c.id, "comment": c.comment}
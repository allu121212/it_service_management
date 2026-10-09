from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app import models
from app.sla import calculate_sla

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    total = db.query(models.ServiceRequest).count()
    open_reqs = db.query(models.ServiceRequest).filter(
        models.ServiceRequest.status.notin_(["RESOLVED", "CLOSED"])
    ).count()

    by_status_raw = dict(db.query(models.ServiceRequest.status, func.count())\
        .group_by(models.ServiceRequest.status).all())
    by_status = {k.value: v for k, v in by_status_raw.items()}

    by_priority = dict(db.query(models.ServiceRequest.priority_id, func.count())\
        .group_by(models.ServiceRequest.priority_id).all())
    by_category = dict(db.query(models.ServiceRequest.category_id, func.count())\
        .group_by(models.ServiceRequest.category_id).all())
    by_assignee = dict(db.query(models.ServiceRequest.assignee_id, func.count())\
        .filter(models.ServiceRequest.assignee_id.isnot(None))
        .group_by(models.ServiceRequest.assignee_id).all())

    unassigned = db.query(models.ServiceRequest).filter(
        models.ServiceRequest.assignee_id.is_(None)).count()

    breached = 0
    open_list = db.query(models.ServiceRequest).filter(
        models.ServiceRequest.status.notin_(["RESOLVED", "CLOSED"])
    ).all()
    for r in open_list:
        p = db.query(models.Priority).get(r.priority_id)
        s = calculate_sla(r, p.sla_hours)
        if s["state"] == "BREACHED":
            breached += 1

    return {
        "total": total,
        "open": open_reqs,
        "by_status": by_status,
        "by_priority": by_priority,
        "by_category": by_category,
        "by_assignee": by_assignee,
        "unassigned": unassigned,
        "sla_breached": breached,
    }


@router.get("/overdue")
def overdue(db: Session = Depends(get_db)):
    out = []
    open_list = db.query(models.ServiceRequest).filter(
        models.ServiceRequest.status.notin_(["RESOLVED", "CLOSED"])
    ).all()
    for r in open_list:
        p = db.query(models.Priority).get(r.priority_id)
        s = calculate_sla(r, p.sla_hours)
        if s["state"] == "BREACHED":
            out.append({"id": r.id, "subject": r.subject, "priority": p.name,
                        "deadline": s["deadline"].isoformat()})
    return out
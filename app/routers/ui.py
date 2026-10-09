from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, crud, schemas
from app.sla import calculate_sla

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    reqs = db.query(models.ServiceRequest).order_by(
        models.ServiceRequest.created_at.desc()
    ).all()
    rows = []
    for r in reqs:
        p = db.query(models.Priority).get(r.priority_id)
        c = db.query(models.Category).get(r.category_id)
        s = calculate_sla(r, p.sla_hours)
        rows.append({"r": r, "priority": p, "category": c, "sla": s})

    total = len(reqs)
    open_count = sum(1 for r in reqs if r.status.value not in ("RESOLVED", "CLOSED"))
    breached = sum(1 for row in rows if row["sla"]["state"] == "BREACHED")
    unassigned = sum(1 for r in reqs if r.assignee_id is None)

    return templates.TemplateResponse(request, "index.html", {
        "rows": rows,
        "total": total,
        "open_count": open_count,
        "breached": breached,
        "unassigned": unassigned,
    })


@router.get("/requests/new", response_class=HTMLResponse)
def new_form(request: Request, db: Session = Depends(get_db)):
    users = db.query(models.User).filter_by(role="employee").all()
    cats = db.query(models.Category).all()
    prios = db.query(models.Priority).all()
    return templates.TemplateResponse(request, "new.html", {
        "users": users, "cats": cats, "prios": prios
    })


@router.post("/requests/new")
def create_form(
    requester_id: int = Form(...),
    subject: str = Form(...),
    description: str = Form(...),
    category_id: int = Form(...),
    priority_id: int = Form(...),
    db: Session = Depends(get_db),
):
    crud.create_request(db, schemas.RequestCreate(
        requester_id=requester_id,
        subject=subject,
        description=description,
        category_id=category_id,
        priority_id=priority_id,
    ))
    return RedirectResponse("/", status_code=303)


@router.get("/requests/{rid}", response_class=HTMLResponse)
def detail(rid: int, request: Request, db: Session = Depends(get_db)):
    r = db.query(models.ServiceRequest).get(rid)
    if not r:
        return HTMLResponse("Not found", status_code=404)

    p = db.query(models.Priority).get(r.priority_id)
    c = db.query(models.Category).get(r.category_id)
    s = calculate_sla(r, p.sla_hours)

    history = db.query(models.RequestHistory).filter_by(request_id=rid)\
        .order_by(models.RequestHistory.timestamp).all()
    comments = db.query(models.Comment).filter_by(request_id=rid)\
        .order_by(models.Comment.created_at).all()

    it_users = db.query(models.User).filter_by(role="it_staff").all()

    return templates.TemplateResponse(request, "detail.html", {
        "r": r, "priority": p, "category": c, "sla": s,
        "history": history, "comments": comments, "it_users": it_users,
    })


@router.post("/requests/{rid}/assign")
def ui_assign(rid: int, assignee_id: int = Form(...), actor_id: int = Form(...),
              db: Session = Depends(get_db)):
    crud.assign_request(db, rid, schemas.AssignPayload(
        assignee_id=assignee_id, actor_id=actor_id))
    return RedirectResponse(f"/requests/{rid}", status_code=303)


@router.post("/requests/{rid}/status")
def ui_status(rid: int, status: str = Form(...), actor_id: int = Form(...),
              db: Session = Depends(get_db)):
    crud.update_status(db, rid, schemas.StatusPayload(
        status=status, actor_id=actor_id))
    return RedirectResponse(f"/requests/{rid}", status_code=303)


@router.post("/requests/{rid}/resolve")
def ui_resolve(rid: int, resolution_details: str = Form(...), actor_id: int = Form(...),
               db: Session = Depends(get_db)):
    crud.resolve_request(db, rid, schemas.ResolvePayload(
        resolution_details=resolution_details, actor_id=actor_id))
    return RedirectResponse(f"/requests/{rid}", status_code=303)


@router.post("/requests/{rid}/close")
def ui_close(rid: int, actor_id: int = Form(...), db: Session = Depends(get_db)):
    crud.close_request(db, rid, schemas.ClosePayload(actor_id=actor_id))
    return RedirectResponse(f"/requests/{rid}", status_code=303)


@router.post("/requests/{rid}/comments")
def ui_comment(rid: int, author_id: int = Form(...), comment: str = Form(...),
               db: Session = Depends(get_db)):
    crud.add_comment(db, rid, schemas.CommentCreate(
        author_id=author_id, comment=comment))
    return RedirectResponse(f"/requests/{rid}", status_code=303)
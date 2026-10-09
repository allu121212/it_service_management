from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app import models, crud, schemas
from app.sla import calculate_sla
from app.auth import verify_password, create_token, hash_password
from app.dependencies import get_current_user, require_role
from app.otp import generate_otp, otp_expiry, send_otp_email

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _redirect_with_cookie(url: str, user) -> RedirectResponse:
    token = create_token(user.id, user.role)
    response = RedirectResponse(url, status_code=303)
    response.set_cookie("token", token, httponly=True, samesite="lax")
    return response


# ============================================================
# LANDING PAGE
# ============================================================

@router.get("/", response_class=HTMLResponse)
def landing(request: Request):
    return templates.TemplateResponse(request, "home.html", {})


# ============================================================
# ADMIN LOGIN (manager only)
# ============================================================

@router.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request):
    return templates.TemplateResponse(request, "admin_login.html", {})


@router.post("/admin/login")
def admin_login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter_by(email=email).first()

    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(request, "admin_login.html",
            {"error": "Invalid email or password."}, status_code=401)

    if user.role != "manager":
        return templates.TemplateResponse(request, "admin_login.html",
            {"error": "This login is for managers only. Please use the User Login."},
            status_code=403)

    if user.is_locked:
        return templates.TemplateResponse(request, "admin_login.html",
            {"error": "Account locked. Contact IT."}, status_code=403)

    user.failed_login_attempts = 0
    db.commit()
    return _redirect_with_cookie("/dashboard", user)


# ============================================================
# USER LOGIN (employee + IT staff)
# ============================================================

@router.get("/user/login", response_class=HTMLResponse)
def user_login_page(request: Request):
    success = request.query_params.get("registered")
    return templates.TemplateResponse(request, "user_login.html", {
        "success": "Registration complete! You can log in now." if success else None,
    })


@router.post("/user/login")
def user_login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter_by(email=email).first()

    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= 5:
                user.is_locked = True
            db.commit()
        return templates.TemplateResponse(request, "user_login.html",
            {"error": "Invalid email or password."}, status_code=401)

    if user.is_locked:
        return templates.TemplateResponse(request, "user_login.html",
            {"error": "Account locked due to too many failed attempts. Contact IT."},
            status_code=403)

    if user.role == "manager":
        return templates.TemplateResponse(request, "user_login.html",
            {"error": "Managers must use the Admin Login."}, status_code=403)

    user.failed_login_attempts = 0
    db.commit()
    return _redirect_with_cookie("/dashboard", user)


# ============================================================
# REGISTRATION
# ============================================================

@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {})


@router.post("/register")
def register_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    role: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    def err(msg):
        return templates.TemplateResponse(request, "register.html",
            {"error": msg}, status_code=400)

    name = name.strip()
    email = email.strip().lower()

    if role not in ("employee", "it_staff"):
        return err("Invalid role selection.")
    if len(password) < 8:
        return err("Password must be at least 8 characters.")
    if password != confirm_password:
        return err("Passwords do not match.")
    if db.query(models.User).filter_by(email=email).first():
        return err("An account with this email already exists.")

    otp = generate_otp()
    db.query(models.PendingRegistration).filter_by(email=email).delete()

    pending = models.PendingRegistration(
        name=name, email=email, role=role,
        password_hash=hash_password(password),
        otp_code=otp,
        otp_expires_at=otp_expiry(15),
    )
    db.add(pending)
    db.commit()
    send_otp_email(email, otp, name)
    return RedirectResponse(f"/verify-otp?email={email}", status_code=303)


# ============================================================
# OTP VERIFICATION
# ============================================================

@router.get("/verify-otp", response_class=HTMLResponse)
def verify_otp_page(request: Request):
    email = request.query_params.get("email", "")
    return templates.TemplateResponse(request, "verify_otp.html", {"email": email})


@router.post("/verify-otp")
def verify_otp_submit(
    request: Request,
    email: str = Form(...),
    otp: str = Form(...),
    db: Session = Depends(get_db),
):
    def err(msg):
        return templates.TemplateResponse(request, "verify_otp.html",
            {"email": email, "error": msg}, status_code=400)

    email = email.strip().lower()
    otp = otp.strip()

    pending = db.query(models.PendingRegistration).filter_by(email=email).first()
    if not pending:
        return err("No pending registration found. Please register again.")
    if datetime.utcnow() > pending.otp_expires_at:
        db.delete(pending); db.commit()
        return err("OTP has expired. Please register again.")
    if pending.otp_code != otp:
        return err("Incorrect OTP. Please try again.")

    user = models.User(
        name=pending.name, email=pending.email, role=pending.role,
        password_hash=pending.password_hash,
        is_email_verified=True, must_change_password=False,
        failed_login_attempts=0, is_locked=False, is_available=True,
    )
    db.add(user)
    db.delete(pending)
    db.commit()
    return RedirectResponse("/user/login?registered=1", status_code=303)


# ============================================================
# DASHBOARD
# ============================================================

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):

    if user.must_change_password:
        return RedirectResponse("/change-password", status_code=303)

    if user.role == "employee":
        reqs = db.query(models.ServiceRequest)\
            .filter(models.ServiceRequest.requester_id == user.id)\
            .order_by(models.ServiceRequest.created_at.desc()).all()
    elif user.role == "it_staff":
        reqs = db.query(models.ServiceRequest)\
            .filter(
                (models.ServiceRequest.assignee_id == user.id) |
                (models.ServiceRequest.assignee_id.is_(None))
            )\
            .order_by(models.ServiceRequest.created_at.desc()).all()
    elif user.role == "manager":
        reqs = db.query(models.ServiceRequest)\
            .order_by(models.ServiceRequest.created_at.desc()).all()
    else:
        reqs = []

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
        "user": user, "rows": rows,
        "total": total, "open_count": open_count,
        "breached": breached, "unassigned": unassigned,
    })


# ============================================================
# CHANGE PASSWORD
# ============================================================

@router.get("/change-password", response_class=HTMLResponse)
def change_password_page(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(request, "change_password.html", {
        "user": user, "forced": user.must_change_password,
    })


@router.post("/change-password")
def change_password_submit(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    def err(msg):
        return templates.TemplateResponse(request, "change_password.html",
            {"user": user, "forced": user.must_change_password, "error": msg},
            status_code=400)

    if not verify_password(current_password, user.password_hash):
        return err("Current password is incorrect.")
    if len(new_password) < 8:
        return err("New password must be at least 8 characters.")
    if new_password != confirm_password:
        return err("New passwords do not match.")
    if new_password == current_password:
        return err("New password must be different from current.")

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    user.password_changed_at = datetime.utcnow()
    db.commit()
    return RedirectResponse("/dashboard", status_code=303)


# ============================================================
# LOGOUT
# ============================================================

@router.get("/logout")
def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("token")
    return response


# ============================================================
# NEW REQUEST — employees only
# ============================================================

@router.get("/requests/new", response_class=HTMLResponse)
def new_form(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user.must_change_password:
        return RedirectResponse("/change-password", status_code=303)

    if user.role != "employee":
        raise HTTPException(
            status_code=403,
            detail="Only employees can create service requests. IT staff and managers work on existing tickets."
        )

    cats = db.query(models.Category).all()
    prios = db.query(models.Priority).all()
    return templates.TemplateResponse(request, "new.html", {
        "user": user, "cats": cats, "prios": prios
    })


@router.post("/requests/new")
def create_form(
    subject: str = Form(...),
    description: str = Form(...),
    category_id: int = Form(...),
    priority_id: int = Form(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != "employee":
        raise HTTPException(status_code=403,
            detail="Only employees can create service requests.")

    crud.create_request(db, schemas.RequestCreate(
        requester_id=user.id, subject=subject,
        description=description, category_id=category_id,
        priority_id=priority_id,
    ))
    return RedirectResponse("/dashboard", status_code=303)


# ============================================================
# REQUEST DETAIL — role-based access
# ============================================================

@router.get("/requests/{rid}", response_class=HTMLResponse)
def detail(rid: int, request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if user.must_change_password:
        return RedirectResponse("/change-password", status_code=303)

    r = db.query(models.ServiceRequest).get(rid)
    if not r:
        return HTMLResponse("Not found", status_code=404)

    if user.role == "employee":
        if r.requester_id != user.id:
            raise HTTPException(403, "You can only view your own requests.")

    elif user.role == "it_staff":
        if r.assignee_id is not None and r.assignee_id != user.id:
            raise HTTPException(403,
                "This request is assigned to another IT staff member.")

    # Manager sees everything.

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
        "history": history, "comments": comments,
        "it_users": it_users, "user": user,
    })


# ============================================================
# ACTIONS — with ownership checks
# ============================================================

@router.post("/requests/{rid}/assign")
def ui_assign(
    rid: int,
    assignee_id: int = Form(...),
    user=Depends(require_role("manager")),
    db: Session = Depends(get_db),
):
    crud.assign_request(db, rid, schemas.AssignPayload(
        assignee_id=assignee_id, actor_id=user.id))
    return RedirectResponse(f"/requests/{rid}", status_code=303)


@router.post("/requests/{rid}/status")
def ui_status(
    rid: int,
    status: str = Form(...),
    user=Depends(require_role("it_staff", "manager")),
    db: Session = Depends(get_db),
):
    req = db.query(models.ServiceRequest).get(rid)

    if user.role == "it_staff":
        if req.assignee_id is None:
            raise HTTPException(403,
                "This request is not assigned to anyone yet. "
                "A manager must assign it to you before you can work on it.")
        if req.assignee_id != user.id:
            raise HTTPException(403,
                "This request is assigned to another IT staff member.")

    crud.update_status(db, rid, schemas.StatusPayload(
        status=status, actor_id=user.id))
    return RedirectResponse(f"/requests/{rid}", status_code=303)


@router.post("/requests/{rid}/resolve")
def ui_resolve(
    rid: int,
    resolution_details: str = Form(...),
    user=Depends(require_role("it_staff", "manager")),
    db: Session = Depends(get_db),
):
    req = db.query(models.ServiceRequest).get(rid)

    if user.role == "it_staff":
        if req.assignee_id is None:
            raise HTTPException(403,
                "This request is not assigned to anyone yet. "
                "A manager must assign it to you first.")
        if req.assignee_id != user.id:
            raise HTTPException(403,
                "This request is assigned to another IT staff member.")

    crud.resolve_request(db, rid, schemas.ResolvePayload(
        resolution_details=resolution_details, actor_id=user.id))
    return RedirectResponse(f"/requests/{rid}", status_code=303)


@router.post("/requests/{rid}/close")
def ui_close(
    rid: int,
    user=Depends(require_role("it_staff", "manager")),
    db: Session = Depends(get_db),
):
    req = db.query(models.ServiceRequest).get(rid)

    if user.role == "it_staff":
        if req.assignee_id is None:
            raise HTTPException(403,
                "This request is not assigned to anyone yet. "
                "A manager must assign it to you first.")
        if req.assignee_id != user.id:
            raise HTTPException(403,
                "This request is assigned to another IT staff member.")

    crud.close_request(db, rid, schemas.ClosePayload(actor_id=user.id))
    return RedirectResponse(f"/requests/{rid}", status_code=303)


@router.post("/requests/{rid}/comments")
def ui_comment(
    rid: int,
    comment: str = Form(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req = db.query(models.ServiceRequest).get(rid)

    if user.role == "employee" and req.requester_id != user.id:
        raise HTTPException(403, "You can only comment on your own requests.")
    if user.role == "it_staff" and req.assignee_id not in (None, user.id):
        raise HTTPException(403, "You can only comment on your assigned requests.")

    crud.add_comment(db, rid, schemas.CommentCreate(
        author_id=user.id, comment=comment))
    return RedirectResponse(f"/requests/{rid}", status_code=303)
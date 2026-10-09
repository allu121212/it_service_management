from datetime import datetime, timedelta
from app.database import SessionLocal, Base, engine
from app import models
from app.models import StatusEnum


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Clear existing demo data (safe re-run)
    db.query(models.RequestHistory).delete()
    db.query(models.Comment).delete()
    db.query(models.ServiceRequest).delete()
    db.query(models.User).delete()
    db.query(models.Category).delete()
    db.query(models.Priority).delete()
    db.commit()

    # Priorities with SLA hours
    priorities = [
        models.Priority(name="Critical", sla_hours=4),
        models.Priority(name="High",     sla_hours=8),
        models.Priority(name="Medium",   sla_hours=24),
        models.Priority(name="Low",      sla_hours=48),
    ]
    db.add_all(priorities)

    # Categories
    categories = [models.Category(name=n) for n in
                  ["Hardware", "Software", "Network",
                   "Access/Permission", "Email", "Other"]]
    db.add_all(categories)

    # Users
    users = [
        models.User(name="Alice Employee",  email="alice@corp.com",   role="employee"),
        models.User(name="Bob Employee",    email="bob@corp.com",     role="employee"),
        models.User(name="Charlie IT",      email="charlie@corp.com", role="it_staff"),
        models.User(name="Dana IT",         email="dana@corp.com",    role="it_staff"),
    ]
    db.add_all(users)
    db.commit()

    # Refresh to get IDs
    for p in priorities: db.refresh(p)
    for c in categories: db.refresh(c)
    for u in users: db.refresh(u)

    P = {p.name: p.id for p in priorities}
    C = {c.name: c.id for c in categories}
    U = {u.name: u.id for u in users}

    now = datetime.utcnow()

    # ------------------------------------------------------------------
    # SCENARIO 1: Critical BREACHED (created 6h ago, still NEW, SLA=4h)
    # ------------------------------------------------------------------
    r1 = models.ServiceRequest(
        requester_id=U["Alice Employee"],
        subject="Production server down",
        description="The main production server is not responding. All services offline.",
        category_id=C["Network"],
        priority_id=P["Critical"],
        status=StatusEnum.NEW,
        created_at=now - timedelta(hours=6),
        updated_at=now - timedelta(hours=6),
    )
    db.add(r1); db.flush()
    db.add(models.RequestHistory(request_id=r1.id, event_type="CREATED",
                                 new_value="NEW", actor_id=U["Alice Employee"],
                                 timestamp=now - timedelta(hours=6)))

    # ------------------------------------------------------------------
    # SCENARIO 2: High APPROACHING (created 7h ago, IN_PROGRESS, SLA=8h)
    # ------------------------------------------------------------------
    r2 = models.ServiceRequest(
        requester_id=U["Bob Employee"],
        subject="CRM application very slow",
        description="The CRM app takes 30+ seconds to load any page.",
        category_id=C["Software"],
        priority_id=P["High"],
        status=StatusEnum.IN_PROGRESS,
        assignee_id=U["Charlie IT"],
        created_at=now - timedelta(hours=7),
        updated_at=now - timedelta(hours=1),
    )
    db.add(r2); db.flush()
    db.add(models.RequestHistory(request_id=r2.id, event_type="CREATED",
                                 new_value="NEW", actor_id=U["Bob Employee"],
                                 timestamp=now - timedelta(hours=7)))
    db.add(models.RequestHistory(request_id=r2.id, event_type="ASSIGNMENT",
                                 new_value=str(U["Charlie IT"]), actor_id=U["Charlie IT"],
                                 timestamp=now - timedelta(hours=5)))
    db.add(models.RequestHistory(request_id=r2.id, event_type="STATUS_CHANGE",
                                 old_value="ASSIGNED", new_value="IN_PROGRESS",
                                 actor_id=U["Charlie IT"],
                                 timestamp=now - timedelta(hours=1)))
    db.add(models.Comment(request_id=r2.id, author_id=U["Charlie IT"],
                          comment="Investigating DB query performance issue.",
                          created_at=now - timedelta(minutes=50)))

    # ------------------------------------------------------------------
    # SCENARIO 3: Medium WITHIN_SLA (created 2h ago, ASSIGNED, SLA=24h)
    # ------------------------------------------------------------------
    r3 = models.ServiceRequest(
        requester_id=U["Alice Employee"],
        subject="New laptop setup request",
        description="Need a new laptop configured for a new hire starting Monday.",
        category_id=C["Hardware"],
        priority_id=P["Medium"],
        status=StatusEnum.ASSIGNED,
        assignee_id=U["Dana IT"],
        created_at=now - timedelta(hours=2),
        updated_at=now - timedelta(hours=1),
    )
    db.add(r3); db.flush()
    db.add(models.RequestHistory(request_id=r3.id, event_type="CREATED",
                                 new_value="NEW", actor_id=U["Alice Employee"],
                                 timestamp=now - timedelta(hours=2)))
    db.add(models.RequestHistory(request_id=r3.id, event_type="ASSIGNMENT",
                                 new_value=str(U["Dana IT"]), actor_id=U["Dana IT"],
                                 timestamp=now - timedelta(hours=1)))

    # ------------------------------------------------------------------
    # SCENARIO 4: Low RESOLVED_WITHIN_SLA (created 2d ago, resolved, closed)
    # ------------------------------------------------------------------
    r4 = models.ServiceRequest(
        requester_id=U["Bob Employee"],
        subject="Password reset request",
        description="Locked out of email account after multiple failed logins.",
        category_id=C["Access/Permission"],
        priority_id=P["Low"],
        status=StatusEnum.CLOSED,
        assignee_id=U["Charlie IT"],
        created_at=now - timedelta(days=2),
        updated_at=now - timedelta(days=1, hours=20),
        resolved_at=now - timedelta(days=1, hours=20),
        closed_at=now - timedelta(days=1, hours=18),
        resolution_details="Reset password and unlocked account. User confirmed access.",
        resolved_by=U["Charlie IT"],
    )
    db.add(r4); db.flush()
    db.add(models.RequestHistory(request_id=r4.id, event_type="CREATED",
                                 new_value="NEW", actor_id=U["Bob Employee"],
                                 timestamp=now - timedelta(days=2)))
    db.add(models.RequestHistory(request_id=r4.id, event_type="ASSIGNMENT",
                                 new_value=str(U["Charlie IT"]), actor_id=U["Charlie IT"],
                                 timestamp=now - timedelta(days=1, hours=22)))
    db.add(models.RequestHistory(request_id=r4.id, event_type="RESOLVED",
                                 new_value="Reset password and unlocked account.",
                                 actor_id=U["Charlie IT"],
                                 timestamp=now - timedelta(days=1, hours=20)))
    db.add(models.RequestHistory(request_id=r4.id, event_type="CLOSED",
                                 actor_id=U["Charlie IT"],
                                 timestamp=now - timedelta(days=1, hours=18)))

    db.commit()
    db.close()
    print("Seeded 4 demo scenarios: BREACHED, APPROACHING, WITHIN_SLA, RESOLVED_WITHIN_SLA")


if __name__ == "__main__":
    seed()
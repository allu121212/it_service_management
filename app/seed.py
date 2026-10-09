from datetime import datetime, timedelta
from sqlalchemy import text
from app.database import SessionLocal, Base, engine
from app import models
from app.models import StatusEnum
from app.auth import hash_password


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # FORCE CLEAR using raw SQL (bypasses FK checks)
    db.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    db.execute(text("TRUNCATE TABLE request_history"))
    db.execute(text("TRUNCATE TABLE comments"))
    db.execute(text("TRUNCATE TABLE requests"))
    db.execute(text("TRUNCATE TABLE users"))
    db.execute(text("TRUNCATE TABLE categories"))
    db.execute(text("TRUNCATE TABLE priorities"))
    db.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    db.commit()

    # PRIORITIES
    db.add_all([
        models.Priority(id=1, name="Critical", sla_hours=4),
        models.Priority(id=2, name="High",     sla_hours=8),
        models.Priority(id=3, name="Medium",   sla_hours=24),
        models.Priority(id=4, name="Low",      sla_hours=48),
    ])

    # CATEGORIES
    cats = ["Hardware", "Software", "Network", "Access/Permission", "Email", "Other"]
    for i, name in enumerate(cats, start=1):
        db.add(models.Category(id=i, name=name))

    # USERS — each has a UNIQUE temporary password (hashed, not plaintext)
    # In production these would be emailed to the user's corporate address.
    users = [
        (1, "Alice Employee", "alice@corp.com",   "employee", "Welcome@Alice1"),
        (2, "Bob Employee",   "bob@corp.com",     "employee", "Welcome@Bob2"),
        (3, "Charlie IT",     "charlie@corp.com", "it_staff", "Welcome@Charlie3"),
        (4, "Dana IT",        "dana@corp.com",    "it_staff", "Welcome@Dana4"),
        (5, "Alekhya",        "alekhya@corp.com", "employee", "Welcome@Alekhya5"),
        (6, "Ravi Kumar",     "ravi@corp.com",    "employee", "Welcome@Ravi6"),
        (7, "Priya IT",       "priya@corp.com",   "it_staff", "Welcome@Priya7"),
        (8, "Suresh IT",      "suresh@corp.com",  "it_staff", "Welcome@Suresh8"),
        (9, "Maya Manager",   "maya@corp.com",    "manager",  "Welcome@Maya9"),
    ]
    for uid, name, email, role, temp_pass in users:
        db.add(models.User(
            id=uid, name=name, email=email, role=role,
            password_hash=hash_password(temp_pass),
            must_change_password=True,
            failed_login_attempts=0,
            is_locked=False,
        ))
    db.commit()

    now = datetime.utcnow()

    # ------------------------------------------------------------------
    # REQUEST #1: Critical BREACHED (created 6h ago, still NEW, SLA=4h)
    # ------------------------------------------------------------------
    r1 = models.ServiceRequest(
        requester_id=1, subject="Production server down",
        description="The main production server is not responding. All services offline.",
        category_id=3, priority_id=1, status=StatusEnum.NEW,
        created_at=now - timedelta(hours=6),
        updated_at=now - timedelta(hours=6),
    )
    db.add(r1); db.flush()
    db.add(models.RequestHistory(request_id=r1.id, event_type="CREATED",
                                 new_value="NEW", actor_id=1,
                                 timestamp=now - timedelta(hours=6)))

    # ------------------------------------------------------------------
    # REQUEST #2: High APPROACHING (created 7h ago, IN_PROGRESS, SLA=8h)
    # ------------------------------------------------------------------
    r2 = models.ServiceRequest(
        requester_id=2, subject="CRM application very slow",
        description="The CRM app takes 30+ seconds to load any page.",
        category_id=2, priority_id=2, status=StatusEnum.IN_PROGRESS,
        assignee_id=3,
        created_at=now - timedelta(hours=7),
        updated_at=now - timedelta(hours=1),
    )
    db.add(r2); db.flush()
    db.add(models.RequestHistory(request_id=r2.id, event_type="CREATED",
                                 new_value="NEW", actor_id=2,
                                 timestamp=now - timedelta(hours=7)))
    db.add(models.RequestHistory(request_id=r2.id, event_type="ASSIGNMENT",
                                 new_value="3", actor_id=3,
                                 timestamp=now - timedelta(hours=5)))
    db.add(models.RequestHistory(request_id=r2.id, event_type="STATUS_CHANGE",
                                 old_value="ASSIGNED", new_value="IN_PROGRESS",
                                 actor_id=3, timestamp=now - timedelta(hours=1)))
    db.add(models.Comment(request_id=r2.id, author_id=3,
                          comment="Investigating DB query performance issue.",
                          created_at=now - timedelta(minutes=50)))

    # ------------------------------------------------------------------
    # REQUEST #3: Medium WITHIN_SLA (created 2h ago, ASSIGNED, SLA=24h)
    # ------------------------------------------------------------------
    r3 = models.ServiceRequest(
        requester_id=1, subject="New laptop setup request",
        description="Need a new laptop configured for a new hire starting Monday.",
        category_id=1, priority_id=3, status=StatusEnum.ASSIGNED,
        assignee_id=4,
        created_at=now - timedelta(hours=2),
        updated_at=now - timedelta(hours=1),
    )
    db.add(r3); db.flush()
    db.add(models.RequestHistory(request_id=r3.id, event_type="CREATED",
                                 new_value="NEW", actor_id=1,
                                 timestamp=now - timedelta(hours=2)))
    db.add(models.RequestHistory(request_id=r3.id, event_type="ASSIGNMENT",
                                 new_value="4", actor_id=4,
                                 timestamp=now - timedelta(hours=1)))

    # ------------------------------------------------------------------
    # REQUEST #4: Low CLOSED (created 2d ago, resolved + closed)
    # ------------------------------------------------------------------
    r4 = models.ServiceRequest(
        requester_id=2, subject="Password reset request",
        description="Locked out of email account after multiple failed logins.",
        category_id=4, priority_id=4, status=StatusEnum.CLOSED,
        assignee_id=3,
        created_at=now - timedelta(days=2),
        updated_at=now - timedelta(days=1, hours=20),
        resolved_at=now - timedelta(days=1, hours=20),
        closed_at=now - timedelta(days=1, hours=18),
        resolution_details="Reset password and unlocked account. User confirmed access.",
        resolved_by=3,
    )
    db.add(r4); db.flush()
    db.add(models.RequestHistory(request_id=r4.id, event_type="CREATED",
                                 new_value="NEW", actor_id=2,
                                 timestamp=now - timedelta(days=2)))
    db.add(models.RequestHistory(request_id=r4.id, event_type="CLOSED",
                                 actor_id=3,
                                 timestamp=now - timedelta(days=1, hours=18)))

    db.commit()
    db.close()
    print("Seeded 4 scenarios + 9 users (IDs 1-9) with unique temp passwords")


if __name__ == "__main__":
    seed()
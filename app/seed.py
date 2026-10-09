from app.database import SessionLocal, Base, engine
from app import models


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(models.Priority).count() == 0:
        db.add_all([
            models.Priority(name="Critical", sla_hours=4),
            models.Priority(name="High",     sla_hours=8),
            models.Priority(name="Medium",   sla_hours=24),
            models.Priority(name="Low",      sla_hours=48),
        ])

    if db.query(models.Category).count() == 0:
        for name in ["Hardware", "Software", "Network", "Access/Permission", "Email", "Other"]:
            db.add(models.Category(name=name))

    if db.query(models.User).count() == 0:
        db.add_all([
            models.User(name="Alice Employee", email="alice@corp.com", role="employee"),
            models.User(name="Bob Employee",   email="bob@corp.com",   role="employee"),
            models.User(name="Charlie IT",     email="charlie@corp.com", role="it_staff"),
            models.User(name="Dana IT",        email="dana@corp.com",    role="it_staff"),
        ])

    db.commit()
    db.close()
    print("Seeded successfully.")


if __name__ == "__main__":
    seed()
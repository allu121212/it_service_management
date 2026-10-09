from datetime import datetime, timedelta
from app.models import StatusEnum

APPROACHING_THRESHOLD = 0.75


def calculate_sla(request, priority_sla_hours: int):
    deadline = request.created_at + timedelta(hours=priority_sla_hours)
    now = datetime.utcnow()

    if request.status in (StatusEnum.RESOLVED, StatusEnum.CLOSED):
        resolved_at = request.resolved_at or request.closed_at
        if resolved_at and resolved_at <= deadline:
            return {"state": "RESOLVED_WITHIN_SLA", "deadline": deadline,
                    "remaining_hours": 0, "overdue_hours": 0, "human": ""}
        return {"state": "BREACHED", "deadline": deadline,
                "remaining_hours": 0, "overdue_hours": 0, "human": ""}

    if now > deadline:
        overdue = (now - deadline).total_seconds() / 3600
        h = int(overdue)
        m = int((overdue - h) * 60)
        return {"state": "BREACHED", "deadline": deadline,
                "remaining_hours": 0, "overdue_hours": overdue,
                "human": f"breached {h}h {m}m ago"}

    total = (deadline - request.created_at).total_seconds()
    elapsed = (now - request.created_at).total_seconds()
    remaining = (deadline - now).total_seconds() / 3600
    rh = int(remaining)
    rm = int((remaining - rh) * 60)

    if total > 0 and (elapsed / total) >= APPROACHING_THRESHOLD:
        return {"state": "APPROACHING", "deadline": deadline,
                "remaining_hours": remaining, "overdue_hours": 0,
                "human": f"{rh}h {rm}m left"}

    return {"state": "WITHIN_SLA", "deadline": deadline,
            "remaining_hours": remaining, "overdue_hours": 0,
            "human": f"{rh}h {rm}m left"}
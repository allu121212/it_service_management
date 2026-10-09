from datetime import datetime, timedelta
from app.models import StatusEnum

APPROACHING_THRESHOLD = 0.75  # 75% of SLA elapsed = approaching


def calculate_sla(request, priority_sla_hours: int):
    deadline = request.created_at + timedelta(hours=priority_sla_hours)
    now = datetime.utcnow()

    if request.status in (StatusEnum.RESOLVED, StatusEnum.CLOSED):
        resolved_at = request.resolved_at or request.closed_at
        if resolved_at and resolved_at <= deadline:
            return {"state": "RESOLVED_WITHIN_SLA", "deadline": deadline}
        return {"state": "BREACHED", "deadline": deadline}

    if now > deadline:
        return {"state": "BREACHED", "deadline": deadline}

    total = (deadline - request.created_at).total_seconds()
    elapsed = (now - request.created_at).total_seconds()
    if total > 0 and (elapsed / total) >= APPROACHING_THRESHOLD:
        return {"state": "APPROACHING", "deadline": deadline}

    return {"state": "WITHIN_SLA", "deadline": deadline}
def make_request(client, **overrides):
    """Helper: create a request with defaults."""
    payload = {
        "requester_id": 1,
        "subject": "Test request",
        "description": "Something is broken",
        "category_id": 1,
        "priority_id": 2,  # High
    }
    payload.update(overrides)
    return client.post("/api/requests", json=payload)


# -------------------------------------------------------------------------
# POSITIVE TESTS
# -------------------------------------------------------------------------

def test_create_request_success(client):
    r = make_request(client)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "NEW"
    assert body["subject"] == "Test request"
    assert body["sla_state"] in ("WITHIN_SLA", "APPROACHING")


def test_full_lifecycle(client):
    # 1. Create
    req_id = make_request(client).json()["id"]

    # 2. Assign to Charlie (id=3, it_staff)
    r = client.post(f"/api/requests/{req_id}/assign",
                    json={"assignee_id": 3, "actor_id": 3})
    assert r.status_code == 200
    assert r.json()["status"] == "ASSIGNED"

    # 3. Move to IN_PROGRESS
    r = client.post(f"/api/requests/{req_id}/status",
                    json={"status": "IN_PROGRESS", "actor_id": 3})
    assert r.status_code == 200
    assert r.json()["status"] == "IN_PROGRESS"

    # 4. Add comment
    r = client.post(f"/api/requests/{req_id}/comments",
                    json={"author_id": 3, "comment": "Investigating"})
    assert r.status_code == 200

    # 5. Resolve
    r = client.post(f"/api/requests/{req_id}/resolve",
                    json={"resolution_details": "Fixed it", "actor_id": 3})
    assert r.status_code == 200
    assert r.json()["status"] == "RESOLVED"
    assert r.json()["sla_state"] == "RESOLVED_WITHIN_SLA"

    # 6. Close
    r = client.post(f"/api/requests/{req_id}/close",
                    json={"actor_id": 3})
    assert r.status_code == 200
    assert r.json()["status"] == "CLOSED"


def test_history_and_comments_returned(client):
    req_id = make_request(client).json()["id"]
    client.post(f"/api/requests/{req_id}/assign",
                json={"assignee_id": 3, "actor_id": 3})
    r = client.get(f"/api/requests/{req_id}")
    body = r.json()
    assert len(body["history"]) >= 2
    events = [h["event"] for h in body["history"]]
    assert "CREATED" in events
    assert "ASSIGNMENT" in events


def test_reports_summary(client):
    make_request(client)  # create one
    r = client.get("/api/reports/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["open"] == 1
    assert body["unassigned"] == 1


# -------------------------------------------------------------------------
# NEGATIVE TESTS
# -------------------------------------------------------------------------

def test_create_request_missing_subject(client):
    r = client.post("/api/requests", json={
        "requester_id": 1,
        "description": "desc",
        "category_id": 1,
        "priority_id": 2,
    })
    assert r.status_code == 422


def test_create_request_invalid_requester(client):
    r = make_request(client, requester_id=999)
    assert r.status_code == 400


def test_assign_to_non_it_user_rejected(client):
    req_id = make_request(client).json()["id"]
    # user 1 = Alice (employee)
    r = client.post(f"/api/requests/{req_id}/assign",
                    json={"assignee_id": 1, "actor_id": 3})
    assert r.status_code == 400


def test_invalid_status_transition(client):
    req_id = make_request(client).json()["id"]  # status = NEW
    # Cannot go NEW -> CLOSED
    r = client.post(f"/api/requests/{req_id}/status",
                    json={"status": "CLOSED", "actor_id": 3})
    assert r.status_code == 400


def test_resolve_without_details_rejected(client):
    req_id = make_request(client).json()["id"]
    client.post(f"/api/requests/{req_id}/assign",
                json={"assignee_id": 3, "actor_id": 3})
    client.post(f"/api/requests/{req_id}/status",
                json={"status": "IN_PROGRESS", "actor_id": 3})
    # Missing resolution_details -> 422
    r = client.post(f"/api/requests/{req_id}/resolve",
                    json={"actor_id": 3})
    assert r.status_code == 422


def test_close_unresolved_rejected(client):
    req_id = make_request(client).json()["id"]
    r = client.post(f"/api/requests/{req_id}/close",
                    json={"actor_id": 3})
    assert r.status_code == 400


def test_modify_closed_request_rejected(client):
    req_id = make_request(client).json()["id"]
    # Full lifecycle to CLOSED
    client.post(f"/api/requests/{req_id}/assign",
                json={"assignee_id": 3, "actor_id": 3})
    client.post(f"/api/requests/{req_id}/status",
                json={"status": "IN_PROGRESS", "actor_id": 3})
    client.post(f"/api/requests/{req_id}/resolve",
                json={"resolution_details": "Done", "actor_id": 3})
    client.post(f"/api/requests/{req_id}/close",
                json={"actor_id": 3})
    # Try to assign again
    r = client.post(f"/api/requests/{req_id}/assign",
                    json={"assignee_id": 3, "actor_id": 3})
    assert r.status_code == 409
\# IT Service Request Management System



A centralized IT service request management system built for the Developer Hackathon challenge. Employees can raise IT service requests, and the IT team can assign, track, resolve, and close them with full SLA monitoring and reporting.



\---



\## 1. Project Overview



This application replaces the current ad-hoc process (messages, emails, verbal communication) with a structured, trackable system.



\*\*Core capabilities:\*\*

\- Employees raise categorized, prioritized IT service requests

\- IT staff take ownership, update status, and add comments

\- Full request lifecycle enforced: `NEW → ASSIGNED → IN\_PROGRESS → ON\_HOLD → RESOLVED → CLOSED`

\- SLA calculated per priority (Critical=4h, High=8h, Medium=24h, Low=48h)

\- Live SLA countdown ("2h 15m left" / "breached 1h ago") on every request

\- Every state change is logged in request history (audit trail)

\- Management dashboard with summary metrics and overdue identification

\- REST API (auto-documented via Swagger UI) + server-rendered web UI



\---



\## 2. Technology Stack



| Layer | Choice |

|---|---|

| Language | Python 3.14 |

| Framework | FastAPI 0.143 |

| ORM | SQLAlchemy 2.1 |

| Database | \*\*MariaDB 13.0\*\* (relational, as recommended) |

| DB Driver | PyMySQL |

| Templates | Jinja2 + Bootstrap 5 |

| Server | Uvicorn |

| Testing | Pytest + HTTPX |



\---



\## 3. Setup Instructions



\### Prerequisites

\- Python 3.10+

\- MariaDB 10.5+ (or MySQL 8+)



\### 3.1 Clone the repository

```bash

git clone https://github.com/allu121212/it\_service\_management.git

cd it\_service\_management

```



\### 3.2 Create virtual environment

```bash

python -m venv venv

venv\\Scripts\\activate        # Windows

\# source venv/bin/activate   # macOS / Linux

```



\### 3.3 Install dependencies

```bash

pip install -r requirements.txt

```



\### 3.4 Set up the database

Log into MariaDB as root:

```sql

CREATE DATABASE it\_service\_db CHARACTER SET utf8mb4;

CREATE USER 'ituser'@'localhost' IDENTIFIED BY 'StrongPass123';

GRANT ALL PRIVILEGES ON it\_service\_db.\* TO 'ituser'@'localhost';

FLUSH PRIVILEGES;

```



\### 3.5 Configure environment

Copy `.env.example` to `.env` and set the connection string:

```

DB\_URL=mysql+pymysql://ituser:StrongPass123@localhost:3306/it\_service\_db

```



\### 3.6 Seed initial data

Creates tables, categories, priorities (with SLA hours), and 4 realistic demo scenarios:

```bash

python -m app.seed

```



\### 3.7 Run the application

```bash

uvicorn app.main:app --reload

```



| URL | Purpose |

|---|---|

| http://127.0.0.1:8000/ | Web UI (dashboard) |

| http://127.0.0.1:8000/docs | Swagger API documentation |

| http://127.0.0.1:8000/health | Health check |



\### 3.8 Run automated tests

```bash

pytest -v

```

Expected: \*\*11 tests pass\*\* (positive, negative, and edge cases).



\---



\## 4. Database Design



\### Entities and relationships



```

users ─────────────┐

&#x20;                  │ (requester\_id)

&#x20;                  ▼

categories ──► requests ◄── priorities

&#x20;                  ▲

&#x20;                  │ (assignee\_id / resolved\_by)

&#x20;        ┌─────────┼──────────┐

&#x20;        │         │          │

&#x20; request\_history comments   users

```



\### Tables



| Table | Purpose | Key columns |

|---|---|---|

| `users` | Employees and IT staff | `id`, `email` (unique), `role`, `is\_available` |

| `categories` | Request categories (manageable) | `id`, `name` (unique) |

| `priorities` | Priority levels + SLA hours (configurable) | `id`, `name`, `sla\_hours` |

| `requests` | Core service requests | FKs to user/category/priority; status enum; timestamps; resolution |

| `request\_history` | Audit log of every event | `request\_id`, `event\_type`, `old\_value`, `new\_value`, `actor\_id`, `timestamp` |

| `comments` | Discussion thread on a request | `request\_id`, `author\_id`, `comment`, `created\_at` |



\### Integrity features

\- \*\*Primary keys\*\* on every table

\- \*\*Foreign keys\*\* with referential integrity

\- \*\*Unique constraints\*\* on `users.email`, `categories.name`, `priorities.name`

\- \*\*Indexes\*\* on `requests.status`, `requests.assignee\_id`, `requests.priority\_id`, `requests.created\_at` (fast filtering \& reports)

\- \*\*Enum type\*\* for `requests.status` — prevents invalid string values



\---



\## 5. API Documentation



All endpoints are documented interactively at `/docs` (Swagger UI).



| Method | Endpoint | Purpose |

|---|---|---|

| POST | `/api/requests` | Create a service request |

| GET | `/api/requests` | List requests (filters: `status`, `priority\_id`, `assignee\_id`, `unassigned`) |

| GET | `/api/requests/{id}` | Get one request with history + comments |

| POST | `/api/requests/{id}/assign` | Assign to IT staff |

| POST | `/api/requests/{id}/status` | Change status (validates transition) |

| POST | `/api/requests/{id}/resolve` | Resolve with mandatory resolution details |

| POST | `/api/requests/{id}/close` | Close a resolved request |

| POST | `/api/requests/{id}/comments` | Add comment |

| GET | `/api/reports/summary` | Dashboard summary metrics |

| GET | `/api/reports/overdue` | List SLA-breached open requests |



\---



\## 6. Business Rules



\### Status transitions (enforced server-side)

```

NEW         → ASSIGNED | ON\_HOLD

ASSIGNED    → IN\_PROGRESS | ON\_HOLD

IN\_PROGRESS → ON\_HOLD | RESOLVED

ON\_HOLD     → IN\_PROGRESS | ASSIGNED

RESOLVED    → CLOSED

CLOSED      → (terminal — no further changes)

```



\### Validation rules

\- Subject, description, category, priority are mandatory

\- Assignee must be an `it\_staff` user with `is\_available = true`

\- Cannot modify a CLOSED request

\- Cannot mark RESOLVED without `resolution\_details`

\- Cannot close a request that is not RESOLVED

\- Cannot move a request to its current status



\### SLA calculation

\- Deadline = `created\_at` + `priorities.sla\_hours`

\- States: `WITHIN\_SLA`, `APPROACHING` (≥75% elapsed), `BREACHED`, `RESOLVED\_WITHIN\_SLA`

\- SLA values are stored in the DB (`priorities.sla\_hours`) — \*\*changing them requires no code change\*\*

\- Live countdown displayed on dashboard and detail page



\---



\## 7. Assumptions



The challenge document explicitly lists ambiguities around SLA. Decisions made:



1\. \*\*SLA clock start:\*\* Clock starts at `created\_at`.

2\. \*\*Weekends included:\*\* Yes — SLA counts calendar time including weekends.

3\. \*\*Holidays included:\*\* Yes — no holiday calendar implemented.

4\. \*\*On Hold time counts:\*\* Yes — the clock keeps running during ON\_HOLD.

5\. \*\*Priority change:\*\* If priority changes, the SLA deadline is recalculated from the original `created\_at` using the new priority's SLA hours.

6\. \*\*SLA configuration change:\*\* Does not retroactively change existing deadlines (deadline computed on read).

7\. \*\*Closed requests cannot be reopened\*\* — for auditability. If needed, a new request should be created.

8\. \*\*No authentication:\*\* Not implemented as the challenge explicitly states "You are not expected to build enterprise-grade authentication during the challenge." `actor\_id` is passed explicitly in API calls to simulate the acting user.

9\. \*\*"Approaching SLA" threshold:\*\* 75% of the SLA duration elapsed.



\---



\## 8. Testing



\### Automated tests (`tests/test\_api.py`)



11 tests, all passing:



\*\*Positive scenarios:\*\*

\- Create request successfully

\- Full lifecycle (create → assign → in progress → comment → resolve → close)

\- History and comments returned correctly

\- Reports summary aggregation



\*\*Negative scenarios:\*\*

\- Create request with missing subject → 422

\- Create request with invalid requester → 400

\- Assign to non-IT user → 400

\- Invalid status transition (NEW → CLOSED) → 400

\- Resolve without resolution details → 422

\- Close unresolved request → 400

\- Modify closed request → 409



Run with:

```bash

pytest -v

```



\---



\## 9. Known Limitations



\- \*\*No authentication or authorization\*\* — `actor\_id` is passed explicitly. Documented as acceptable for challenge scope.

\- \*\*Reopening a closed request is not supported.\*\*

\- \*\*No pagination\*\* on the requests list — fine for small data volumes.

\- \*\*No email notifications\*\* when a request is assigned or updated.

\- \*\*SLA excludes holidays\*\* — only calendar time is used.

\- \*\*No file attachments\*\* on requests or comments.



\---



\## 10. Future Improvements



Given additional time:

1\. \*\*Authentication\*\* with JWT and role-based access (employee vs. IT staff vs. admin)

2\. \*\*Email/Slack notifications\*\* on assignment and status changes

3\. \*\*Pagination and filtering UI\*\* on the requests list

4\. \*\*Comments editable/deletable\*\* with edit history

5\. \*\*Attachments\*\* for screenshots/logs

6\. \*\*Business-hours-only SLA\*\* with a holiday calendar

7\. \*\*SLA countdown on all pages\*\* with auto-refresh

8\. \*\*Admin UI\*\* for managing categories, priorities, and SLA configuration

9\. \*\*Export reports\*\* to CSV/Excel

10\. \*\*Docker compose\*\* for one-command setup



\---



\## 11. Screenshots



\### Dashboard — All SLA States Visible

!\[Dashboard](docs/dashboard.png)



\### Request Detail Page — History, Comments, Actions

!\[Detail](docs/detail.png)



\### API Documentation (Swagger UI)

!\[Swagger](docs/swagger.png)



\### Automated Test Results (11 passing)

!\[Tests](docs/tests.png)



\---



\## 12. Author



Built during the Developer Hackathon.


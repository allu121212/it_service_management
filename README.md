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

\- Every state change is logged in request history

\- Management dashboard with summary metrics and overdue identification

\- Rest API (auto-documented via Swagger UI) + server-rendered web UI



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


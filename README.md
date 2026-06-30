# Shift Attendance Tracker

Internal Django tool for managing **student employee work attendance** (not academic/class attendance).

## Stack

- Django monolith (templates + Admin)
- SQLite
- django-htmx (for upcoming supervisor UI)
- WeasyPrint (for upcoming PDF export)

## Apps

| App | Purpose |
|-----|---------|
| `accounts` | Custom `User` with `role`, `building`, `manager` |
| `buildings` | Work locations / departments |
| `workers` | Student employees, attendance, notes, monthly scores |
| `budget` | Manager headcount budgets per building/period |

## Roles

- **Director** — full access via Admin
- **Manager** — sees supervisors and workers under their team
- **Supervisor** — sees only their assigned building

## Quick start

```powershell
cd shift-attendance-tracker
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py seed_demo_data
.\.venv\Scripts\python manage.py runserver
```

Open http://127.0.0.1:8000/

### Demo accounts

| Username | Password | Role | After login |
|----------|----------|------|-------------|
| `director` | `demo1234` | Director | Admin (full access) |
| `manager` | `demo1234` | Manager | Admin (team + budgets) |
| `supervisor_north` | `demo1234` | Supervisor | Admin (North Hall only) |
| `supervisor_south` | `demo1234` | Supervisor | Admin (South Hall only) |

Everyone uses the same **Unfold Admin** UI at `/admin/`. What you see is filtered by role.

`seed_demo_data` only inserts sample rows into the database (users, buildings, workers). Business rules live in `workers/services.py`, `config/permissions.py`, and Admin.

## Worker fields

- **POS #** (`position_number`) — position slot at that building, from the original spreadsheet "POS #" column (e.g. `1`, `2`). **Lead** (`is_lead`) marks team-lead slots (old sheet suffix `-L`).

## Development phases

1. **Models + Admin** — role-filtered querysets in Unfold Admin
2. **Supervisor daily work** — same Admin (no separate UI; keeps one visual style)
3. Budget dashboard
4. PDF export (WeasyPrint)
5. Audit log + permission hardening

## Create a superuser manually

```powershell
.\.venv\Scripts\python manage.py createsuperuser
```

Set `role` to `director` in Admin after creation.

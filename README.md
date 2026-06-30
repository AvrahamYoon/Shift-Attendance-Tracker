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

Open http://127.0.0.1:8000/admin/

### Demo accounts

| Username | Password | Role |
|----------|----------|------|
| `director` | `demo1234` | Director |
| `manager` | `demo1234` | Manager |
| `supervisor_north` | `demo1234` | Supervisor (North Hall) |
| `supervisor_south` | `demo1234` | Supervisor (South Hall) |

## Development phases

1. **Models + Admin** (current) — role-filtered querysets in Admin
2. Supervisor daily pages — HTMX forms
3. Budget dashboard
4. PDF export (WeasyPrint)
5. Audit log + permission hardening

## Create a superuser manually

```powershell
.\.venv\Scripts\python manage.py createsuperuser
```

Set `role` to `director` in Admin after creation.

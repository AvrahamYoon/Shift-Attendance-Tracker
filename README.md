# Shift Attendance Tracker

Internal Django app for **student employee work attendance** at BYU-Idaho (not class attendance). All roles use the same [django-unfold](https://github.com/unfoldadmin/django-unfold) Admin at `/admin/`; data is filtered by role.

## Stack

| Layer | Choice |
|-------|--------|
| Framework | Django 6 |
| UI | django-unfold (Admin) |
| Database | SQLite |
| Time zone | `America/Denver` (Mountain Time) |
| PDF | ReportLab (term & worker reports from Admin) |
| Planned | Budget dashboard, audit log |

## Apps

| App | Purpose |
|-----|---------|
| `accounts` | Custom `User` — role, manager, supervisor assignment via buildings |
| `buildings` | Work sites; each building has **one** supervisor |
| `workers` | Students, attendance, BYUI terms, notes, monthly scores |
| `budget` | Headcount budgets per building |
| `config` | Settings, role permissions, Unfold navigation |

## Roles & access

| Role | Access |
|------|--------|
| **Director** | Full Admin — users, buildings, all workers and attendance |
| **Manager** | Read team data; manage budgets for buildings their supervisors run |
| **Supervisor** | Workers, attendance, notes, and scores for **assigned buildings** only |

### Buildings & supervisors

- Each **building** has exactly **one** supervisor (`Building.supervisor`).
- A **supervisor** may manage **multiple buildings** (e.g. East + West Hall).
- A worker’s supervisor is always `worker.building.supervisor` — unambiguous on the Workers list.
- Directors assign supervisors on **Buildings** in Admin.

### Notes

- Creating a note requires choosing a **building** you’re allowed to access.
- **Worker** on a note is optional (building-level notes). If set, the worker must belong to that building.

## Quick start

```powershell
cd shift-attendance-tracker
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py sync_byui_terms
.\.venv\Scripts\python manage.py seed_demo_data
.\.venv\Scripts\python manage.py runserver
```

- Home: http://127.0.0.1:8000/
- Sign in: http://127.0.0.1:8000/accounts/login/ → redirects to Admin

### Demo accounts

Password for all: `demo1234`

| Username | Role | Buildings |
|----------|------|-----------|
| `director` | Director | All |
| `manager` | Manager | Team overview |
| `supervisor_north` | Supervisor | North Hall |
| `supervisor_south` | Supervisor | South Hall |
| `supervisor_multi` | Supervisor | East Hall + West Hall |

`seed_demo_data` only inserts sample rows. Business rules live in `config/permissions.py`, `workers/attendance.py`, and Admin/forms.

## Attendance

### Categories & limits (per BYUI semester)

| Category | Limit | Counting |
|----------|-------|----------|
| Absence | 4 | **By day** — duplicate dates on the same day count once |
| Tardy | 4 | Per record |
| No show | 1 | Per record |

Saving a record assigns the matching **Term** from the record date (gaps between
semesters count toward the **previous** term) and shows **warnings** when limits
are reached or exceeded (records are not blocked).

### Workers list

- Columns: **Absences**, **Tardy**, **No show** with color badges (green / orange / red by usage).
- **Alert** column when any category is over the term limit.
- **Status** filter defaults to **Active**; use **Inactive** or **All** to find past employees.
- Use **Mark inactive** (bulk action) when someone leaves — do not delete unless you are a Director and need to remove bad data. Inactive workers keep all attendance history.

### Term selector

Use the **Viewing term** dropdown on the Admin home page or Workers list. Badges, worker summaries, and PDF exports follow the selected term. Recording attendance still uses each record's date.

### Per-term rosters (from Spring 2026)

Each BYUI semester has its own worker roster (`WorkerTermEnrollment`). **Fall 2025** and **Winter 2026** have no roster — the Workers list is empty for those terms. Rosters start at **Spring 2026**; when a new term is synced, active employees inherit from the previous term automatically.

### Deleting

On list pages (Attendance, Buildings, Workers, Notes, Budgets): select rows → **Delete** appears above the bottom edge (requires delete permission).

### PDF export

From **Workers** in Admin:

- **Export PDF** (top right on the list) — term attendance for all workers you can see, plus budget overview for your buildings.
- **Export PDF** (on a worker’s detail page) — that worker’s term summary and attendance records.

Reports use the **selected viewing term** from the Admin dropdown.

## BYUI academic terms

Terms follow the [BYU-Idaho academic calendar](https://www.byui.edu/academic-calendar/) (Fall, Winter, Spring, and Summer Session when applicable).

```powershell
.\.venv\Scripts\python manage.py sync_byui_terms
```

Example: **Winter 2026** = Jan 7 – Apr 9, 2026; **Spring 2026** = Apr 20 – Jul 22, 2026; **Summer 2026** = Jul 27 – Sep 9, 2026.

Directors can also edit terms under **Workers → Terms**.

## Worker fields

| Field | Meaning |
|-------|---------|
| **Building** | Work site / department |
| **Shift** | e.g. `4:30-7:30 AM` |
| **Term status** | Staying / Leaving / New — employment intent, **not** the BYUI academic term |

## Project layout (logic)

| Path | Role |
|------|------|
| `config/permissions.py` | `accessible_buildings()`, role queryset filters |
| `workers/attendance.py` | Term limits, day-based absence counts, warnings |
| `workers/byui_terms.py` | Official semester date ranges |
| `workers/forms.py` | Scoped forms (worker, building, notes) |
| `workers/admin.py` | Unfold Admin for workers & attendance |

## Manual superuser

```powershell
.\.venv\Scripts\python manage.py createsuperuser
```

Set **role** to `director` and assign buildings on the **Buildings** screen as needed.

## Roadmap

1. Budget dashboard (quota vs actual headcount)
2. Audit log and permission hardening

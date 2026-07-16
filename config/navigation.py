"""Role-aware Unfold sidebar navigation."""

from django.urls import reverse_lazy


def _role(request):
    return getattr(request.user, "role", None)


def can_see_daily_ops(request):
    return request.user.is_authenticated and request.user.is_staff


def can_see_buildings(request):
    return can_see_daily_ops(request)


def can_see_budgets(request):
    # Supervisors need Budgets to see their building allocation/variance.
    return can_see_daily_ops(request)


def can_see_terms(request):
    return can_see_daily_ops(request)


def can_see_users(request):
    return can_see_daily_ops(request)


def users_nav_title(request):
    from accounts.models import Role

    if _role(request) == Role.SUPERVISOR:
        return "My account"
    return "Users"


def get_sidebar_navigation(request):
    daily_items = [
        {
            "title": "Workers",
            "icon": "groups",
            "link": reverse_lazy("admin:workers_worker_changelist"),
            "permission": can_see_daily_ops,
        },
        {
            "title": "Attendance",
            "icon": "event_busy",
            "link": reverse_lazy("admin:workers_attendancerecord_changelist"),
            "permission": can_see_daily_ops,
        },
        {
            "title": "Notes",
            "icon": "sticky_note_2",
            "link": reverse_lazy("admin:workers_note_changelist"),
            "permission": can_see_daily_ops,
        },
        {
            "title": "Monthly scores",
            "icon": "grade",
            "link": reverse_lazy("admin:workers_monthlyscore_changelist"),
            "permission": can_see_daily_ops,
        },
    ]

    org_items = [
        {
            "title": "Buildings",
            "icon": "apartment",
            "link": reverse_lazy("admin:buildings_building_changelist"),
            "permission": can_see_buildings,
        },
        {
            "title": "Budgets",
            "icon": "account_balance_wallet",
            "link": reverse_lazy("admin:budget_budget_changelist"),
            "permission": can_see_budgets,
        },
        {
            "title": "Terms",
            "icon": "calendar_month",
            "link": reverse_lazy("admin:workers_term_changelist"),
            "permission": can_see_terms,
        },
        {
            "title": users_nav_title(request),
            "icon": "manage_accounts",
            "link": reverse_lazy("admin:accounts_user_changelist"),
            "permission": can_see_users,
        },
    ]

    return [
        {
            "title": "Daily operations",
            "separator": True,
            "items": daily_items,
        },
        {
            "title": "Organization",
            "separator": True,
            "items": org_items,
        },
    ]

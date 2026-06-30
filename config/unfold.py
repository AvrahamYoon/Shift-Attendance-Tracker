from django.templatetags.static import static
from django.urls import reverse_lazy

UNFOLD = {
    "SITE_TITLE": "Shift Attendance",
    "SITE_HEADER": "Attendance Tracker",
    "SITE_SUBHEADER": "Student employee work attendance",
    "SITE_URL": "/",
    "SITE_SYMBOL": "fact_check",
    "SHOW_HISTORY": True,
    "SHOW_BACK_BUTTON": True,
    "BORDER_RADIUS": "8px",
    "COLORS": {
        "primary": {
            "50": "oklch(97.4% .014 244.7)",
            "100": "oklch(93.8% .032 245.0)",
            "200": "oklch(88.2% .057 243.5)",
            "300": "oklch(79.2% .093 242.4)",
            "400": "oklch(68.8% .131 241.3)",
            "500": "oklch(58.8% .158 241.1)",
            "600": "oklch(51.2% .165 241.0)",
            "700": "oklch(44.8% .145 241.2)",
            "800": "oklch(38.6% .118 242.0)",
            "900": "oklch(33.6% .094 243.2)",
            "950": "oklch(23.8% .072 244.5)",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Daily operations",
                "separator": True,
                "items": [
                    {
                        "title": "Workers",
                        "icon": "groups",
                        "link": reverse_lazy("admin:workers_worker_changelist"),
                    },
                    {
                        "title": "Attendance",
                        "icon": "event_busy",
                        "link": reverse_lazy(
                            "admin:workers_attendancerecord_changelist"
                        ),
                    },
                    {
                        "title": "Notes",
                        "icon": "sticky_note_2",
                        "link": reverse_lazy("admin:workers_note_changelist"),
                    },
                    {
                        "title": "Monthly scores",
                        "icon": "grade",
                        "link": reverse_lazy("admin:workers_monthlyscore_changelist"),
                    },
                ],
            },
            {
                "title": "Organization",
                "separator": True,
                "items": [
                    {
                        "title": "Buildings",
                        "icon": "apartment",
                        "link": reverse_lazy("admin:buildings_building_changelist"),
                    },
                    {
                        "title": "Budgets",
                        "icon": "account_balance_wallet",
                        "link": reverse_lazy("admin:budget_budget_changelist"),
                    },
                    {
                        "title": "Terms",
                        "icon": "calendar_month",
                        "link": reverse_lazy("admin:workers_term_changelist"),
                    },
                    {
                        "title": "Users",
                        "icon": "manage_accounts",
                        "link": reverse_lazy("admin:accounts_user_changelist"),
                    },
                ],
            },
        ],
    },
    "STYLES": [
        lambda request: static("css/custom.css"),
    ],
}

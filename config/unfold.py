from django.templatetags.static import static

from config.navigation import get_sidebar_navigation

UNFOLD = {
    "SITE_TITLE": "Shift Attendance",
    "SITE_HEADER": "Attendance Tracker",
    "SITE_SUBHEADER": "Student employee work attendance",
    "SITE_URL": "/",
    "SITE_SYMBOL": "fact_check",
    "SHOW_HISTORY": True,
    "SHOW_BACK_BUTTON": True,
    "BORDER_RADIUS": "10px",
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
        "navigation": get_sidebar_navigation,
    },
    "STYLES": [
        lambda request: static("css/custom.css"),
    ],
}

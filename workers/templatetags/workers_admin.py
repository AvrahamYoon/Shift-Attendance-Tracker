from django import template

from workers.models import Term

register = template.Library()


@register.simple_tag
def current_term_banner():
    """Return current BYUI term (with gap fallback) for admin banner."""
    return Term.current()

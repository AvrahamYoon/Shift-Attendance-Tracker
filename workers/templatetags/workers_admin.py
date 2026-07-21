from django import template
from django.urls import reverse

from workers.term_context import available_terms, get_view_term
from workers.models import Term

register = template.Library()


@register.inclusion_tag("admin/helpers/term_selector.html", takes_context=True)
def term_selector(context, compact=False):
    request = context["request"]
    view_term = get_view_term(request)
    current_term = Term.current()
    return {
        "view_term": view_term,
        "current_term": current_term,
        "terms": available_terms(),
        "set_term_url": reverse("workers_set_view_term"),
        "next_url": request.get_full_path(),
        "compact": compact,
    }

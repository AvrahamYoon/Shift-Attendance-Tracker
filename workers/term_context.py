"""Session-backed BYUI term selection for admin views and reports."""

from workers.models import Term

SESSION_KEY = "admin_view_term_id"


def get_view_term(request):
    """Term used for list badges, summaries, and PDF export."""
    if request is not None:
        term_id = request.GET.get("term")
        if term_id:
            term = Term.objects.filter(pk=term_id).first()
            if term:
                return term
        session_id = request.session.get(SESSION_KEY)
        if session_id:
            term = Term.objects.filter(pk=session_id).first()
            if term:
                return term
    return Term.current()


def set_view_term(request, term_id):
    """Persist selected term in session; pass None/'' to reset to current."""
    if term_id in (None, ""):
        request.session.pop(SESSION_KEY, None)
        return Term.current()
    term = Term.objects.filter(pk=term_id).first()
    if term:
        request.session[SESSION_KEY] = term.pk
        return term
    return get_view_term(request)


def available_terms():
    return Term.objects.order_by("-start_date")

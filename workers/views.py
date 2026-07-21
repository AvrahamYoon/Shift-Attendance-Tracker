from django.shortcuts import redirect
from django.urls import reverse

from workers.term_context import set_view_term


def set_view_term_view(request):
    if request.method != "POST":
        return redirect(reverse("admin:index"))

    term_id = request.POST.get("term")
    set_view_term(request, term_id or None)
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER")
    if not next_url:
        next_url = reverse("admin:index")
    return redirect(next_url)

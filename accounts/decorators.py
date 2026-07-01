from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from accounts.models import Role


def role_required(*roles):
    """Restrict a view to users with one of the given roles."""

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def supervisor_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.role != Role.SUPERVISOR:
            raise PermissionDenied
        if not request.user.buildings.exists():
            raise PermissionDenied("Supervisor account has no buildings assigned.")
        return view_func(request, *args, **kwargs)

    return wrapper

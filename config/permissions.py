"""Role-based queryset filters shared by admin and views."""

from accounts.models import Role
from buildings.models import Building


def has_director_access(user):
    return user.is_authenticated and (
        user.is_superuser or user.role == Role.DIRECTOR
    )


def accessible_buildings(user):
    """Buildings the user may view or act on."""
    if not user.is_authenticated:
        return Building.objects.none()
    if has_director_access(user):
        return Building.objects.all()
    if user.role == Role.SUPERVISOR:
        return Building.objects.filter(supervisor=user)
    if user.role == Role.MANAGER:
        return Building.objects.filter(supervisor__manager=user).distinct()
    return Building.objects.none()


def user_can_access_building(user, building):
    if building is None:
        return False
    return accessible_buildings(user).filter(pk=building.pk).exists()


def filter_workers(qs, user):
    if not user.is_authenticated:
        return qs.none()
    if has_director_access(user):
        return qs
    return qs.filter(building__in=accessible_buildings(user))


def filter_by_worker_relation(qs, user, worker_path="worker"):
    if not user.is_authenticated:
        return qs.none()
    if has_director_access(user):
        return qs
    return qs.filter(**{f"{worker_path}__building__in": accessible_buildings(user)})


def filter_buildings(qs, user):
    if not user.is_authenticated:
        return qs.none()
    if has_director_access(user):
        return qs
    return qs.filter(pk__in=accessible_buildings(user).values("pk"))


def filter_supervisors(qs, user):
    qs = qs.filter(role=Role.SUPERVISOR)
    if not user.is_authenticated:
        return qs.none()
    if has_director_access(user):
        return qs
    if user.role == Role.MANAGER:
        return qs.filter(manager=user)
    if user.role == Role.SUPERVISOR:
        return qs.filter(pk=user.pk)
    return qs.none()


def filter_notes(qs, user):
    if not user.is_authenticated:
        return qs.none()
    if has_director_access(user):
        return qs
    return qs.filter(building__in=accessible_buildings(user))


def filter_budgets(qs, user):
    if not user.is_authenticated:
        return qs.none()
    if has_director_access(user):
        return qs
    return qs.filter(building__in=accessible_buildings(user))

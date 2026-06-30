"""Role-based queryset filters shared by admin and views."""


def filter_workers(qs, user):
    if not user.is_authenticated:
        return qs.none()
    if user.role == "supervisor":
        return qs.filter(building=user.building)
    if user.role == "manager":
        return qs.filter(supervisor__manager=user)
    return qs


def filter_by_worker_relation(qs, user, worker_path="worker"):
    if not user.is_authenticated:
        return qs.none()
    if user.role == "supervisor":
        return qs.filter(**{f"{worker_path}__building": user.building})
    if user.role == "manager":
        return qs.filter(**{f"{worker_path}__supervisor__manager": user})
    return qs


def filter_buildings(qs, user):
    if not user.is_authenticated:
        return qs.none()
    if user.role == "supervisor":
        if user.building_id:
            return qs.filter(pk=user.building_id)
        return qs.none()
    if user.role == "manager":
        return qs.filter(workers__supervisor__manager=user).distinct()
    return qs


def filter_supervisors(qs, user):
    from accounts.models import Role

    qs = qs.filter(role=Role.SUPERVISOR)
    if not user.is_authenticated:
        return qs.none()
    if user.role == "manager":
        return qs.filter(manager=user)
    if user.role == "supervisor":
        return qs.filter(pk=user.pk)
    return qs


def filter_notes(qs, user):
    if not user.is_authenticated:
        return qs.none()
    if user.role == "supervisor":
        return qs.filter(building=user.building)
    if user.role == "manager":
        return qs.filter(
            building__workers__supervisor__manager=user
        ).distinct()
    return qs


def filter_budgets(qs, user):
    if not user.is_authenticated:
        return qs.none()
    if user.role == "supervisor":
        return qs.filter(supervisor=user)
    if user.role == "manager":
        return qs.filter(supervisor__manager=user)
    return qs

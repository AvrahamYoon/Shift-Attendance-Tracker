from django.core.management.base import BaseCommand

from accounts.models import Role, User
from buildings.models import Building
from budget.models import Budget
from workers.byui_terms import sync_byui_terms
from workers.models import Term, Worker, WorkerStatus, WorkerTermEnrollment
from workers.roster import ROSTER_START_TERM_NAME, sync_worker_enrollment, term_has_roster


class Command(BaseCommand):
    """Insert sample buildings, users, and workers for local development only."""

    help = "Create demo users, buildings, and sample workers for local development."

    def _supervisor(self, username, manager, **defaults):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "role": Role.SUPERVISOR,
                "manager": manager,
                "is_staff": True,
                **defaults,
            },
        )
        if created:
            user.set_password("demo1234")
            user.save()
        return user

    def handle(self, *args, **options):
        buildings = {
            "north": Building.objects.get_or_create(
                name="North Hall",
                defaults={"address": "100 Campus Dr"},
            )[0],
            "south": Building.objects.get_or_create(
                name="South Hall",
                defaults={"address": "200 Campus Dr"},
            )[0],
            "east": Building.objects.get_or_create(
                name="East Hall",
                defaults={"address": "300 Campus Dr"},
            )[0],
            "west": Building.objects.get_or_create(
                name="West Hall",
                defaults={"address": "400 Campus Dr"},
            )[0],
        }

        sync_byui_terms(Term)

        director, created = User.objects.get_or_create(
            username="director",
            defaults={
                "first_name": "Dana",
                "last_name": "Director",
                "email": "director@example.com",
                "role": Role.DIRECTOR,
                "is_staff": True,
            },
        )
        if created:
            director.set_password("demo1234")
            director.save()

        manager, created = User.objects.get_or_create(
            username="manager",
            defaults={
                "first_name": "Morgan",
                "last_name": "Manager",
                "email": "manager@example.com",
                "role": Role.MANAGER,
                "is_staff": True,
            },
        )
        if created:
            manager.set_password("demo1234")
            manager.save()

        sup_north = self._supervisor(
            "supervisor_north",
            manager,
            first_name="Sam",
            last_name="Supervisor",
            email="north@example.com",
        )
        sup_south = self._supervisor(
            "supervisor_south",
            manager,
            first_name="Sydney",
            last_name="Supervisor",
            email="south@example.com",
        )
        sup_multi = self._supervisor(
            "supervisor_multi",
            manager,
            first_name="Taylor",
            last_name="Supervisor",
            email="multi@example.com",
        )

        buildings["north"].supervisor = sup_north
        buildings["north"].save(update_fields=["supervisor"])
        buildings["south"].supervisor = sup_south
        buildings["south"].save(update_fields=["supervisor"])
        for key in ("east", "west"):
            buildings[key].supervisor = sup_multi
            buildings[key].save(update_fields=["supervisor"])

        User.objects.filter(
            username__in=("supervisor_east", "supervisor_west")
        ).delete()

        workers = [
            {
                "name": "Alex Student",
                "i_number": "I12345678",
                "building": buildings["north"],
                "shift": "4:30-7:30 AM",
            },
            {
                "name": "Blake Student",
                "i_number": "I23456789",
                "building": buildings["north"],
                "shift": "4:30-7:30 AM",
            },
            {
                "name": "Casey Student",
                "i_number": "I34567890",
                "building": buildings["south"],
                "shift": "7:30-10:30 AM",
            },
            {
                "name": "Drew Student",
                "i_number": "I45678901",
                "building": buildings["east"],
                "shift": "8:00-11:00 AM",
            },
            {
                "name": "Emery Student",
                "i_number": "I56789012",
                "building": buildings["west"],
                "shift": "1:00-4:00 PM",
            },
        ]
        for data in workers:
            worker, _ = Worker.objects.get_or_create(
                i_number=data["i_number"],
                defaults={**data, "status": WorkerStatus.ACTIVE},
            )
            spring = Term.objects.filter(name=ROSTER_START_TERM_NAME).first()
            if spring and term_has_roster(spring):
                sync_worker_enrollment(
                    worker,
                    spring,
                    building=worker.building,
                    shift=worker.shift,
                    term_status=worker.term_status,
                    status=worker.status,
                )

        for building, headcount in (
            (buildings["north"], 3),
            (buildings["south"], 2),
            (buildings["east"], 2),
            (buildings["west"], 2),
        ):
            Budget.objects.update_or_create(
                building=building,
                defaults={
                    "allocated_headcount": headcount,
                    "set_by": manager,
                },
            )

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self.stdout.write("Log in at /admin/ with:")
        self.stdout.write("  director / demo1234")
        self.stdout.write("  manager / demo1234")
        self.stdout.write("  supervisor_north / demo1234   (North Hall)")
        self.stdout.write("  supervisor_south / demo1234   (South Hall)")
        self.stdout.write("  supervisor_multi / demo1234   (East + West Hall)")

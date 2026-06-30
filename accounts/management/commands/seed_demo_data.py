from django.core.management.base import BaseCommand

from accounts.models import Role, User
from buildings.models import Building
from budget.models import Budget
from workers.models import Worker, WorkerStatus


class Command(BaseCommand):
    help = "Create demo users, buildings, and sample workers for local development."

    def handle(self, *args, **options):
        building_a, _ = Building.objects.get_or_create(
            name="North Hall",
            defaults={"address": "100 Campus Dr"},
        )
        building_b, _ = Building.objects.get_or_create(
            name="South Hall",
            defaults={"address": "200 Campus Dr"},
        )

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

        sup_north, created = User.objects.get_or_create(
            username="supervisor_north",
            defaults={
                "first_name": "Sam",
                "last_name": "Supervisor",
                "email": "north@example.com",
                "role": Role.SUPERVISOR,
                "building": building_a,
                "manager": manager,
                "is_staff": True,
            },
        )
        if created:
            sup_north.set_password("demo1234")
            sup_north.save()

        sup_south, created = User.objects.get_or_create(
            username="supervisor_south",
            defaults={
                "first_name": "Sydney",
                "last_name": "Supervisor",
                "email": "south@example.com",
                "role": Role.SUPERVISOR,
                "building": building_b,
                "manager": manager,
                "is_staff": True,
            },
        )
        if created:
            sup_south.set_password("demo1234")
            sup_south.save()

        workers = [
            {
                "name": "Alex Student",
                "i_number": "I12345678",
                "building": building_a,
                "position_number": "1",
                "is_lead": True,
                "shift": "4:30-7:30 AM",
            },
            {
                "name": "Blake Student",
                "i_number": "I23456789",
                "building": building_a,
                "position_number": "2",
                "shift": "4:30-7:30 AM",
            },
            {
                "name": "Casey Student",
                "i_number": "I34567890",
                "building": building_b,
                "position_number": "1",
                "shift": "7:30-10:30 AM",
            },
        ]
        for data in workers:
            Worker.objects.get_or_create(
                i_number=data["i_number"],
                defaults={**data, "status": WorkerStatus.ACTIVE},
            )

        for building, headcount in ((building_a, 3), (building_b, 2)):
            Budget.objects.get_or_create(
                building=building,
                period="2026-07",
                defaults={
                    "allocated_headcount": headcount,
                    "set_by": manager,
                },
            )

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self.stdout.write("Log in at /admin/ with:")
        self.stdout.write("  director / demo1234")
        self.stdout.write("  manager / demo1234")
        self.stdout.write("  supervisor_north / demo1234")
        self.stdout.write("  supervisor_south / demo1234")

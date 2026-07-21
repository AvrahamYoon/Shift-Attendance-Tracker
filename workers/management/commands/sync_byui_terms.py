from django.core.management.base import BaseCommand

from workers.byui_terms import sync_byui_terms
from workers.models import Term


class Command(BaseCommand):
    help = "Load BYU-Idaho full-semester dates into the Terms table."

    def handle(self, *args, **options):
        created, inherited = sync_byui_terms(Term)
        self.stdout.write(
            self.style.SUCCESS(
                f"BYUI terms synced ({len(Term.objects.all())} total, "
                f"{created} new, {inherited} roster rows inherited)."
            )
        )

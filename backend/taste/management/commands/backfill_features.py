from django.core.management.base import BaseCommand

from taste.services import backfill_features


class Command(BaseCommand):
    help = "Create heuristic taste features for all catalog titles."

    def handle(self, *args, **options):
        created, updated = backfill_features()
        self.stdout.write(
            self.style.SUCCESS(f"Features: {created} created, {updated} updated")
        )

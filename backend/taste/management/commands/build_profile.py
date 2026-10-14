from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from taste.services import build_profile


class Command(BaseCommand):
    help = "Rebuild ratings-based taste preferences for all users."

    def handle(self, *args, **options):
        total = 0
        for user in get_user_model().objects.all():
            total += build_profile(user)
        self.stdout.write(self.style.SUCCESS(f"Rebuilt {total} preferences"))

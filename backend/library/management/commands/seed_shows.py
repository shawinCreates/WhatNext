import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import Show
from library.models import UserShow, LibraryStatus


class Command(BaseCommand):
    help = "Seed library UserShow entries from the show seed CSV"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            type=str,
            default=".kilo/plans/1793780438151-shows-seed-data.csv",
            help="Path to the show seed CSV file",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be seeded without writing",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv"])
        if not csv_path.is_absolute():
            csv_path = Path(__file__).resolve().parents[4] / csv_path

        if not csv_path.exists():
            self.stderr.write(f"CSV not found: {csv_path}")
            return

        from django.contrib.auth import get_user_model
        User = get_user_model()
        user, _ = User.objects.get_or_create(
            username="owner",
            defaults={"is_staff": True, "is_superuser": True},
        )

        # Build lookup: (title_lower, year) -> Show
        catalog = {}
        for s in Show.objects.all():
            key = (s.name.strip().lower(), s.release_year)
            catalog.setdefault(key, []).append(s)

        created = 0
        updated = 0
        skipped = 0
        missing = []

        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                num = int(row["#"])
                title = row["Show Name"].strip()
                year = int(row["Year"]) if row["Year"] else None
                watched = row["Watched"].strip().lower() == "y"
                my_rating = row["My Rating"].strip()
                favorit = row["Favorit"].strip().lower() == "y"
                note = row["Note"].strip()

                if not watched:
                    skipped += 1
                    continue

                rating = float(my_rating) if my_rating else None

                # Look up show in catalog
                matches = catalog.get((title.lower(), year), [])
                if not matches:
                    matches = [
                        s
                        for (t, y), ss in catalog.items()
                        if y == year and title.lower() in t
                        for s in ss
                    ]
                if not matches:
                    missing.append((num, title, year))
                    skipped += 1
                    continue

                show = matches[0]

                if options["dry_run"]:
                    self.stdout.write(
                        f"[dry-run] {num}: {title} ({year}) -> show_id={show.id} rating={rating} fav={favorit}"
                    )
                    created += 1
                    continue

                with transaction.atomic():
                    entry, was_created = UserShow.objects.update_or_create(
                        user=user,
                        show=show,
                        defaults={
                            "status": LibraryStatus.WATCHED,
                            "rating": rating,
                            "is_favorite": favorit,
                            "personal_note": note,
                        },
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1

        if options["dry_run"]:
            self.stdout.write(
                f"\nDry-run complete: would seed {created} shows, {skipped} skipped, {len(missing)} missing"
            )
        else:
            self.stdout.write(
                f"\nSeed complete: {created} created, {updated} updated, {skipped} skipped"
            )

        if missing:
            self.stdout.write(self.style.WARNING(f"\n{len(missing)} shows NOT found in catalog:"))
            for num, title, year in missing:
                self.stdout.write(f"  #{num}: {title} ({year})")

        # Best effort: enrich credits and embeddings if possible
        try:
            from django.core.management import call_command

            self.stdout.write("Enriching credits/embeddings (best effort)...")
            call_command("backfill_credits", "--shows-only", "--limit", "500", verbosity=0)
            call_command("embed_catalog", "--shows-only", "--limit", "500", verbosity=0)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Enrichment skipped: {e}"))


# Optional post-seed enrichment (best effort)
try:
    from django.core.management import call_command
except Exception:
    call_command = None

from django.core.management.base import BaseCommand

from catalog.embeddings import embed_title, get_embedding_service
from catalog.models import Movie, Show


class Command(BaseCommand):
    help = "Generate embeddings for catalog movies and shows"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Regenerate all embeddings")
        parser.add_argument("--movies-only", action="store_true")
        parser.add_argument("--shows-only", action="store_true")
        parser.add_argument("--limit", type=int, default=0)

    def handle(self, *args, **options):
        force = options["force"]
        svc = get_embedding_service()
        self.stdout.write(f"Embedding backend: {svc.backend} ({svc.model_name}, dim={svc.dim})")

        updated = 0
        if not options["shows_only"]:
            qs = Movie.objects.all()
            if not force:
                qs = qs.filter(embedding__isnull=True)
            if options["limit"]:
                qs = qs[: options["limit"]]
            for movie in qs:
                try:
                    embed_title(movie, save=True)
                    updated += 1
                    if updated % 10 == 0:
                        self.stdout.write(f"  movies: {updated}")
                except Exception as e:
                    self.stderr.write(f"Error embedding movie {movie.id}: {e}")

        if not options["movies_only"]:
            qs = Show.objects.all()
            if not force:
                qs = qs.filter(embedding__isnull=True)
            if options["limit"]:
                qs = qs[: options["limit"]]
            for show in qs:
                try:
                    embed_title(show, save=True)
                    updated += 1
                    if updated % 10 == 0:
                        self.stdout.write(f"  shows: {updated}")
                except Exception as e:
                    self.stderr.write(f"Error embedding show {show.id}: {e}")

        self.stdout.write(self.style.SUCCESS(f"Embedded {updated} titles"))

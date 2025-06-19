from django.core.management.base import BaseCommand, CommandError
import logging

from core.services.western_ecuador_stats import (
    precalculate_all_stats, 
    clear_all_cached_stats,
    ALLOWED_BENCHMARK_COLLECTIONS
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Pre-calculate western Ecuador summary statistics for all benchmark collections'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recalculation even if cached values exist',
        )
        parser.add_argument(
            '--collection',
            type=str,
            help='Calculate stats for specific collection only',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all cached statistics before calculating',
        )

    def handle(self, *args, **options):
        # Validate collection option
        if options['collection'] and options['collection'] not in ALLOWED_BENCHMARK_COLLECTIONS:
            raise CommandError(f"Invalid collection: {options['collection']}")

        collections_to_process = [options['collection']] if options['collection'] else ALLOWED_BENCHMARK_COLLECTIONS

        self.stdout.write(f"Starting pre-calculation for {len(collections_to_process)} collections...")

        # Clear cache if requested
        if options['clear']:
            cleared_count = clear_all_cached_stats()
            self.stdout.write(f"Cleared {cleared_count} cached statistics")

        # Pre-calculate statistics
        try:
            results = precalculate_all_stats(
                force_recalculate=options['force'],
                collection_filter=options['collection']
            )

            # Print individual results as we go
            for collection_id in collections_to_process:
                # This is a simplified way to show progress since the service doesn't provide per-item feedback
                # In practice, you might want to modify the service to yield progress
                pass

            # Summary
            self.stdout.write("\n" + "="*50)
            self.stdout.write(f"Pre-calculation completed:")
            self.stdout.write(f"  Successful: {results['successful']}")
            self.stdout.write(f"  Failed: {results['failed']}")
            self.stdout.write(f"  Skipped: {results['skipped']}")
            self.stdout.write(f"  Total: {len(collections_to_process)}")

            if results['failed'] > 0:
                self.stdout.write(
                    self.style.WARNING("Some calculations failed. Check logs for details.")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS("All calculations completed successfully!")
                )

        except Exception as e:
            raise CommandError(f"Pre-calculation failed: {e}")
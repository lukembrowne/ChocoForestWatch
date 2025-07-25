from django.core.management.base import BaseCommand, CommandError
import logging

from core.services.western_ecuador_stats import (
    precalculate_all_stats, 
    clear_all_cached_stats,
    get_allowed_datasets
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Pre-calculate western Ecuador summary statistics for all benchmark collections using simplified calculation for pre-processed datasets'

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
        parser.add_argument(
            '--test-first',
            action='store_true',
            help='Test with first collection only to verify setup',
        )
        parser.add_argument(
            '--db-host',
            type=str,
            choices=['local', 'remote'],
            required=True,
            help='Database host configuration: "local" for Docker environment, "remote" for external database',
        )

    def handle(self, *args, **options):
        # Get current allowed collections
        allowed_collections = get_allowed_datasets()
        
        # Validate collection option
        if options['collection'] and options['collection'] not in allowed_collections:
            raise CommandError(f"Invalid collection: {options['collection']}")

        if options['test_first']:
            collections_to_process = [allowed_collections[0]]  # First collection only
            self.stdout.write(self.style.WARNING("🧪 Test mode: Processing first collection only"))
        elif options['collection']:
            collections_to_process = [options['collection']]
        else:
            collections_to_process = allowed_collections

        self.stdout.write(f"Starting pre-calculation for {len(collections_to_process)} collections...")

        # Clear cache if requested
        if options['clear']:
            cleared_count = clear_all_cached_stats()
            self.stdout.write(f"Cleared {cleared_count} cached statistics")

        # Pre-calculate statistics
        try:
            self.stdout.write(self.style.SUCCESS("🚀 Starting pre-calculation process with simplified mode..."))
            self.stdout.write("✨ Using optimized calculation for pre-processed datasets")
            self.stdout.write("💡 Tip: You can monitor detailed progress in the Django logs")
            self.stdout.write("")
            
            results = precalculate_all_stats(
                force_recalculate=options['force'],
                collection_filter=options['collection'],
                db_host=options['db_host']
            )

            # Summary
            self.stdout.write("\n" + "="*60)
            self.stdout.write(self.style.SUCCESS("🏁 Pre-calculation Results:"))
            self.stdout.write(f"  ✅ Successful: {results['successful']}")
            self.stdout.write(f"  ❌ Failed: {results['failed']}")
            self.stdout.write(f"  ⏭️  Skipped: {results['skipped']}")
            self.stdout.write(f"  📊 Total: {len(collections_to_process)}")

            if results['failed'] > 0:
                self.stdout.write("")
                self.stdout.write(
                    self.style.WARNING("⚠️  Some calculations failed. Check Django logs above for details.")
                )
                self.stdout.write(
                    "💡 Common issues: TiTiler service down, network timeouts, or invalid boundary data"
                )
            elif results['successful'] > 0:
                self.stdout.write("")
                self.stdout.write(
                    self.style.SUCCESS("🎉 All simplified calculations completed successfully!")
                )
                self.stdout.write(
                    "✨ Western Ecuador statistics are now cached and ready for instant access"
                )
                self.stdout.write(
                    "🚀 Benefiting from optimized calculation for pre-processed datasets"
                )
            else:
                self.stdout.write("")
                self.stdout.write(
                    self.style.WARNING("📋 All statistics were already cached. Use --force to recalculate.")
                )

        except Exception as e:
            self.stdout.write("")
            self.stdout.write(self.style.ERROR(f"💥 Pre-calculation failed: {e}"))
            self.stdout.write("💡 Check that TITILER_URL and BOUNDARY_GEOJSON_PATH environment variables are set correctly")
            raise CommandError(f"Pre-calculation failed: {e}")
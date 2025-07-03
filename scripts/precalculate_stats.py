#!/usr/bin/env python3
"""
Standalone script to pre-calculate western Ecuador statistics.
This can be run from the project root directory.

Usage:
    python scripts/precalculate_stats.py
    python scripts/precalculate_stats.py --force
    python scripts/precalculate_stats.py --collection datasets-hansen-tree-cover-2022
"""

import os
import sys
import argparse
import django
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent / "backend" / "djangocfw"
sys.path.insert(0, str(backend_dir))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangocfw.settings')
django.setup()

# Now we can import Django modules
from core.services.western_ecuador_stats import (
    precalculate_all_stats, 
    clear_all_cached_stats,
    ALLOWED_BENCHMARK_COLLECTIONS
)


def main():
    parser = argparse.ArgumentParser(description='Pre-calculate western Ecuador summary statistics')
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force recalculation even if cached values exist'
    )
    parser.add_argument(
        '--collection',
        type=str,
        help='Calculate stats for specific collection only',
        choices=ALLOWED_BENCHMARK_COLLECTIONS
    )
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear all cached statistics before calculating'
    )
    
    args = parser.parse_args()
    
    print("Western Ecuador Statistics Pre-calculation Script")
    print("=" * 50)
    
    # Show which collections will be processed
    collections_to_process = [args.collection] if args.collection else ALLOWED_BENCHMARK_COLLECTIONS
    print(f"Collections to process: {len(collections_to_process)}")
    for collection in collections_to_process:
        print(f"  - {collection}")
    print()
    
    # Clear cache if requested
    if args.clear:
        print("Clearing existing cache...")
        cleared_count = clear_all_cached_stats()
        print(f"Cleared {cleared_count} cached statistics\n")
    
    # Pre-calculate statistics
    try:
        print("Starting pre-calculation...")
        results = precalculate_all_stats(
            force_recalculate=args.force,
            collection_filter=args.collection
        )
        
        # Summary
        print("\n" + "="*50)
        print("Pre-calculation completed:")
        print(f"  Successful: {results['successful']}")
        print(f"  Failed: {results['failed']}")
        print(f"  Skipped: {results['skipped']}")
        print(f"  Total: {len(collections_to_process)}")
        
        if results['failed'] > 0:
            print("\nWARNING: Some calculations failed. Check Django logs for details.")
            sys.exit(1)
        else:
            print("\nAll calculations completed successfully!")
            
    except Exception as e:
        print(f"\nERROR: Pre-calculation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Standalone Benchmark Runner
~~~~~~~~~~~~~~~~~~~~~~~~~~

This script runs benchmark evaluation independently of the full ML pipeline.
It allows you to evaluate any STAC collection against training polygons without
requiring a complete training run.

Usage Examples:
    # Evaluate a single collection against project polygons
    python run_benchmarks_only.py --collection "benchmarks-hansen-tree-cover-2022" --project-id 6 --year 2022 --output-dir ./benchmark_results

    # Evaluate multiple collections
    python run_benchmarks_only.py --collections "benchmarks-hansen-tree-cover-2022" "benchmarks-mapbiomas-2022" --project-id 6 --year 2022

    # Use custom validation CSV files
    python run_benchmarks_only.py --collection "benchmarks-hansen-tree-cover-2022" --project-id 6 --year 2022 --validation-dir ./custom_validation

    # Evaluate against all available benchmark collections
    python run_benchmarks_only.py --all-benchmarks --project-id 6 --year 2022

    # Use specific database configuration
    python run_benchmarks_only.py --collection "benchmarks-hansen-tree-cover-2022" --project-id 6 --year 2022 --db-host remote

Features:
- Run benchmarks without full pipeline execution
- Flexible collection selection (single, multiple, or all benchmarks)
- Custom validation data sources
- Configurable output directories
- Robust error handling with collection-level recovery
- Database connection configuration
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from ml_pipeline.benchmark_tester import BenchmarkTester
from ml_pipeline.db_utils import get_db_connection
from ml_pipeline.extractor import TitilerExtractor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default benchmark collections
DEFAULT_BENCHMARK_COLLECTIONS = [
    "benchmarks-hansen-tree-cover-2022",      # Hansen Global Forest Change
    "benchmarks-mapbiomas-2022",              # MapBiomas Ecuador
    "benchmarks-esa-landcover-2020",          # ESA WorldCover
    "benchmarks-jrc-forestcover-2020",        # JRC Global Forest Cover
    "benchmarks-palsar-2020",                 # PALSAR Forest/Non-Forest
    "benchmarks-wri-treecover-2020",          # WRI Tree Cover
]

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run benchmark evaluation independently of the full ML pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single collection
  python run_benchmarks_only.py --collection "benchmarks-hansen-tree-cover-2022" --project-id 6 --year 2022

  # Multiple collections
  python run_benchmarks_only.py --collections "benchmarks-hansen-tree-cover-2022" "benchmarks-mapbiomes-2022" --project-id 6 --year 2022

  # All benchmark collections
  python run_benchmarks_only.py --all-benchmarks --project-id 6 --year 2022

  # Custom output directory
  python run_benchmarks_only.py --collection "benchmarks-hansen-tree-cover-2022" --project-id 6 --year 2022 --output-dir ./my_results
        """
    )
    
    # Collection selection (mutually exclusive)
    collection_group = parser.add_mutually_exclusive_group(required=True)
    collection_group.add_argument(
        "--collection", 
        type=str, 
        help="Single STAC collection ID to evaluate"
    )
    collection_group.add_argument(
        "--collections", 
        nargs="+", 
        help="Multiple STAC collection IDs to evaluate"
    )
    collection_group.add_argument(
        "--all-benchmarks", 
        action="store_true", 
        help="Evaluate all default benchmark collections"
    )
    
    # Required parameters
    parser.add_argument(
        "--project-id", 
        type=int, 
        required=True, 
        help="Training polygon project ID"
    )
    parser.add_argument(
        "--year", 
        type=str, 
        required=True, 
        help="Year to evaluate (e.g., '2022')"
    )
    
    # Optional parameters
    parser.add_argument(
        "--output-dir", 
        type=str, 
        default="./benchmark_results_standalone", 
        help="Directory to save benchmark results (default: ./benchmark_results_standalone)"
    )
    parser.add_argument(
        "--validation-dir", 
        type=str, 
        help="Directory containing held-out validation CSV files (optional)"
    )
    parser.add_argument(
        "--run-id", 
        type=str, 
        help="Run ID for organizing results (auto-generated if not provided)"
    )
    parser.add_argument(
        "--titiler-url", 
        type=str, 
        default="http://localhost:8083", 
        help="TiTiler service URL (default: http://localhost:8083)"
    )
    parser.add_argument(
        "--db-host", 
        type=str, 
        choices=["local", "remote"], 
        default="local", 
        help="Database host configuration (default: local)"
    )
    parser.add_argument(
        "--continue-on-error", 
        action="store_true", 
        help="Continue processing other collections if one fails"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Show what would be processed without running benchmarks"
    )
    
    return parser.parse_args()

def validate_arguments(args):
    """Validate command line arguments."""
    # Validate year format
    try:
        year_int = int(args.year)
        if year_int < 2000 or year_int > 2030:
            logger.warning(f"Year {args.year} seems unusual, but proceeding...")
    except ValueError:
        logger.error(f"❌ Invalid year format: {args.year}")
        sys.exit(1)
    
    # Validate project ID
    if args.project_id <= 0:
        logger.error(f"❌ Project ID must be positive: {args.project_id}")
        sys.exit(1)
    
    # Validate validation directory if provided
    if args.validation_dir:
        validation_path = Path(args.validation_dir)
        if not validation_path.exists():
            logger.error(f"❌ Validation directory does not exist: {validation_path}")
            sys.exit(1)
        if not validation_path.is_dir():
            logger.error(f"❌ Validation path is not a directory: {validation_path}")
            sys.exit(1)

def get_collections_to_process(args) -> List[str]:
    """Determine which collections to process based on arguments."""
    if args.collection:
        return [args.collection]
    elif args.collections:
        return args.collections
    elif args.all_benchmarks:
        return DEFAULT_BENCHMARK_COLLECTIONS.copy()
    else:
        # This shouldn't happen due to mutually_exclusive_group
        logger.error("❌ No collections specified")
        sys.exit(1)

def check_collection_exists(collection: str, titiler_url: str) -> bool:
    """Check if a STAC collection exists and has COGs."""
    try:
        extractor = TitilerExtractor(base_url=titiler_url, collection=collection)
        cogs = extractor.get_all_cog_urls(collection)
        if len(cogs) == 0:
            logger.warning(f"⚠️  Collection '{collection}' exists but has no COGs")
            return False
        logger.info(f"✅ Collection '{collection}' found with {len(cogs)} COGs")
        return True
    except Exception as e:
        logger.error(f"❌ Collection '{collection}' not accessible: {str(e)}")
        return False

def generate_run_id(args) -> str:
    """Generate a run ID if not provided."""
    if args.run_id:
        return args.run_id
    
    # Auto-generate based on timestamp and collections
    timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
    if args.collection:
        collection_suffix = args.collection.split('-')[-1]  # e.g., "2022" from "benchmarks-hansen-tree-cover-2022"
    elif args.all_benchmarks:
        collection_suffix = "all_benchmarks"
    else:
        collection_suffix = "multi"
    
    return f"standalone_benchmark_{collection_suffix}_{timestamp}"

def run_single_benchmark(
    collection: str, 
    project_id: int, 
    year: str, 
    titiler_url: str,
    output_dir: Path,
    validation_dir: Optional[Path] = None,
    run_id: Optional[str] = None
) -> bool:
    """Run benchmark for a single collection."""
    logger.info(f"\n📈 Evaluating benchmark: {collection}")
    logger.info("-" * 80)
    
    try:
        # Create BenchmarkTester instance
        tester = BenchmarkTester(
            base_url=titiler_url,
            collection=collection,
            year=year,
            project_id=project_id,
            run_id=run_id,
            test_features_dir=validation_dir
        )
        
        # Run the benchmark
        metrics_df = tester.run(save=False)  # Don't save to default location
        
        # Save results to custom output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{collection}.csv"
        metrics_df.to_csv(output_file, index=False)
        logger.info(f"📊 Results saved to: {output_file}")
        
        # Print summary
        overall_row = metrics_df[metrics_df['month'] == 'overall']
        if not overall_row.empty:
            accuracy = overall_row['accuracy'].iloc[0]
            f1_forest = overall_row['f1_forest'].iloc[0]
            f1_nonforest = overall_row['f1_nonforest'].iloc[0]
            logger.info(f"✅ Overall accuracy: {accuracy:.3f}, F1 (Forest): {f1_forest:.3f}, F1 (Non-Forest): {f1_nonforest:.3f}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to evaluate {collection}: {str(e)}")
        return False

def main():
    """Main function."""
    # Parse and validate arguments
    args = parse_arguments()
    validate_arguments(args)
    
    # Get collections to process
    collections = get_collections_to_process(args)
    
    # Generate run ID
    run_id = generate_run_id(args)
    
    # Set up paths
    output_dir = Path(args.output_dir)
    validation_dir = Path(args.validation_dir) if args.validation_dir else None
    
    # Log configuration
    logger.info("🚀 Starting Standalone Benchmark Runner")
    logger.info(f"📊 Collections to evaluate: {len(collections)}")
    logger.info(f"📋 Project ID: {args.project_id}")
    logger.info(f"📅 Year: {args.year}")
    logger.info(f"🏃 Run ID: {run_id}")
    logger.info(f"📁 Output directory: {output_dir}")
    logger.info(f"🔍 Validation directory: {validation_dir or 'None (using all polygons)'}")
    logger.info(f"🌐 TiTiler URL: {args.titiler_url}")
    logger.info(f"🗄️  Database: {args.db_host}")
    logger.info("=" * 80)
    
    # Show collections
    logger.info("📋 Collections to process:")
    for i, collection in enumerate(collections, 1):
        logger.info(f"  {i}. {collection}")
    
    # Dry run check
    if args.dry_run:
        logger.info("\n🔍 DRY RUN - No benchmarks will be executed")
        
        # Check which collections exist
        logger.info("\n🔍 Checking collection availability...")
        available_collections = []
        for collection in collections:
            if check_collection_exists(collection, args.titiler_url):
                available_collections.append(collection)
        
        logger.info(f"\n📊 Summary: {len(available_collections)}/{len(collections)} collections available")
        if available_collections:
            logger.info("✅ Available collections:")
            for collection in available_collections:
                logger.info(f"  - {collection}")
        
        missing_collections = set(collections) - set(available_collections)
        if missing_collections:
            logger.info("❌ Missing collections:")
            for collection in missing_collections:
                logger.info(f"  - {collection}")
        
        logger.info("\n🔍 Dry run completed")
        return
    
    # Test database connection
    logger.info("\n🔗 Testing database connection...")
    try:
        engine = get_db_connection()
        with engine.connect() as conn:
            result = conn.execute("SELECT 1").fetchone()
            logger.info("✅ Database connection successful")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        sys.exit(1)
    
    # Check TiTiler service
    logger.info(f"\n🌐 Testing TiTiler service at {args.titiler_url}...")
    try:
        # Try to create a simple extractor to test the service
        test_extractor = TitilerExtractor(base_url=args.titiler_url, collection="test")
        logger.info("✅ TiTiler service accessible")
    except Exception as e:
        logger.error(f"❌ TiTiler service not accessible: {str(e)}")
        logger.error("Make sure TiTiler service is running and accessible")
        sys.exit(1)
    
    # Process collections
    successful_benchmarks = 0
    failed_benchmarks = []
    
    for i, collection in enumerate(collections, 1):
        logger.info(f"\n📊 Processing collection {i}/{len(collections)}: {collection}")
        
        # Check if collection exists
        if not check_collection_exists(collection, args.titiler_url):
            logger.warning(f"⚠️  Skipping unavailable collection: {collection}")
            failed_benchmarks.append(collection)
            if not args.continue_on_error:
                logger.error("❌ Stopping due to missing collection (use --continue-on-error to skip)")
                sys.exit(1)
            continue
        
        # Run benchmark
        success = run_single_benchmark(
            collection=collection,
            project_id=args.project_id,
            year=args.year,
            titiler_url=args.titiler_url,
            output_dir=output_dir,
            validation_dir=validation_dir,
            run_id=run_id
        )
        
        if success:
            successful_benchmarks += 1
        else:
            failed_benchmarks.append(collection)
            if not args.continue_on_error:
                logger.error("❌ Stopping due to benchmark failure (use --continue-on-error to skip)")
                sys.exit(1)
    
    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 BENCHMARK EVALUATION SUMMARY")
    logger.info("=" * 80)
    
    total_collections = len(collections)
    success_rate = successful_benchmarks / total_collections * 100 if total_collections > 0 else 0
    
    logger.info(f"📈 Processed: {successful_benchmarks}/{total_collections} collections ({success_rate:.1f}% success rate)")
    logger.info(f"📁 Results saved to: {output_dir}")
    
    if failed_benchmarks:
        logger.warning(f"❌ Failed collections: {', '.join(failed_benchmarks)}")
    
    if successful_benchmarks > 0:
        logger.info(f"\n🎉 Benchmark evaluation completed successfully at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        logger.error("❌ No benchmarks completed successfully")
        sys.exit(1)

if __name__ == "__main__":
    main()
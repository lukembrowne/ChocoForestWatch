#!/usr/bin/env python3
"""
Upload GFW Alerts to Local Database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Simple script to upload GFW alerts STAC collections to the local database
without running the full processing pipeline. This is useful when you already
have the alerts uploaded to S3 but need to add them to your local development database.

Usage:
    poetry run python upload_gfw_alerts_to_local.py --years 2022 2023 2024
"""

import sys
import argparse
import logging
from pathlib import Path

# Add the ml_pipeline source to the path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from ml_pipeline.stac_builder import STACManager, STACManagerConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def upload_gfw_alerts_to_local(years):
    """Upload GFW alerts collections to local database."""
    
    try:
        # Initialize local STAC manager
        local_stac_config = STACManagerConfig(use_remote_db=False)
        local_stac_manager = STACManager(local_stac_config)
        
        logger.info(f"Local DB connection details: Host={local_stac_manager.cfg.pg_env_vars['PGHOST']}, DB={local_stac_manager.cfg.pg_env_vars['PGDATABASE']}")
        
        # Test local connection
        if not local_stac_manager.test_connection():
            logger.error("❌ Local database connection failed")
            return False
        
        logger.info("✅ Local database connection verified")
        
        success_count = 0
        for year in years:
            try:
                collection_id = f"datasets-gfw-integrated-alerts-{year}"
                logger.info(f"\nProcessing year {year} - Collection: {collection_id}")
                
                # Check if collection already exists
                if local_stac_manager.verify_collection_exists(collection_id):
                    logger.info(f"Collection {collection_id} already exists in local database")
                    
                    # Ask user if they want to delete and recreate
                    response = input(f"Delete and recreate collection {collection_id}? (y/N): ").strip().lower()
                    if response == 'y':
                        logger.info(f"Deleting existing collection: {collection_id}")
                        local_stac_manager.delete_collection(collection_id)
                    else:
                        logger.info(f"Skipping {collection_id}")
                        continue
                
                # Create collection in local database
                local_stac_manager.process_year(
                    year=str(year),
                    prefix_on_s3="datasets/gfw-integrated-alerts",
                    collection_id=collection_id,
                    asset_key="data",
                    asset_roles=["data"],
                    asset_title=f"GFW Integrated Deforestation Alerts {year}",
                    extra_asset_fields={
                        "gfw:encoding": "date_conf",
                        "gfw:decoding_info": "First digit: confidence level (1-4), remaining digits: days since 2014-12-31"
                    }
                )
                
                logger.info(f"✅ Successfully created collection in local database: {collection_id}")
                success_count += 1
                
            except Exception as e:
                logger.error(f"❌ Failed to process year {year}: {str(e)}")
        
        logger.info(f"\n=== SUMMARY ===")
        logger.info(f"Successfully processed {success_count}/{len(years)} collections")
        
        return success_count == len(years)
        
    except Exception as e:
        logger.error(f"Script failed: {str(e)}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Upload GFW Alerts to Local Database")
    parser.add_argument("--years", nargs="+", type=int, default=[2022, 2023, 2024],
                        help="Years to upload (default: 2022 2023 2024)")
    
    args = parser.parse_args()
    
    logger.info(f"Uploading GFW alerts to local database for years: {args.years}")
    
    success = upload_gfw_alerts_to_local(args.years)
    
    if success:
        logger.info("🎉 All collections uploaded successfully!")
    else:
        logger.error("❌ Some collections failed to upload")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
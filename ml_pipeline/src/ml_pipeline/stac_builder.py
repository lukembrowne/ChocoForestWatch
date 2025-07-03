"""
ml_pipeline.stac_manager
~~~~~~~~~~~~~~~~~~~~~~~~
Build, load & manage STAC Collections/Items from COGs stored in DigitalOcean Spaces.

Requires
--------
pip install boto3 pystac pypgstac rasterio python-dotenv psycopg2-binary
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import os
import calendar
import json
import tempfile
import subprocess
from typing import Iterable, Sequence
from contextlib import contextmanager

import boto3
import psycopg2
import psycopg2.extras
import rasterio
from rasterio.warp import transform_bounds
from dotenv import load_dotenv
from pystac import (
    Item,
    Collection,
    Asset,
    MediaType,
    Link,
    Extent,
    SpatialExtent,
    TemporalExtent,
)

from ml_pipeline.s3_utils import get_s3_client, list_files
from ml_pipeline.version import get_version_metadata

# ---------------------------------------------------------------------
#  Custom exceptions
# ---------------------------------------------------------------------


class STACManagerError(Exception):
    """Base exception for STAC Manager operations."""
    pass


class CollectionNotFoundError(STACManagerError):
    """Raised when a requested collection is not found."""
    pass


class STACConnectionError(STACManagerError):
    """Raised when database connection fails."""
    pass


class STACSafetyError(STACManagerError):
    """Raised when safety checks fail during STAC operations."""
    pass


# ---------------------------------------------------------------------
#  Configuration dataclass
# ---------------------------------------------------------------------


@dataclass
class STACManagerConfig:
    # DigitalOcean Spaces
    bucket: str = "choco-forest-watch"
    
    # Database connection type
    use_remote_db: bool = True

    # PgSTAC connection is handled through env vars - will be set in __post_init__
    pg_env_vars: dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize pg_env_vars after instance creation to avoid shared dictionaries."""
        if not self.pg_env_vars:  # Only set if not already provided
            # Ensure .env file is loaded from project root
            project_root = Path(__file__).parent.parent.parent.parent  # Go up from src/ml_pipeline to project root
            env_path = project_root / ".env"
            if env_path.exists():
                load_dotenv(env_path)
            
            # Set base connection info from environment
            base_host = os.getenv("DB_IP")
            
            self.pg_env_vars = {
                "PGHOST": base_host or ('localhost' if not self.use_remote_db else None),
                "PGPORT": os.getenv("DB_PORT") or "5432",
                "PGDATABASE": os.getenv("POSTGRES_DB"),
                "PGUSER": os.getenv("POSTGRES_USER"),
                "PGPASSWORD": os.getenv("POSTGRES_PASSWORD"),
            }
            
            # Override host for local connections or provide fallback
            if not self.use_remote_db:
                self.pg_env_vars["PGHOST"] = 'localhost'
            elif not self.pg_env_vars["PGHOST"]:
                raise ValueError(f"DB_IP environment variable not found. Please ensure .env file exists at {env_path} and contains DB_IP setting.")
                
            # Debug logging to verify configuration
            print(f"STACManagerConfig initialized: use_remote_db={self.use_remote_db}, PGHOST={self.pg_env_vars['PGHOST']}")

# Note: We no longer set global environment variables here to avoid conflicts.
# Each STACManager instance now manages its own database connection parameters
# through the explicit environment dictionary passed to subprocess calls.


# ---------------------------------------------------------------------
#  STACManager class
# ---------------------------------------------------------------------


class STACManager:
    """
    Utility to manage STAC Collections/Items from COGs stored in DigitalOcean Spaces.
    
    Provides functionality to:
    - Build and upsert STAC Collections/Items to pgSTAC
    - Safely delete STAC Collections and their associated items
    - Query and manage existing STAC data

    Parameters
    ----------
    cfg
        STACManagerConfig with Spaces + pgSTAC settings.
    """

    def __init__(self, cfg: STACManagerConfig = STACManagerConfig()):
        # Load .env file from project root for S3 credentials
        project_root = Path(__file__).parent.parent.parent.parent  # Go up from src/ml_pipeline to project root
        env_path = project_root / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            
        self.cfg = cfg
        self.s3, _ = get_s3_client(cfg.bucket)
        
        # Note: Database connection configuration is handled in STACManagerConfig.__post_init__

    # ------------------------------------------------------------------
    #  Database connection management
    # ------------------------------------------------------------------
    
    def get_db_connection(self):
        """Get a PostgreSQL database connection."""
        try:
            return psycopg2.connect(
                host=self.cfg.pg_env_vars["PGHOST"],
                port=self.cfg.pg_env_vars["PGPORT"],
                database=self.cfg.pg_env_vars["PGDATABASE"],
                user=self.cfg.pg_env_vars["PGUSER"],
                password=self.cfg.pg_env_vars["PGPASSWORD"],
            )
        except psycopg2.Error as e:
            raise STACConnectionError(f"Failed to connect to database: {str(e)}") from e
    
    @contextmanager
    def db_transaction(self):
        """Context manager for database transactions with automatic rollback on error."""
        conn = None
        try:
            conn = self.get_db_connection()
            conn.autocommit = False
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Database transaction failed, rolled back: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()
    
    def test_connection(self) -> bool:
        """Test database connection and return True if successful."""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    return cur.fetchone()[0] == 1
        except STACConnectionError as e:
            print(f"Database connection test failed: {str(e)}")
            return False
    
    def check_locks(self, collection_id: str = None) -> list[dict]:
        """
        Check for database locks that might be blocking operations.
        
        Parameters
        ----------
        collection_id : str, optional
            If provided, check for locks specifically on this collection
            
        Returns
        -------
        list[dict]
            List of active locks
        """
        try:
            with self.get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    if collection_id:
                        # Check for locks on specific collection
                        cur.execute("""
                            SELECT 
                                pid,
                                mode,
                                locktype,
                                granted,
                                query_start,
                                state,
                                query
                            FROM pg_locks l
                            JOIN pg_stat_activity a ON l.pid = a.pid
                            WHERE a.query ILIKE %s OR a.query ILIKE %s
                            ORDER BY query_start
                        """, (f'%{collection_id}%', '%pgstac.items%'))
                    else:
                        # Check for all locks on pgstac tables
                        cur.execute("""
                            SELECT 
                                pid,
                                mode,
                                locktype,
                                granted,
                                query_start,
                                state,
                                query
                            FROM pg_locks l
                            JOIN pg_stat_activity a ON l.pid = a.pid
                            WHERE a.query ILIKE '%pgstac%'
                            ORDER BY query_start
                        """)
                    
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"Failed to check locks: {str(e)}")
            return []

    # ------------------------------------------------------------------
    #  Collection management methods
    # ------------------------------------------------------------------
    
    
    def list_collections(self) -> list[dict]:
        """
        List all STAC collections in the database.
        
        Returns
        -------
        list[dict]
            List of collection info dictionaries with id and item count
        """
        try:
            with self.get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("""
                        SELECT 
                            c.id,
                            COUNT(i.id) as item_count
                        FROM pgstac.collections c
                        LEFT JOIN pgstac.items i ON c.id = i.collection
                        GROUP BY c.id
                        ORDER BY c.id
                    """)
                    return [dict(row) for row in cur.fetchall()]
        except STACConnectionError:
            raise
        except Exception as e:
            print(f"Failed to list collections: {str(e)}")
            return []
    
    def get_collection_info(self, collection_id: str) -> dict | None:
        """
        Get detailed information about a specific collection.
        
        Parameters
        ----------
        collection_id : str
            The ID of the collection to query
            
        Returns
        -------
        dict | None
            Collection information or None if not found
        """
        try:
            with self.get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("""
                        SELECT 
                            c.id,
                            COUNT(i.id) as item_count,
                            MIN(i.datetime) as earliest_item,
                            MAX(i.datetime) as latest_item
                        FROM pgstac.collections c
                        LEFT JOIN pgstac.items i ON c.id = i.collection
                        WHERE c.id = %s
                        GROUP BY c.id
                    """, (collection_id,))
                    
                    result = cur.fetchone()
                    return dict(result) if result else None
        except STACConnectionError:
            raise
        except Exception as e:
            print(f"Failed to get collection info for '{collection_id}': {str(e)}")
            return None
    
    def verify_collection_exists(self, collection_id: str) -> bool:
        """
        Check if a collection exists in the database.
        
        Parameters
        ----------
        collection_id : str
            The ID of the collection to check
            
        Returns
        -------
        bool
            True if collection exists, False otherwise
        """
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT 1 FROM pgstac.collections WHERE id = %s",
                        (collection_id,)
                    )
                    return cur.fetchone() is not None
        except STACConnectionError:
            raise
        except Exception as e:
            print(f"Failed to verify collection '{collection_id}': {str(e)}")
            return False
    
    def backup_collection(self, collection_id: str, backup_path: str | None = None) -> str | None:
        """
        Create a SQL backup of a collection and its items.
        
        Parameters
        ----------
        collection_id : str
            The ID of the collection to backup
        backup_path : str | None, optional
            Path for the backup file. If None, creates a temporary file.
            
        Returns
        -------
        str | None
            Path to the backup file, or None if backup failed
        """
        if not self.verify_collection_exists(collection_id):
            print(f"Collection '{collection_id}' does not exist, cannot create backup")
            return None
            
        if backup_path is None:
            backup_path = f"{collection_id}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        
        try:
            # Use pg_dump to create backup
            pg_dump_cmd = [
                "pg_dump",
                "-h", self.cfg.pg_env_vars["PGHOST"],
                "-p", str(self.cfg.pg_env_vars["PGPORT"]),
                "-U", self.cfg.pg_env_vars["PGUSER"],
                "-d", self.cfg.pg_env_vars["PGDATABASE"],
                "-t", "pgstac.collections",
                "-t", "pgstac.items",
                "--where", f"collection='{collection_id}' OR id='{collection_id}'",
                "-f", backup_path
            ]
            
            # Set all database connection environment variables for pg_dump
            env = os.environ.copy()
            env.update(self.cfg.pg_env_vars)
            
            result = subprocess.run(pg_dump_cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ Collection '{collection_id}' backed up to: {backup_path}")
                return backup_path
            else:
                print(f"❌ Backup failed: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"Failed to backup collection '{collection_id}': {str(e)}")
            return None
    
    def delete_collection(self, collection_id: str, dry_run: bool = False) -> dict:
        """
        Fast deletion using pgSTAC's optimized deletion functions.
        
        This method bypasses some safety checks for faster deletion of large collections.
        
        Parameters
        ----------
        collection_id : str
            The ID of the collection to delete
        dry_run : bool, optional
            If True, only reports what would be deleted without making changes
            
        Returns
        -------
        dict
            Summary of the deletion operation
        """
        print(f"{'[DRY RUN] ' if dry_run else ''}Fast deletion for collection: {collection_id}")
        
        if not self.verify_collection_exists(collection_id):
            return {
                "status": "error",
                "message": f"Collection '{collection_id}' not found",
                "items_deleted": 0,
                "collection_deleted": False
            }
        
        # Get item count for reporting
        info = self.get_collection_info(collection_id)
        item_count = info['item_count'] if info else 0
        
        if dry_run:
            return {
                "status": "dry_run",
                "message": f"Would delete {item_count} items and collection '{collection_id}'",
                "items_would_delete": item_count,
                "collection_would_delete": True
            }
        
        try:
            import time
            start_time = time.time()
            
            with self.get_db_connection() as conn:
                conn.autocommit = True  # Use autocommit for faster operations
                with conn.cursor() as cur:
                    # Set high timeout for partition cleanup
                    cur.execute("SET statement_timeout = '600s'")  # 10 minutes
                    
                    print(f"Calling pgSTAC delete_collection for '{collection_id}'...")
                    cur.execute("SELECT pgstac.delete_collection(%s)", (collection_id,))
                    result = cur.fetchone()[0]
                    
                    elapsed = time.time() - start_time
                    print(f"✅ Fast deletion completed in {elapsed:.2f}s")
                    
                    return {
                        "status": "success",
                        "message": f"Fast deletion completed for '{collection_id}' in {elapsed:.2f}s",
                        "items_deleted": item_count,
                        "collection_deleted": True,
                        "pgstac_result": result
                    }
                    
        except Exception as e:
            error_msg = f"Fast deletion failed for '{collection_id}': {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "status": "error",
                "message": error_msg,
                "items_deleted": 0,
                "collection_deleted": False
            }

    # ------------------------------------------------------------------
    #  Public helpers
    # ------------------------------------------------------------------

    def list_cogs(self, prefix: str) -> list[dict]:
        """Return every `.tif[f]` under a prefix with S3 URL + key."""
        return list_files(prefix, self.cfg.bucket)

    def build_collection(
        self,
        collection_id: str,
        year: str,
        month: str | None = None,
        description: str | None = None,
        license: str = "proprietary",
    ) -> Collection:
        """
        Build a STAC Collection for either monthly or annual data.
        
        Parameters
        ----------
        collection_id : str
            The ID for the collection
        year : str
            The year of the data
        month : str | None, optional
            The month of the data. If None, creates an annual collection.
        description : str | None, optional
            Collection description. If None, generates one based on temporal extent.
        license : str, optional
            The license for the collection, by default "proprietary"
        """
        if month:
            first = datetime(int(year), int(month), 1)
            last = datetime(
                int(year), int(month), calendar.monthrange(int(year), int(month))[1]
            )
            desc = description or f"Monthly data for {year}-{month}"
        else:
            first = datetime(int(year), 1, 1)
            last = datetime(int(year), 12, 31)
            desc = description or f"Annual data for {year}"

        col = Collection(
            id=collection_id,
            description=desc,
            license=license,
            extent=Extent(
                SpatialExtent([[-180, -90, 180, 90]]),
                TemporalExtent([[first, last]]),
            ),
        )
        
        # Add version metadata to collection extra fields
        version_metadata = get_version_metadata()
        col.extra_fields["version"] = version_metadata["pipeline_version"]
        col.extra_fields["created_at"] = version_metadata["created_at"]
        col.extra_fields["processing:software"] = version_metadata["software"]

        col.add_link(
            Link(
                rel="license",
                target="https://www.planet.com/nicfi/",
                media_type="text/html",
                title="NICFI License",
            )
        )
        return col

    def build_item(
        self,
        cog: dict,
        year: str,
        month: str | None = None,
        asset_key: str = "data",
        asset_roles: Sequence[str] = ("data",),
        asset_title: str | None = None,
        media_type: str = MediaType.COG,
        extra_asset_fields: dict | None = None,
        derived_from: str | None = None,
    ) -> Item:
        """Return a STAC Item (bounds derived from the COG itself)."""
        try:
            # Check if file exists and is accessible
            self.s3.head_object(Bucket=self.cfg.bucket, Key=cog["key"])
            
            # Use the proper S3 URL format
            s3_url = f"s3://{self.cfg.bucket}/{cog['key']}"
            
            with rasterio.open(s3_url) as ds:
                wgs_bounds = transform_bounds(ds.crs, "EPSG:4326", *ds.bounds)

            if month:
                dt = datetime(int(year), int(month), 1)
            else:
                dt = datetime(int(year), 1, 1)
                
            item_id = Path(cog["key"]).stem

            # Add version metadata to properties
            version_metadata = get_version_metadata()
            properties = {
                "version": version_metadata["pipeline_version"],
                "created_at": version_metadata["created_at"],
                "processing:software": version_metadata["software"],
            }
            
            itm = Item(
                id=item_id,
                geometry={
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [wgs_bounds[0], wgs_bounds[1]],
                            [wgs_bounds[2], wgs_bounds[1]],
                            [wgs_bounds[2], wgs_bounds[3]],
                            [wgs_bounds[0], wgs_bounds[3]],
                            [wgs_bounds[0], wgs_bounds[1]],
                        ]
                    ],
                },
                bbox=list(wgs_bounds),
                datetime=dt,
                properties=properties,
            )

            asset_dict = {
                "href": cog["url"],
                "media_type": media_type,
                "roles": list(asset_roles),
                "title": asset_title or f"{asset_key} for {item_id}",
            }
            if extra_asset_fields:
                asset_dict.update(extra_asset_fields)

            itm.add_asset(asset_key, Asset.from_dict(asset_dict))

            # provenance link
            if derived_from:
                itm.add_link(
                    Link(
                        rel="derived_from",
                        href=derived_from,
                        media_type="application/json",
                    )
                )

            return itm
            
        except Exception as e:
            print(f"Error building item for {cog['key']}: {str(e)}")
            raise

    def upsert_to_pgstac(self, collection: Collection, items: Iterable[Item]) -> None:
        """Write temp JSON / ndjson and call pypgstac CLI with explicit connection parameters."""
        with tempfile.TemporaryDirectory() as tmp:
            col_path = Path(tmp) / "collection.json"
            items_path = Path(tmp) / "items.ndjson"

            collection.save_object(dest_href=str(col_path))
            with items_path.open("w") as f:
                for it in items:
                    f.write(json.dumps(it.to_dict()) + "\n")

            # Create environment with explicit database connection settings
            env = os.environ.copy()
            env.update(self.cfg.pg_env_vars)
            
            print(f"Using database connection: {self.cfg.pg_env_vars['PGHOST']}:{self.cfg.pg_env_vars['PGPORT']}/{self.cfg.pg_env_vars['PGDATABASE']}")

            subprocess.run(
                ["pypgstac", "load", "collections", "--method", "upsert", str(col_path)],
                check=True,
                env=env,
            )
            subprocess.run(
                ["pypgstac", "load", "items", "--method", "upsert", str(items_path)],
                check=True,
                env=env,
            )
            print(f"✅ Upserted ⟨{collection.id}⟩ and {len(list(items))} items")

    def process_month(
        self,
        year: str,
        month: str,
        prefix_on_s3: str,
        collection_id: str,
        asset_key: str,
        asset_roles: Sequence[str],
        asset_title: str,
        *,
        extra_asset_fields: dict | None = None,
        derived_from_tpl: str | None = None,
    ) -> None:
        """
        Process monthly data and create STAC collection/items.
        
        Parameters
        ----------
        year : str
            The year of the data
        month : str
            The month of the data
        prefix_on_s3 : str
            The S3 prefix where the data is stored
        collection_id : str
            The ID for the STAC collection
        asset_key : str
            The key for the asset in the STAC item
        asset_roles : Sequence[str]
            The roles for the asset
        asset_title : str
            The title for the asset
        extra_asset_fields : dict | None, optional
            Additional fields to add to the asset
        derived_from_tpl : str | None, optional
            Template for the derived_from link
        """
        month_str = f"{int(month):02d}"
        year_str = str(year)
        s3_prefix = f"{prefix_on_s3}/{year_str}/{month_str}"

        cogs = self.list_cogs(s3_prefix)
        print(f"🔍 Found {len(cogs)} COGs under {s3_prefix}")

        # Test for duplicates
        cog_counts = {}
        for cg in cogs:
            key = cg["key"]
            cog_counts[key] = cog_counts.get(key, 0) + 1
        
        # Report any duplicates found
        print("Checking for duplicates...")
        duplicates = {key: count for key, count in cog_counts.items() if count > 1}
        if duplicates:
            print("\n⚠️  Found duplicate COGs:")
            for key, count in duplicates.items():
                print(f"  - {key}: {count} occurrences")
        else:
            print("\n✅ No duplicate COGs found")

        col = self.build_collection(
            collection_id=collection_id,
            year=year_str,
            month=month_str,
            description=f"{asset_title} for {year_str}-{month_str}",
        )

        # Track unique item IDs to avoid duplicates
        seen_item_ids = set()
        items: list[Item] = []
        
        for cg in cogs:
            item_id = Path(cg["key"]).stem
            
            # Skip if we've already processed this item
            if item_id in seen_item_ids:
                print(f"Skipping duplicate item {item_id}")
                continue
                
            seen_item_ids.add(item_id)
            
            derived_href = (
                derived_from_tpl.format(item_id=item_id)
                if derived_from_tpl
                else None
            )
            try:
                it = self.build_item(
                    cog=cg,
                    year=year_str,
                    month=month_str,
                    asset_key=asset_key,
                    asset_roles=asset_roles,
                    asset_title=asset_title,
                    extra_asset_fields=extra_asset_fields,
                    derived_from=derived_href,
                )
                items.append(it)
                col.add_item(it)
            except rasterio.errors.RasterioIOError as e:
                print(f"Failed to read raster file {item_id}: {str(e)}")
                continue
            except Exception as e:
                print(f"Unexpected error processing {item_id}: {str(e)}")
                continue

        self.upsert_to_pgstac(col, items)

    def process_year(
        self,
        year: str,
        prefix_on_s3: str,
        collection_id: str,
        asset_key: str,
        asset_roles: Sequence[str],
        asset_title: str,
        *,
        extra_asset_fields: dict | None = None,
        derived_from_tpl: str | None = None,
    ) -> None:
        """
        Process annual data and create STAC collection/items.
        
        Parameters
        ----------
        year : str
            The year of the data
        prefix_on_s3 : str
            The S3 prefix where the data is stored
        collection_id : str
            The ID for the STAC collection
        asset_key : str
            The key for the asset in the STAC item
        asset_roles : Sequence[str]
            The roles for the asset
        asset_title : str
            The title for the asset
        extra_asset_fields : dict | None, optional
            Additional fields to add to the asset
        derived_from_tpl : str | None, optional
            Template for the derived_from link
        """
        year_str = str(year)
        s3_prefix = f"{prefix_on_s3}/{year_str}"

        cogs = self.list_cogs(s3_prefix)
        print(f"🔍 Found {len(cogs)} COGs under {s3_prefix}")

        if len(cogs) == 0:
            raise ValueError(f"No COGs found for {collection_id} in {year_str}")

        print(f"Building collection {collection_id} for {year_str}")
        col = self.build_collection(
            collection_id=collection_id,
            year=year_str,
            description=f"{asset_title} for {year_str}",
        )

        items: list[Item] = []
        for cg in cogs:
            derived_href = (
                derived_from_tpl.format(item_id=Path(cg["key"]).stem)
                if derived_from_tpl
                else None
            )
            print(f"Building item {Path(cg['key']).stem} for {year_str}")
            it = self.build_item(
                cog=cg,
                year=year_str,
                asset_key=asset_key,
                asset_roles=asset_roles,
                asset_title=asset_title,
                extra_asset_fields=extra_asset_fields,
                derived_from=derived_href,
            )
            items.append(it)
            print(f"Added item {Path(cg['key']).stem} to collection {collection_id}")
            col.add_item(it)

        # Update collection extent based on actual items
        if items:
            all_bboxes = [item.bbox for item in items]
            min_lon = min(bbox[0] for bbox in all_bboxes)
            min_lat = min(bbox[1] for bbox in all_bboxes)
            max_lon = max(bbox[2] for bbox in all_bboxes)
            max_lat = max(bbox[3] for bbox in all_bboxes)
            
            col.extent.spatial = SpatialExtent([[min_lon, min_lat, max_lon, max_lat]])
            print(f"Updated collection extent to: [{min_lon}, {min_lat}, {max_lon}, {max_lat}]")

        self.upsert_to_pgstac(col, items)
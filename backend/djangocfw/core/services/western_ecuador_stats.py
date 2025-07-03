"""
Service module for managing western Ecuador summary statistics.
"""

import os
import json
import logging
import requests
from django.core.cache import cache
from django.utils import timezone
from pyproj import Transformer
from shapely.ops import transform
from shapely.geometry import shape
from shapely.ops import unary_union

from ml_pipeline.summary_stats import AOISummaryStats

logger = logging.getLogger(__name__)

# Global cache for boundary polygon
_global_boundary_polygon = None

# Allowed benchmark collections
ALLOWED_BENCHMARK_COLLECTIONS = [
    "datasets-hansen-tree-cover-2022",
    "datasets-mapbiomes-2022", 
    "datasets-esa-landcover-2020",
    "datasets-jrc-forestcover-2020",
    "datasets-palsar-2020",
    "datasets-wri-treecover-2020",
    "northern_choco_test_2025_06_20_2022_merged_composite",  # CFW composite
]


def get_cache_key(collection_id):
    """Get the cache key for a collection ID."""
    return f"western_ecuador_stats_{collection_id}"


def _is_preprocessed_collection(collection_id):
    """
    Determine if a collection is pre-processed and already clipped to Western Ecuador.
    These collections can use simplified pixel counting without boundary clipping.
    
    As of the latest update, all datasets are now pre-processed to be clipped to 
    western Ecuador with no data outside of that range.
    """
    # All collections are now pre-processed and clipped to Western Ecuador
    # We can assume the data sets are already clipped to western Ecuador 
    # with no data outside of that range
    return True  # All collections are now pre-processed



def _load_boundary_polygon():
    """Load and cache the project boundary as a shapely geometry in Web Mercator projection."""
    global _global_boundary_polygon
    if _global_boundary_polygon is not None:
        return _global_boundary_polygon

    # Path to the GeoJSON that defines the project boundary. Allow override via env var.
    boundary_path = os.environ.get("BOUNDARY_GEOJSON_PATH")
    logger.info(f"📂 Loading boundary from: {boundary_path}")

    try:
        # Load GeoJSON file
        if boundary_path.startswith("http://") or boundary_path.startswith("https://"):
            resp = requests.get(boundary_path, timeout=30)
            resp.raise_for_status()
            geojson = resp.json()
        else:
            with open(boundary_path, "r", encoding="utf-8") as f:
                geojson = json.load(f)
        
        logger.info(f"📄 Loaded GeoJSON with {len(geojson.get('features', []))} features")
        
        # Load geometries and convert to Web Mercator
        # Create transformer from WGS84 to Web Mercator
        project = Transformer.from_crs('EPSG:4326', 'EPSG:3857', always_xy=True).transform
        
        # Load and transform each geometry
        geoms = []
        for i, feat in enumerate(geojson.get("features", [])):
            try:
                logger.info(f"🔄 Processing feature {i+1}: {feat['geometry']['type']}")
                geom = shape(feat["geometry"])
                logger.info(f"✓ Shapely geometry created: {geom.geom_type}")
                
                # Transform to Web Mercator - this is where the error likely occurs
                logger.info("🗺️  Transforming to Web Mercator...")
                
                # Try direct transformation first
                try:
                    geom_3857 = transform(project, geom)
                    logger.info(f"✓ Direct transformation complete: {geom_3857.geom_type}")
                except NotImplementedError as e:
                    # Fallback: use the geometry's __geo_interface__ and recreate
                    logger.warning(f"⚠️  Direct transform failed, using fallback method: {str(e)}")
                    
                    # Convert to GeoJSON, transform coordinates manually, then back to shapely
                    geo_dict = geom.__geo_interface__
                    
                    def transform_coords(coords):
                        """Recursively transform coordinate arrays"""
                        if isinstance(coords[0], (list, tuple)):
                            return [transform_coords(c) for c in coords]
                        else:
                            # This is a coordinate pair [lon, lat]
                            x, y = project(coords[0], coords[1])
                            return [x, y]
                    
                    # Transform the coordinates
                    geo_dict['coordinates'] = transform_coords(geo_dict['coordinates'])
                    
                    # Recreate shapely geometry
                    geom_3857 = shape(geo_dict)
                    logger.info(f"✓ Fallback transformation complete: {geom_3857.geom_type}")
                
                geoms.append(geom_3857)
                
            except Exception as e:
                logger.error(f"❌ Failed to process feature {i+1}: {str(e)}")
                logger.error(f"💥 Feature geometry type: {feat['geometry']['type']}")
                raise
        
        logger.info(f"✅ Processed {len(geoms)} geometries successfully")
        
        # Combine geometries
        if len(geoms) == 1:
            _global_boundary_polygon = geoms[0]
            logger.info(f"📦 Using single geometry: {_global_boundary_polygon.geom_type}")
        else:
            logger.info("🔗 Combining multiple geometries with unary_union...")
            _global_boundary_polygon = unary_union(geoms)
            logger.info(f"📦 Combined into: {_global_boundary_polygon.geom_type}")
        
        return _global_boundary_polygon
        
    except Exception as e:
        logger.error(f"❌ Failed to load boundary polygon: {str(e)}")
        logger.error(f"💥 Error type: {type(e).__name__}")
        raise


def _convert_boundary_to_geojson(boundary_polygon):
    """Convert boundary polygon to GeoJSON format (WGS84)."""
    try:
        # Convert boundary polygon to GeoJSON format (WGS84)
        project_back = Transformer.from_crs('EPSG:3857', 'EPSG:4326', always_xy=True).transform
        
        # Try direct transformation first
        try:
            boundary_wgs84 = transform(project_back, boundary_polygon)
            logger.info(f"✓ Direct back-transformation successful: {boundary_wgs84.geom_type}")
        except NotImplementedError as e:
            logger.warning(f"⚠️  Direct back-transform failed, using fallback: {str(e)}")
            
            # Fallback: manual coordinate transformation
            geo_dict = boundary_polygon.__geo_interface__
            
            def transform_coords_back(coords):
                """Recursively transform coordinate arrays back to WGS84"""
                if isinstance(coords[0], (list, tuple)):
                    return [transform_coords_back(c) for c in coords]
                else:
                    # This is a coordinate pair [x, y] in Web Mercator
                    lon, lat = project_back(coords[0], coords[1])
                    return [lon, lat]
            
            # Transform the coordinates back to WGS84
            geo_dict['coordinates'] = transform_coords_back(geo_dict['coordinates'])
            
            # Recreate shapely geometry in WGS84
            boundary_wgs84 = shape(geo_dict)
            logger.info(f"✓ Fallback back-transformation complete: {boundary_wgs84.geom_type}")
        
        # Use shapely's built-in geo interface which handles all geometry types properly
        geometry_dict = boundary_wgs84.__geo_interface__
        
        # Create GeoJSON feature
        boundary_geojson = {
            "type": "Feature",
            "geometry": geometry_dict
        }
        
        logger.info(f"✓ Converted to GeoJSON: {geometry_dict['type']} geometry")
        return boundary_geojson
        
    except Exception as e:
        logger.error(f"❌ Failed to convert boundary to GeoJSON: {str(e)}")
        logger.error(f"💥 Error type: {type(e).__name__}")
        raise Exception(f"Boundary conversion failed: {str(e)}")


def get_western_ecuador_stats(collection_id, force_recalculate=False):
    """
    Get western Ecuador statistics for a collection, either from cache or by calculating them.
    
    Args:
        collection_id (str): The collection ID to get stats for
        force_recalculate (bool): If True, force recalculation even if cached
        
    Returns:
        dict: Statistics dictionary with metadata
        
    Raises:
        ValueError: If collection_id is invalid
        Exception: If calculation fails
    """
    if collection_id not in ALLOWED_BENCHMARK_COLLECTIONS:
        raise ValueError(f"Invalid collection_id: {collection_id}")
    
    cache_key = get_cache_key(collection_id)
    
    # Check cache first (unless force recalculate)
    if not force_recalculate:
        cached_stats = cache.get(cache_key)
        if cached_stats:
            logger.info(f"✓ Returning cached western Ecuador stats for collection {collection_id}")
            return cached_stats
    
    # Calculate new stats
    logger.info(f"🔄 Starting simplified calculation of western Ecuador stats for collection {collection_id}")
    
    try:
        # Get required environment variables
        titiler_url = os.environ.get("TITILER_URL")
        if not titiler_url:
            raise Exception("TITILER_URL environment variable not set")
        
        logger.info(f"📍 Using TiTiler URL: {titiler_url}")
        
        # All collections now use the unified boundary-based approach
        logger.info("🚀 Using unified boundary-based calculation")
        aoi_stats = AOISummaryStats(titiler_url, collection_id)
        
        logger.info("🧮 Starting summary computation...")
        
        try:
            # Use the unified summary method (loads boundary automatically if no AOI provided)
            stats_df = aoi_stats.summary()
        except Exception as e:
            logger.error(f"❌ Summary computation failed: {str(e)}")
            raise
        
        if stats_df is None or stats_df.empty:
            raise Exception("AOISummaryStats returned empty results")
        
        stats_dict = stats_df.iloc[0].to_dict()
        logger.info(f"✓ Statistics computed successfully: {len(stats_dict)} metrics")
        
        # Add metadata
        stats_dict['collection_id'] = collection_id
        stats_dict['area_name'] = 'Western Ecuador'
        stats_dict['cached_at'] = timezone.now().isoformat()
        
        # Cache the result to disk
        logger.info(f"💾 Caching results to disk with key: {cache_key}")
        cache.set(cache_key, stats_dict)
        
        logger.info(f"🎉 Successfully calculated and cached western Ecuador stats for collection {collection_id}")
        logger.info(f"📈 Forest coverage: {stats_dict.get('pct_forest', 0) * 100:.1f}%, Total area: {stats_dict.get('forest_ha', 0) + stats_dict.get('nonforest_ha', 0):.1f} ha")
        
        return stats_dict
        
    except Exception as e:
        logger.error(f"❌ Failed to calculate western Ecuador stats for {collection_id}: {str(e)}")
        logger.error(f"💥 Error type: {type(e).__name__}")
        raise


def precalculate_all_stats(force_recalculate=False, collection_filter=None):
    """
    Pre-calculate western Ecuador statistics for all or specified collections.
    
    Args:
        force_recalculate (bool): If True, recalculate even if cached
        collection_filter (str): If provided, only calculate for this collection
        
    Returns:
        dict: Summary of results with 'successful', 'failed', and 'skipped' counts
    """
    collections_to_process = ALLOWED_BENCHMARK_COLLECTIONS
    if collection_filter:
        if collection_filter not in ALLOWED_BENCHMARK_COLLECTIONS:
            raise ValueError(f"Invalid collection: {collection_filter}")
        collections_to_process = [collection_filter]

    
    total_collections = len(collections_to_process)
    results = {'successful': 0, 'failed': 0, 'skipped': 0}
    
    logger.info(f"🚀 Starting pre-calculation for {total_collections} collection(s)")
    logger.info(f"📋 Collections to process: {', '.join(collections_to_process)}")
    
    for i, collection_id in enumerate(collections_to_process, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 Processing collection {i}/{total_collections}: {collection_id}")
        logger.info(f"{'='*60}")
        
        try:
            cache_key = get_cache_key(collection_id)
            
            # Check if already cached (unless force flag is used)
            if not force_recalculate and cache.get(cache_key):
                logger.info(f"⏭️  Skipping {collection_id} (already cached)")
                results['skipped'] += 1
                continue
            
            # Calculate stats
            logger.info(f"🎯 Starting calculation for {collection_id}...")
            start_time = timezone.now()
            
            get_western_ecuador_stats(collection_id, force_recalculate=True)
            
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            results['successful'] += 1
            logger.info(f"✅ Successfully completed {collection_id} in {duration:.1f} seconds")
            logger.info(f"📈 Progress: {results['successful'] + results['failed']} of {total_collections} completed")
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate stats for {collection_id}: {str(e)}")
            logger.error(f"💥 Error type: {type(e).__name__}")
            results['failed'] += 1
    
    logger.info(f"\n{'='*60}")
    logger.info(f"🏁 Pre-calculation completed!")
    logger.info(f"✅ Successful: {results['successful']}")
    logger.info(f"❌ Failed: {results['failed']}")
    logger.info(f"⏭️  Skipped: {results['skipped']}")
    logger.info(f"📊 Total: {total_collections}")
    logger.info(f"{'='*60}")
    
    return results


def clear_all_cached_stats():
    """Clear all cached western Ecuador statistics."""
    cleared_count = 0
    for collection_id in ALLOWED_BENCHMARK_COLLECTIONS:
        cache_key = get_cache_key(collection_id)
        if cache.delete(cache_key):
            cleared_count += 1
    
    logger.info(f"Cleared {cleared_count} cached western Ecuador statistics")
    return cleared_count
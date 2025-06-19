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
    "benchmarks-hansen-tree-cover-2022",
    "benchmarks-mapbiomes-2022", 
    "benchmarks-esa-landcover-2020",
    "benchmarks-jrc-forestcover-2020",
    "benchmarks-palsar-2020",
    "benchmarks-wri-treecover-2020",
    "nicfi-pred-northern_choco_test_2025_06_16-composite-2022",  # CFW composite
]


def get_cache_key(collection_id):
    """Get the cache key for a collection ID."""
    return f"western_ecuador_stats_{collection_id}"


def _load_boundary_polygon():
    """Load and cache the project boundary as a shapely geometry in Web Mercator projection."""
    global _global_boundary_polygon
    if _global_boundary_polygon is not None:
        return _global_boundary_polygon

    # Path to the GeoJSON that defines the project boundary. Allow override via env var.
    boundary_path = os.environ.get("BOUNDARY_GEOJSON_PATH")

    try:
        if boundary_path.startswith("http://") or boundary_path.startswith("https://"):
            resp = requests.get(boundary_path, timeout=30)
            resp.raise_for_status()
            geojson = resp.json()
        else:
            with open(boundary_path, "r", encoding="utf-8") as f:
                geojson = json.load(f)
        
        # Load geometries and convert to Web Mercator
        # Create transformer from WGS84 to Web Mercator
        project = Transformer.from_crs('EPSG:4326', 'EPSG:3857', always_xy=True).transform
        
        # Load and transform each geometry
        geoms = []
        for feat in geojson.get("features", []):
            geom = shape(feat["geometry"])
            # Transform to Web Mercator
            geom_3857 = transform(project, geom)
            geoms.append(geom_3857)
        
        if len(geoms) == 1:
            _global_boundary_polygon = geoms[0]
        else:
            _global_boundary_polygon = unary_union(geoms)
        
        return _global_boundary_polygon
    except Exception as e:
        logger.error(f"Failed to load boundary polygon: {e}")
        raise


def _convert_boundary_to_geojson(boundary_polygon):
    """Convert boundary polygon to GeoJSON format (WGS84)."""
    # Convert boundary polygon to GeoJSON format (WGS84)
    project_back = Transformer.from_crs('EPSG:3857', 'EPSG:4326', always_xy=True).transform
    boundary_wgs84 = transform(project_back, boundary_polygon)
    
    # Create GeoJSON feature
    boundary_geojson = {
        "type": "Feature",
        "geometry": {
            "type": boundary_wgs84.geom_type,
            "coordinates": list(boundary_wgs84.exterior.coords) if hasattr(boundary_wgs84, 'exterior') else boundary_wgs84.__geo_interface__['coordinates']
        }
    }
    
    return boundary_geojson


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
            logger.info(f"Returning cached western Ecuador stats for collection {collection_id}")
            return cached_stats
    
    # Calculate new stats
    logger.info(f"Calculating western Ecuador stats for collection {collection_id}")
    
    # Get required environment variables
    titiler_url = os.environ.get("TITILER_URL")
    if not titiler_url:
        raise Exception("TITILER_URL environment variable not set")
    
    # Get the boundary polygon
    boundary_polygon = _load_boundary_polygon()
    if not boundary_polygon:
        raise Exception("Could not load western Ecuador boundary")
    
    # Convert to GeoJSON
    boundary_geojson = _convert_boundary_to_geojson(boundary_polygon)
    
    # Calculate statistics using AOISummaryStats
    stats_df = AOISummaryStats(titiler_url, collection_id).summary(boundary_geojson)
    stats_dict = stats_df.iloc[0].to_dict()
    
    # Add metadata
    stats_dict['collection_id'] = collection_id
    stats_dict['area_name'] = 'Western Ecuador'
    stats_dict['cached_at'] = timezone.now().isoformat()
    
    # Cache the result to disk
    cache.set(cache_key, stats_dict)
    
    logger.info(f"Successfully calculated and cached western Ecuador stats for collection {collection_id}")
    return stats_dict


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
    
    results = {'successful': 0, 'failed': 0, 'skipped': 0}
    
    for collection_id in collections_to_process:
        try:
            cache_key = get_cache_key(collection_id)
            
            # Check if already cached (unless force flag is used)
            if not force_recalculate and cache.get(cache_key):
                logger.info(f"Skipping {collection_id} (already cached)")
                results['skipped'] += 1
                continue
            
            # Calculate stats
            get_western_ecuador_stats(collection_id, force_recalculate=True)
            results['successful'] += 1
            
        except Exception as e:
            logger.error(f"Failed to calculate stats for {collection_id}: {e}")
            results['failed'] += 1
    
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
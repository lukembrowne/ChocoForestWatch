# ml_pipeline/polygon_loader.py
import geopandas as gpd
from shapely.geometry import shape, MultiPolygon
import pandas as pd

def load_training_polygons(engine,
                           project_id: int,
                           basemap_date: str,
                           table: str = "core_trainingpolygonset",
                           geom_col: str = "polygons") -> gpd.GeoDataFrame:
    """Load training polygons from the database and convert them to a GeoDataFrame.

    This function retrieves training polygons from the specified database table,
    processes them from a GeoJSON FeatureCollection format, and returns them as
    a GeoDataFrame in EPSG:4326 (WGS84) coordinate system.

    Args:
        engine: SQLAlchemy database engine instance
        project_id (int): ID of the project to load polygons for
        basemap_date (str): Date of the basemap in format 'YYYY-MM'
        table (str, optional): Name of the database table containing polygons. 
            Defaults to "core_trainingpolygonset".
        geom_col (str, optional): Name of the geometry column in the table. 
            Defaults to "polygons".

    Returns:
        gpd.GeoDataFrame: A GeoDataFrame containing the training polygons with the following columns:
            - id: Unique identifier for each polygon
            - project_id: Project identifier
            - basemap_date: Date of the basemap
            - classLabel: Classification label for the polygon
            - geometry: Shapely geometry object (in EPSG:4326)

    Note:
        The function assumes the input geometry is stored as a GeoJSON FeatureCollection
        in the database. Each feature in the collection should have a geometry and
        properties containing at least a 'classLabel'.
    """
    
    q = f"""
      SELECT id, project_id, basemap_date, feature_count, {geom_col}
      FROM {table}
      WHERE excluded = false
        AND basemap_date = %s
        AND project_id = %s
    """
    raw = pd.read_sql(q, engine, params=(basemap_date, project_id))

    # If no data, return empty GeoDataFrame
    if raw.empty:
        return gpd.GeoDataFrame()

    rows = []
    for _, row in raw.iterrows():
        fc = row[geom_col]
        if isinstance(fc, dict) and fc.get("type") == "FeatureCollection":
            for feat in fc["features"]:
                geom = shape(feat["geometry"])
                rows.append(
                    {
                        "id": feat.get("id", row["id"]),
                        "project_id": row["project_id"],
                        "basemap_date": row["basemap_date"],
                        "classLabel": feat["properties"].get("classLabel", ""),
                        "geometry": geom,
                    }
                )
    # Converts from EPSG:3857 to EPSG:4326 (lat/lon)
    gdf = gpd.GeoDataFrame(rows, crs="EPSG:3857").to_crs("EPSG:4326")
    return gdf
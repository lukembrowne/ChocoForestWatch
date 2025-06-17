from __future__ import annotations
import pandas as pd
from shapely.geometry import shape
from ml_pipeline.extractor import TitilerExtractor
from ml_pipeline.raster_utils import pixels_to_labels, extract_pixels_with_missing

class AOISummaryStats:
    """
    Compute % forest / non-forest + area (ha) + missing % inside an arbitrary AOI.
    Example:
        stats = AOISummaryStats("http://localhost:8083", "benchmarks-hansen-tree-cover-2022")
        df = stats.summary(aoi_geojson)
    """

    def __init__(self, base_url: str, collection: str, *, band_indexes=[1]):
        self.collection = collection
        self.band_indexes = band_indexes
        self.extractor = TitilerExtractor(base_url.rstrip("/"), collection, band_indexes)
        # logger.info(
        #     "Initialized AOISummaryStats with base_url=%s, collection=%s, band_indexes=%s",
        #     base_url, collection, band_indexes
        # )
        print(f"Initialized AOISummaryStats with base_url={base_url}, collection={collection}, band_indexes={band_indexes}")

    def summary(self, aoi_geojson: dict) -> pd.DataFrame:
        geom = shape(aoi_geojson["geometry"])   # keeps CRS WGS84
        # logger.info("Starting summary computation for AOI with bounds: %s", geom.bounds)
        print(f"Starting summary computation for AOI with bounds: {geom.bounds}")
        px, missing_px, px_area_m2 = extract_pixels_with_missing(
            self.extractor, geom, self.band_indexes
        )

        if px.size == 0:
            raise RuntimeError("AOI has no valid pixels in this collection.")

        labels = pixels_to_labels(self.collection, px.squeeze())
        forest_px = (labels == "Forest").sum()
        nonforest_px = (labels == "Non-Forest").sum()

        if px_area_m2 is None:        # defensive; should never happen
            raise RuntimeError("Could not determine pixel area.")
        m2_to_ha = px_area_m2 / 10_000

        data = {
            "forest_px": forest_px,
            "nonforest_px": nonforest_px,
            "missing_px": missing_px,
            "pct_forest": forest_px / (forest_px + nonforest_px) if (forest_px + nonforest_px) else 0,
            "pct_missing": missing_px / (forest_px + nonforest_px + missing_px),
            "forest_ha": forest_px * m2_to_ha,
            "nonforest_ha": nonforest_px * m2_to_ha,
        }
        # logger.info(
        #     "Extracted %d valid pixels and %d pixels with missing data",
        #     px.size, missing_px
        # )
        print(f"Extracted {px.size} valid pixels and {missing_px} pixels with missing data")
        # logger.info(
        #     "Pixel classification counts — Forest: %d, Non-Forest: %d",
        #     forest_px, nonforest_px
        # )
        print(f"Pixel classification counts — Forest: {forest_px}, Non-Forest: {nonforest_px}")
        summary_df = pd.DataFrame([data])
        # logger.info("Computed summary statistics:\n%s", summary_df.to_string(index=False))
        print("Computed summary statistics:")
        return summary_df
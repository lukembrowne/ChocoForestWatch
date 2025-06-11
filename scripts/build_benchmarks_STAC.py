#%% 
from ml_pipeline.polygon_loader import load_training_polygons
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report
from ml_pipeline.extractor import TitilerExtractor
import numpy as np
from ml_pipeline.benchmark_metrics_io import (
    save_metrics_csv,
    load_all_metrics,
    show_accuracy_table,
    plot_accuracy,
)

from ml_pipeline.s3_utils import upload_file
from pathlib import Path
from ml_pipeline.db_utils import get_db_connection
from ml_pipeline.stac_builder import STACBuilder




#%% 
engine = get_db_connection()


# %%

# Process extermal benchmark datasets - Hansen Tree Cover

# Should maybe move this elsewhere since only have to do it once?


# # Hansen Tree Cover 2022
# tif_path = "./benchmark_rasters/TreeCover2022-Hansen_wec.tif"
# remote_key = f"benchmarks/HansenTreeCover/2022/{Path(tif_path).name}"
# upload_file(Path(tif_path), remote_key)

# from ml_pipeline.stac_builder import STACBuilder

# builder = STACBuilder()

# builder.process_year(
#     year=2022,
#     prefix="benchmarks/HansenTreeCover",
#     collection_id="benchmarks-hansen-tree-cover-2022",
#     asset_key="data",
#     asset_roles=["benchmark"],
#     asset_title="Hansen Tree Cover 2022",
# )

# # Ecuador MapBiomes 2022
# # MapBiomes Ecuador from Ecociencia 2022
# # Download Tif directly here - https://ecuador.mapbiomas.org/mapas-de-cobertura-y-uso/
# # Legend for values - https://ecuador.mapbiomas.org/wp-content/uploads/sites/7/2023/12/Ecuador_Legend-Code-Col-1.pdf
# # 3 = Forest, 4 = open forest
# # 21 = agriculture mosaic
# # 27 = not observed
# tif_path = "./benchmark_rasters/ecuador_coverage_2022_wec.tif"
# remote_key = f"benchmarks/MapBiomes/2022/{Path(tif_path).name}"
# upload_file(Path(tif_path), remote_key)


# builder = STACBuilder()

# builder.process_year(
#     year=2022,
#     prefix="benchmarks/MapBiomes",
#     collection_id="benchmarks-mapbiomes-2022",
#     asset_key="data",
#     asset_roles=["benchmark"],
#     asset_title="MapBiomes 2022",
# )


# # ESA Land Cover 2020
# tif_path = "./benchmark_rasters/LandCover2020-ESA_wec_merged.tif"
# remote_key = f"benchmarks/ESA-Landcover/2020/{Path(tif_path).name}"
# upload_file(Path(tif_path), remote_key)

# builder = STACBuilder()

# builder.process_year(
#     year=2020,
#     prefix="benchmarks/ESA-Landcover",
#     collection_id="benchmarks-esa-landcover-2020",
#     asset_key="data",
#     asset_roles=["benchmark"],
#     asset_title="ESA Land Cover 2020",
# )

# # JRC Forest Cover 2020
# tif_path = "./benchmark_rasters/ForestCover2020-JRC_wec_merged.tif"
# remote_key = f"benchmarks/JRC-ForestCover/2020/{Path(tif_path).name}"
# upload_file(Path(tif_path), remote_key)

# builder = STACBuilder()

# builder.process_year(
#     year=2020,
#     prefix="benchmarks/JRC-ForestCover",
#     collection_id="benchmarks-jrc-forestcover-2020",
#     asset_key="data",
#     asset_roles=["benchmark"],
#     asset_title="JRC Forest Cover 2020",
# )

# # PALSAR-2 2020
# # PALSAR-2 - Global 4-class PALSAR-2/PALSAR Forest/Non-Forest Map 
# # https://developers.google.com/earth-engine/datasets/catalog/JAXA_ALOS_PALSAR_YEARLY_FNF4#description
# tif_path = "./benchmark_rasters/PALSAR2020_wec.tif"
# remote_key = f"benchmarks/PALSAR/2020/{Path(tif_path).name}"
# upload_file(Path(tif_path), remote_key)

# builder = STACBuilder()

# builder.process_year(
#     year=2020,
#     prefix="benchmarks/PALSAR",
#     collection_id="benchmarks-palsar-2020",
#     asset_key="data",
#     asset_roles=["benchmark"],
#     asset_title="PALSAR 2020",
# )



# # WRI Tree Cover 2020
# tif_path = "./benchmark_rasters/TreeCover2020-WRI_wec_merged.tif"
# remote_key = f"benchmarks/WRI-TreeCover/2020/{Path(tif_path).name}"
# upload_file(Path(tif_path), remote_key)

# builder = STACBuilder()

# builder.process_year(
#     year=2020,
#     prefix="benchmarks/WRI-TreeCover",
#     collection_id="benchmarks-wri-treecover-2020",
#     asset_key="data",
#     asset_roles=["benchmark"],
#     asset_title="WRI Tree Cover 2020",
# )
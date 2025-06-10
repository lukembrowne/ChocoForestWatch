import xarray as xr
import rioxarray
import numpy as np
from pathlib import Path
from osgeo import gdal, gdalconst
import rasterio
from ml_pipeline.stac_builder import STACBuilder
from ml_pipeline.s3_utils import upload_file
import tempfile
import shutil

class CompositeGenerator:
    def __init__(self, run_id: str, year: str, root: str = "runs"):
        self.run_id = run_id
        self.year = year
        self.root = Path(root)
        self.run_path = self.root / run_id
        self.temp_dir = None
        
    def __enter__(self):
        """Create temporary directory when entering context."""
        self.temp_dir = tempfile.mkdtemp()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up temporary directory when exiting context."""
        if self.temp_dir:
            shutil.rmtree(self.temp_dir)
        
    def generate_composite(self, quad_name: str, min_pixels: int = 10):
        """Generate annual composite for a given quad."""
        if not self.temp_dir:
            raise RuntimeError("CompositeGenerator must be used as a context manager")
            
        # List monthly COGs
        months = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        cogs = [
            f"s3://choco-forest-watch/predictions/{self.run_id}/{self.year}/{m:02d}/{quad_name}_{self.year}_{m:02d}.tiff"
            for m in months
        ]

        print("Retrieving monthly COGs...")
        print("Retrieved COGs: ", cogs)

        # Open and stack monthly data
        print("Stacking monthly data...")
        stacked = self._stack_monthly_data(cogs)
        print("Stacked monthly data.")
        
        # Generate forest flag
        print("Generating forest flag...")
        forest_flag = self._generate_forest_flag(stacked)
        print("Generated forest flag.")
        
        # Create output files in temp directory
        print("Creating output files...")
        stacked_path, cover_path = self._create_output_files(quad_name, forest_flag, stacked, min_pixels)
        print("Created output files.")
        
        try:
            # Upload to S3
            print("Uploading to S3...")
            self._upload_to_s3(quad_name, cover_path)
            print("Uploaded to S3.")

        finally:
            # Clean up temp files
            # if stacked_path.exists():
            #     stacked_path.unlink()
            if cover_path.exists():
                cover_path.unlink()
        
    def _stack_monthly_data(self, cogs):
        """Stack monthly data into a single xarray."""
        def open_month(url):
            da = rioxarray.open_rasterio(url, masked=True)
            month = url.split('_')[-1].split('.')[0]
            return da.expand_dims(time=[month])
            
        return xr.concat([open_month(u) for u in cogs], dim="time").load()
        
    def _generate_forest_flag(self, stacked):
        """Generate forest flag from stacked data."""
        data = stacked.sel(band=1)
        
        # Count clear observations
        valid = (~data.isin([2, 3, 5, 6, 255])).sum("time")
        
        # Majority vote
        masked = data.where(~data.isin([2, 3, 5, 6]))
        class_counts = xr.concat(
            [(masked == v).sum("time").assign_coords(class_val=v)
             for v in [0, 1, 4]],
            dim="class_val"
        )
        
        majority = class_counts.argmax("class_val").astype(np.uint8)
        
        # Forest flag
        forest_flag = majority.where(valid >= 2, 255)
        forest_flag = (forest_flag == 0).astype(np.uint8)
        forest_flag = forest_flag.where(valid >= 2, 255)
        
        return forest_flag
        
    def _create_output_files(self, quad_name, forest_flag, stacked, min_pixels):
        """Create and save output files in temp directory."""
        # Create stacked file
        # stacked_stack = stacked.squeeze("band", drop=True)
        # stacked_stack = (
        #     stacked_stack.rename(time="band")
        #     .assign_coords(band=("band", range(1, len(stacked.time) + 1)))
        #     .transpose("band", "y", "x")
        # )
        
        # Save stacked file
        # stacked_path = Path(self.temp_dir) / f"{quad_name}_{self.year}_forest_stacked.tif"
        # out = xr.concat([forest_flag, stacked_stack], dim="band").transpose("band", "y", "x")
        # out.rio.to_raster(
        #     stacked_path,
        #     dtype="uint8", tiled=True, compress="deflate"
        # )
        stacked_path = None
        
        # Save forest cover file
        cover_path = Path(self.temp_dir) / f"{quad_name}_{self.year}_forest_cover.tif"
        out = xr.concat([forest_flag], dim="band").transpose("band", "y", "x")
        out.rio.to_raster(
            cover_path,
            dtype="uint8", tiled=True, compress="deflate"
        )
        
        # Apply sieve filter
        self._apply_sieve_filter(cover_path, min_pixels)
        
        return stacked_path, cover_path
        
    def _apply_sieve_filter(self, tif_path, min_pixels):
        """Apply sieve filter to remove small objects."""
        gdal.UseExceptions()
        ds = gdal.Open(str(tif_path), gdalconst.GA_Update)
        if ds is None:
            raise RuntimeError(f"GDAL failed to open {tif_path!s}")
            
        band = ds.GetRasterBand(1)
        nodata = band.GetNoDataValue()
        
        gdal.SieveFilter(
            srcBand=band,
            maskBand=None,
            dstBand=band,
            threshold=min_pixels,
            connectedness=8
        )
        
        if nodata is not None:
            band.SetNoDataValue(nodata)
            
        band.FlushCache()
        ds = None
        
    def _upload_to_s3(self, quad_name, cover_path):
        """Upload to S3 and create STAC collection."""
        # Upload stacked file
        # stacked_remote_key = f"predictions/{self.run_id}-composites/{self.year}/{quad_name}_{self.year}_forest_stacked.tif"
        # upload_file(stacked_path, stacked_remote_key)
        
        # Upload forest cover file
        cover_remote_key = f"predictions/{self.run_id}-composites/{self.year}/{quad_name}_{self.year}_forest_cover.tif"
        upload_file(cover_path, cover_remote_key)
        
    def _create_stac_collection(self):
        # Create STAC
        builder = STACBuilder()
        builder.process_year(
            year=self.year,
            prefix_on_s3=f"predictions/{self.run_id}-composites",
            collection_id=f"nicfi-pred-{self.run_id}-composite-{self.year}",
            asset_key="data",
            asset_roles=["classification"],
            asset_title=f"Annual Forest Cover Composite for {self.run_id}",
            extra_asset_fields={
                "raster:bands": [
                    {
                        "name": "forest_flag",
                        "nodata": 255,
                        "data_type": "uint8",
                        "description": "Forest flag (1=Forest, 0=Non-Forest, 255=No Data)"
                    }
                ]
            }
        ) 
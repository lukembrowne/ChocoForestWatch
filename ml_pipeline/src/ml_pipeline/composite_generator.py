import xarray as xr
import rioxarray
import numpy as np
from pathlib import Path
from osgeo import gdal, gdalconst
import rasterio
from ml_pipeline.stac_builder import STACManager, STACManagerConfig
from ml_pipeline.s3_utils import upload_file, list_files, download_file
import tempfile
import shutil
import logging

class CompositeGenerator:
    def __init__(self, run_id: str, year: str, root: str = None):
        self.run_id = run_id
        self.year = year
        
        if root is None:
            # Use the same logic as RunManager for consistent paths
            # Go up from src/ml_pipeline to ml_pipeline root
            ml_pipeline_root = Path(__file__).parent.parent.parent
            self.root = ml_pipeline_root / "runs"
        else:
            self.root = Path(root)
            
        self.run_path = self.root / run_id
        self.temp_dir = None
        self.local_composite_files = []  # Track local composite files for merging
        
    def __enter__(self):
        """Create temporary directory when entering context."""
        self.temp_dir = tempfile.mkdtemp()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up temporary directory when exiting context."""
        # Only clean up local composite files if they're in temp directory
        # Don't clean up files that have been moved to persistent location
        temp_files_to_clean = [f for f in self.local_composite_files if str(f).startswith(str(self.temp_dir)) if self.temp_dir]
        for temp_file in temp_files_to_clean:
            if Path(temp_file).exists():
                Path(temp_file).unlink()
        
        if self.temp_dir:
            shutil.rmtree(self.temp_dir)
        
    def generate_composite(self, quad_name: str, min_pixels: int = 10, skip_s3_upload: bool = False, use_local_files: bool = False):
        """Generate annual composite for a given quad."""
        if not self.temp_dir:
            raise RuntimeError("CompositeGenerator must be used as a context manager")
            
        # List monthly COGs
        months = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        
        if use_local_files:
            # Discover which months actually have prediction files for this quad
            pred_base_dir = self.run_path / "prediction_cogs" / self.year
            available_months = []
            
            for month_dir in sorted(pred_base_dir.glob("*")):
                if month_dir.is_dir():
                    # Check if this quad has a file in this month
                    quad_file = month_dir / f"{quad_name}_{self.year}_{month_dir.name}.tiff"
                    if quad_file.exists():
                        available_months.append(int(month_dir.name))
            
            if not available_months:
                raise FileNotFoundError(f"No prediction files found for quad {quad_name} in {pred_base_dir.absolute()}")
            
            print(f"Found prediction files for quad {quad_name} in months: {available_months}")
            
            # Use absolute paths for only available months
            cogs = [
                str(self.run_path.absolute() / f"prediction_cogs/{self.year}/{m:02d}/{quad_name}_{self.year}_{m:02d}.tiff")
                for m in available_months
            ]
        else:
            # Use S3 paths
            cogs = [
                f"s3://choco-forest-watch/predictions/{self.run_id}/{self.year}/{m:02d}/{quad_name}_{self.year}_{m:02d}.tiff"
                for m in months
            ]

        print("Retrieving monthly COGs...")
        print(f"Retrieved {len(cogs)} COGs: {cogs}")

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
            if skip_s3_upload:
                # Keep local file for later merging - move to persistent composites directory
                print("Skipping S3 upload, keeping file for local merging...")
                
                # Create composites directory in run path
                composites_dir = self.run_path / "composites"
                composites_dir.mkdir(exist_ok=True)
                
                # Move file from temp to persistent location
                persistent_path = composites_dir / cover_path.name
                import shutil
                shutil.move(str(cover_path), str(persistent_path))
                
                self.local_composite_files.append(persistent_path)
                print(f"Moved composite to persistent location: {persistent_path}")
                return str(persistent_path)  # Return path for tracking
            else:
                # Upload to S3
                print("Uploading to S3...")
                self._upload_to_s3(quad_name, cover_path)
                print("Uploaded to S3.")

        except Exception as e:
            # Clean up on error
            if cover_path.exists():
                cover_path.unlink()
            if skip_s3_upload and len(self.local_composite_files) > 0:
                # Clean up the last added file if it exists
                last_file = self.local_composite_files[-1]
                if Path(last_file).exists():
                    Path(last_file).unlink()
                self.local_composite_files.pop()
            raise
        finally:
            # Clean up temp files only if not keeping for local merge
            if not skip_s3_upload and cover_path.exists():
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
    
    def cleanup_local_files(self):
        """Clean up locally stored composite files."""
        for file_path in self.local_composite_files:
            if Path(file_path).exists():
                Path(file_path).unlink()
        self.local_composite_files.clear()
        
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
        
        # Upload forest cover file to unified datasets structure
        cover_remote_key = f"datasets/cfw-{self.run_id}/{self.year}/{quad_name}_{self.year}_forest_cover.tif"
        upload_file(cover_path, cover_remote_key)
        
    def merge_composites(self, use_local_files: bool = False):
        """Merge all individual composite COGs into a single mosaic COG."""
        if not self.temp_dir:
            raise RuntimeError("CompositeGenerator must be used as a context manager")
            
        logger = logging.getLogger(__name__)
        logger.info(f"🔄 Starting merge of composite COGs for {self.run_id}-{self.year}")
        
        if use_local_files:
            # Discover local composite files from the composites directory
            composites_dir = self.run_path / "composites"
            if not composites_dir.exists():
                logger.warning(f"⚠️  Composites directory not found: {composites_dir}")
                return None
                
            # Find all composite files in the directory
            composite_files = list(composites_dir.glob("*_forest_cover.tif"))
            if not composite_files:
                logger.warning(f"⚠️  No composite files found in: {composites_dir}")
                return None
                
            logger.info(f"📊 Found {len(composite_files)} local composite files to merge")
            
            if len(composite_files) <= 1:
                logger.info("ℹ️  Only one or no local files found, skipping merge")
                return None
                
            local_cog_paths = [str(f) for f in composite_files]
            logger.info(f"✅ Using {len(local_cog_paths)} local COG files")
        else:
            # Original S3-based workflow
            # List all individual composite COGs from S3
            s3_prefix = f"datasets/cfw-{self.run_id}/{self.year}/"
            s3_files = list_files(prefix=s3_prefix)
            
            if not s3_files:
                logger.warning(f"⚠️  No composite files found at {s3_prefix}")
                return None
                
            cog_files = [f for f in s3_files if f['key'].endswith('_forest_cover.tif')]
            logger.info(f"📊 Found {len(cog_files)} individual composite COGs to merge")
            
            if len(cog_files) <= 1:
                logger.info("ℹ️  Only one or no COG files found, skipping merge")
                return None
                
            # Download all COGs to temp directory
            logger.info("⬇️  Downloading individual COGs...")
            local_cog_paths = []
            
            for i, cog_file in enumerate(cog_files):
                local_path = Path(self.temp_dir) / f"composite_{i:04d}.tif"
                download_file(cog_file['key'], local_path)
                local_cog_paths.append(str(local_path))
                
            logger.info(f"✅ Downloaded {len(local_cog_paths)} COG files")
        
        # Create merged COG using GDAL
        if use_local_files:
            # Save merged file to persistent composites directory
            composites_dir = self.run_path / "composites"
            composites_dir.mkdir(exist_ok=True)
            merged_path = composites_dir / f"{self.run_id}_{self.year}_merged_composite.tif"
        else:
            # Use temp directory for S3 workflow
            merged_path = Path(self.temp_dir) / f"{self.run_id}_{self.year}_merged_composite.tif"
            
        logger.info(f"🔗 Merging COGs into: {merged_path.name}")
        
        # Use GDAL BuildVRT and Translate for efficient merging
        vrt_path = Path(self.temp_dir) / f"{self.run_id}_{self.year}_temp.vrt"
        
        # Initialize intermediate_path for finally block
        intermediate_path = Path(self.temp_dir) / f"{self.run_id}_{self.year}_intermediate.tif"
        
        try:
            # Build VRT first for efficient handling of overlapping regions
            vrt_options = gdal.BuildVRTOptions(
                resampleAlg='nearest',
                addAlpha=False,
                hideNodata=True
            )
            gdal.BuildVRT(str(vrt_path), local_cog_paths, options=vrt_options)
            
            # Translate VRT to intermediate GeoTIFF
            translate_options = gdal.TranslateOptions(
                format='GTiff',
                creationOptions=[
                    'TILED=YES',
                    'COMPRESS=DEFLATE',
                    'PREDICTOR=1',
                    'BIGTIFF=IF_SAFER'
                ]
            )
            
            gdal.Translate(str(intermediate_path), str(vrt_path), options=translate_options)
            
            # Add overviews to intermediate file
            logger.info("📈 Adding overviews to merged raster...")
            ds = gdal.Open(str(intermediate_path), gdal.GA_Update)
            if ds is None:
                raise RuntimeError(f"Failed to open intermediate file: {intermediate_path}")
            ds.BuildOverviews("NEAREST", [2, 4, 8, 16, 32])
            ds = None
            
            # Convert to proper COG format
            logger.info("🔄 Converting to Cloud Optimized GeoTIFF...")
            cog_options = gdal.TranslateOptions(
                format='GTiff',
                creationOptions=[
                    'COPY_SRC_OVERVIEWS=YES',
                    'TILED=YES',
                    'COMPRESS=DEFLATE',
                    'PREDICTOR=1',
                    'BIGTIFF=IF_SAFER'
                ]
            )
            
            gdal.Translate(str(merged_path), str(intermediate_path), options=cog_options)
            
            logger.info(f"✅ Successfully merged {len(local_cog_paths)} COGs into single file")
            
            if use_local_files:
                # For local workflow, return the local path
                logger.info(f"🎉 Merge completed successfully, saved to: {merged_path}")
                return str(merged_path)
            else:
                # Upload merged COG to S3
                merged_s3_key = f"datasets/cfw-{self.run_id}/{self.year}/{self.run_id}_{self.year}_merged_composite.tif"
                logger.info(f"⬆️  Uploading merged COG to S3: {merged_s3_key}")
                upload_file(merged_path, merged_s3_key)
                
                logger.info("🎉 Merge and upload completed successfully")
                return merged_s3_key
            
        except Exception as e:
            logger.error(f"❌ Error during COG merge: {str(e)}")
            raise
        finally:
            # Clean up temp files
            if vrt_path.exists():
                vrt_path.unlink()
            if intermediate_path.exists():
                intermediate_path.unlink()
            
            # Clean up downloaded files (but not local composite files if using local workflow)
            if not use_local_files:
                for local_path in local_cog_paths:
                    if Path(local_path).exists():
                        Path(local_path).unlink()
            
            # Only clean up merged file if using S3 workflow (temp file)
            # For local workflow, keep the merged file in persistent location
            if not use_local_files and merged_path.exists():
                merged_path.unlink()
                
            # Keep local composite files for subsequent pipeline steps
            # Don't clean up local files in local-only workflows
            if not use_local_files:  # Only clean up if using S3 workflow
                self.cleanup_local_files()
        
    def _create_stac_collection(self, use_remote_db: bool, use_merged_cog: bool = False):
        """Create STAC collection for either individual COGs or merged COG."""
        logger = logging.getLogger(__name__)
        
        # Create STAC
        logger.info(f"Creating STAC collection for {self.run_id} with remote db: {use_remote_db}, merged: {use_merged_cog}")
        builder = STACManager(STACManagerConfig(use_remote_db=use_remote_db))

        if use_merged_cog:
            # For merged COG, we need to create a collection with just the merged file
            logger.info(f"Processing merged COG for {self.run_id}")
            
            # Check if merged COG exists
            merged_key = f"datasets/cfw-{self.run_id}/{self.year}/{self.run_id}_{self.year}_merged_composite.tif"
            s3_files = list_files(prefix=f"datasets/cfw-{self.run_id}/{self.year}/")
            merged_files = [f for f in s3_files if f['key'].endswith('_merged_composite.tif')]
            
            if not merged_files:
                logger.warning(f"⚠️  No merged COG found, falling back to individual COGs")
                use_merged_cog = False
            else:
                logger.info(f"✅ Found merged COG: {merged_files[0]['key']}")
        
        if use_merged_cog:
            # For merged COG, temporarily rename individual files or adjust the approach
            # Since process_year doesn't support file filtering, we'll use a different strategy
            logger.info("📚 Creating STAC collection for merged COG...")
            
            # Create a temporary custom collection for the merged file
            self._create_merged_stac_collection(builder)
        else:
            # Create STAC collection for individual COGs (original behavior)
            logger.info(f"Processing individual COGs for {self.run_id}")
            builder.process_year(
                year=self.year,
                prefix_on_s3=f"datasets/cfw-{self.run_id}",
                collection_id=f"datasets-cfw-{self.run_id}-{self.year}",
                asset_key="data",
                asset_roles=["classification"],
                asset_title=f"ChocoForestWatch Annual Forest Cover - {self.run_id}",
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
    
    def _create_merged_stac_collection(self, builder):
        """Create STAC collection specifically for merged COG files."""
        logger = logging.getLogger(__name__)
        
        # Get the merged file from S3
        s3_files = list_files(prefix=f"datasets/cfw-{self.run_id}/{self.year}/")
        merged_files = [f for f in s3_files if f['key'].endswith('_merged_composite.tif')]
        
        if not merged_files:
            logger.error("❌ No merged COG files found for STAC collection creation")
            return
            
        # Process only the merged files manually
        collection_id = f"datasets-cfw-{self.run_id}-{self.year}"
        
        # Use the existing process_year method but with a prefix that only matches merged files
        # We'll temporarily copy the merged file to a separate location to isolate it
        temp_prefix = f"datasets/cfw-{self.run_id}-merged/{self.year}/"
        
        # Copy merged file to temporary location for STAC processing
        from ml_pipeline.s3_utils import copy_s3_object
        
        for merged_file in merged_files:
            source_key = merged_file['key']
            filename = source_key.split('/')[-1]
            dest_key = f"{temp_prefix}{filename}"
            
            try:
                copy_s3_object(source_key, dest_key)
                logger.info(f"📁 Copied merged file for STAC: {dest_key}")
                
                # Now process with the isolated prefix
                builder.process_year(
                    year=self.year,
                    prefix_on_s3=f"datasets/cfw-{self.run_id}-merged",
                    collection_id=collection_id,
                    asset_key="data",
                    asset_roles=["classification"],
                    asset_title=f"ChocoForestWatch Annual Forest Cover - {self.run_id} (Merged)",
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
                
                # Clean up temporary copy
                from ml_pipeline.s3_utils import delete_s3_object
                delete_s3_object(dest_key)
                logger.info(f"🗑️  Cleaned up temporary file: {dest_key}")
                
            except Exception as e:
                logger.error(f"❌ Error processing merged COG for STAC: {str(e)}")
                raise 
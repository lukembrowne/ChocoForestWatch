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
        
    def generate_composite(self, quad_name: str, min_pixels: int = 10, skip_s3_upload: bool = False, use_local_files: bool = False, algorithm: str = 'majority_vote'):
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
        print(f"Generating forest flag using {algorithm} algorithm...")
        forest_flag = self._generate_forest_flag(stacked, algorithm)
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
        
    def _generate_forest_flag(self, stacked, algorithm='majority_vote'):
        """Generate forest flag from stacked data.
        
        Args:
            stacked: xarray dataset with time series data
            algorithm: Algorithm to use ('majority_vote', 'temporal_trend', 'change_point', 'latest_valid', 'weighted_temporal')
        """
        data = stacked.sel(band=1)
        
        # Count clear observations
        valid = (~data.isin([2, 3, 5, 6, 255])).sum("time") # Don't count cloud, shadow, haze, sensor error, or no data
        
        if algorithm == 'majority_vote':
            return self._majority_vote_algorithm(data, valid)
        elif algorithm == 'temporal_trend':
            return self._temporal_trend_algorithm(data, valid)
        elif algorithm == 'change_point':
            return self._change_point_algorithm(data, valid)
        elif algorithm == 'latest_valid':
            return self._latest_valid_algorithm(data, valid)
        elif algorithm == 'weighted_temporal':
            return self._weighted_temporal_algorithm(data, valid)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}. Available: 'majority_vote', 'temporal_trend', 'change_point', 'latest_valid', 'weighted_temporal'")
    
    def _majority_vote_algorithm(self, data, valid):
        """Original majority vote algorithm."""
        # Majority vote
        masked = data.where(~data.isin([2, 3, 5, 6])) # Don't count cloud, shadow, haze, sensor error, or no data
        class_counts = xr.concat(
            [(masked == v).sum("time").assign_coords(class_val=v)
             for v in [0, 1, 4]], # Count forest, non-forest, and water
            dim="class_val"
        )
        
        majority = class_counts.argmax("class_val").astype(np.uint8) # Choose majority
        
        # Forest flag
        forest_flag = majority.where(valid >= 2, 255)
        forest_flag = (forest_flag == 0).astype(np.uint8)
        forest_flag = forest_flag.where(valid >= 2, 255)
        
        return forest_flag
    
    def _temporal_trend_algorithm(self, data, valid):
        """Temporal trend algorithm that considers time series patterns for deforestation detection."""
        # Mask invalid observations
        masked = data.where(~data.isin([2, 3, 5, 6])) # Don't count cloud, shadow, haze, sensor error, or no data
        
        # Apply the temporal trend logic pixel by pixel
        def analyze_temporal_trend(pixel_series):
            # Remove NaN values and get valid time series
            if hasattr(pixel_series, 'dropna'):
                valid_series = pixel_series.dropna('time')
                values = valid_series.values
            else:
                # Handle numpy array case
                values = pixel_series[~np.isnan(pixel_series)]
            
            if len(values) < 2:
                return 255  # Not enough data
            
            # Helper function to get runs of consecutive values
            def get_runs(arr):
                if len(arr) == 0:
                    return []
                runs = []
                current_val = arr[0]
                current_count = 1
                
                for i in range(1, len(arr)):
                    if arr[i] == current_val:
                        current_count += 1
                    else:
                        runs.append((current_val, current_count))
                        current_val = arr[i]
                        current_count = 1
                runs.append((current_val, current_count))
                return runs
            
            # Get runs of consecutive values
            runs = get_runs(values)
            
            # Recent consensus: if last 2-3 observations are consistent, use that
            if len(values) >= 2:
                recent_values = values[-2:]  # Last 2 values
                if len(recent_values) >= 2 and np.all(recent_values == recent_values[0]):
                    # Check if it's a valid class (forest=0, non-forest=1, water=4)
                    if recent_values[0] in [0, 1, 4]:
                        return 1 if recent_values[0] == 0 else 0  # Convert to forest flag
                
                # Check last 3 if available
                if len(values) >= 3:
                    recent_values = values[-3:]
                    if len(recent_values) >= 3 and np.all(recent_values == recent_values[0]):
                        if recent_values[0] in [0, 1, 4]:
                            return 1 if recent_values[0] == 0 else 0
            
            # Change point detection: look for forest -> non-forest transitions
            if len(runs) >= 2:
                # Check if we have a clear transition from forest to non-forest
                for i in range(len(runs) - 1):
                    current_class, current_count = runs[i]
                    next_class, next_count = runs[i + 1]
                    
                    # Forest to non-forest transition with sufficient evidence
                    if (current_class == 0 and next_class == 1 and 
                        current_count >= 2 and next_count >= 1):
                        return 0  # Non-forest (deforestation detected)
                    
                    # Non-forest to forest transition (reforestation)
                    if (current_class == 1 and next_class == 0 and 
                        current_count >= 2 and next_count >= 2):
                        return 1  # Forest (reforestation detected)
            
            # Run length analysis: filter out isolated classifications
            if len(runs) >= 3:
                # Look for pattern like [forest, isolated_non_forest, forest]
                for i in range(1, len(runs) - 1):
                    prev_class, prev_count = runs[i - 1]
                    curr_class, curr_count = runs[i]
                    next_class, next_count = runs[i + 1]
                    
                    # Isolated non-forest between forest observations (likely noise)
                    if (prev_class == 0 and curr_class == 1 and next_class == 0 and
                        curr_count == 1 and prev_count >= 1 and next_count >= 1):
                        # Filter out the isolated observation and treat as forest
                        return 1  # Forest
                    
                    # Isolated forest between non-forest observations (likely noise)
                    if (prev_class == 1 and curr_class == 0 and next_class == 1 and
                        curr_count == 1 and prev_count >= 1 and next_count >= 1):
                        # Filter out the isolated observation and treat as non-forest
                        return 0  # Non-forest
            
            # Fallback to majority vote if no clear temporal pattern
            counts = {0: 0, 1: 0, 4: 0}  # forest, non-forest, water
            for val in values:
                if val in counts:
                    counts[val] += 1
            
            # Find majority class
            max_count = max(counts.values())
            if max_count == 0:
                return 255  # No valid data
            
            # Get the class with maximum count
            majority_class = max(counts, key=counts.get)
            
            # Convert to forest flag (1=forest, 0=non-forest)
            return 1 if majority_class == 0 else 0
        
        # Apply the analysis to each pixel
        forest_flag = xr.apply_ufunc(
            analyze_temporal_trend,
            masked,
            input_core_dims=[['time']],
            output_core_dims=[[]],
            vectorize=True,
            dask='parallelized',
            output_dtypes=[np.uint8]
        )
        
        # Apply minimum valid observations requirement (3 observations needed for pattern recognition)
        forest_flag = forest_flag.where(valid >= 3, 255)
        
        return forest_flag
    
    def _change_point_algorithm(self, data, valid):
        """Change point detection algorithm that identifies significant transitions in time series."""
        # Mask invalid observations
        masked = data.where(~data.isin([2, 3, 5, 6])) # Don't count cloud, shadow, haze, sensor error, or no data
        
        def detect_change_point(pixel_series):
            # Remove NaN values and get valid time series
            if hasattr(pixel_series, 'dropna'):
                valid_series = pixel_series.dropna('time')
                values = valid_series.values
            else:
                # Handle numpy array case
                values = pixel_series[~np.isnan(pixel_series)]
            
            if len(values) < 3:
                return 255  # Not enough data for change point detection
            n = len(values)
            
            # Only consider forest (0) and non-forest (1) for change point detection
            # Convert water (4) to non-forest (1) for simplicity
            binary_values = np.where(values == 0, 0, 1)
            
            # Find the best change point by testing different split positions
            best_score = -np.inf
            best_changepoint = None
            best_post_change_class = None
            
            # Test change points from position 1 to n-2 (need at least 1 observation on each side)
            for cp in range(1, n - 1):
                pre_segment = binary_values[:cp]
                post_segment = binary_values[cp:]
                
                # Calculate dominant class in each segment
                pre_forest_count = np.sum(pre_segment == 0)
                pre_nonforest_count = np.sum(pre_segment == 1)
                post_forest_count = np.sum(post_segment == 0)
                post_nonforest_count = np.sum(post_segment == 1)
                
                # Determine dominant class in each segment
                pre_dominant = 0 if pre_forest_count > pre_nonforest_count else 1
                post_dominant = 0 if post_forest_count > post_nonforest_count else 1
                
                # Only consider this a valid change point if the dominant classes differ
                if pre_dominant != post_dominant:
                    # Calculate confidence scores based on segment homogeneity
                    pre_confidence = max(pre_forest_count, pre_nonforest_count) / len(pre_segment)
                    post_confidence = max(post_forest_count, post_nonforest_count) / len(post_segment)
                    
                    # Score is the product of confidences weighted by segment lengths
                    score = (pre_confidence * len(pre_segment) + post_confidence * len(post_segment)) / n
                    
                    # Bonus for deforestation (forest -> non-forest) to prioritize these changes
                    if pre_dominant == 0 and post_dominant == 1:
                        score *= 1.2
                    
                    if score > best_score:
                        best_score = score
                        best_changepoint = cp
                        best_post_change_class = post_dominant
            
            # If we found a significant change point, use post-change classification
            if best_changepoint is not None and best_score > 0.6:  # Threshold for significance
                return 1 if best_post_change_class == 0 else 0  # Convert to forest flag
            
            # Fallback to majority vote if no significant change point detected
            forest_count = np.sum(binary_values == 0)
            nonforest_count = np.sum(binary_values == 1)
            
            if forest_count > nonforest_count:
                return 1  # Forest
            elif nonforest_count > forest_count:
                return 0  # Non-forest
            else:
                # Tie - use the last observation
                return 1 if binary_values[-1] == 0 else 0
        
        # Apply the change point detection to each pixel
        forest_flag = xr.apply_ufunc(
            detect_change_point,
            masked,
            input_core_dims=[['time']],
            output_core_dims=[[]],
            vectorize=True,
            dask='parallelized',
            output_dtypes=[np.uint8]
        )
        
        # Apply minimum valid observations requirement (4 observations needed for statistical significance)
        forest_flag = forest_flag.where(valid >= 4, 255)
        
        return forest_flag
    
    def _latest_valid_algorithm(self, data, valid):
        """Latest valid algorithm that uses the most recent valid observation."""
        # Mask invalid observations
        masked = data.where(~data.isin([2, 3, 5, 6])) # Don't count cloud, shadow, haze, sensor error, or no data
        
        def get_latest_valid(pixel_series):
            # Remove NaN values and get valid time series
            if hasattr(pixel_series, 'dropna'):
                valid_series = pixel_series.dropna('time')
                values = valid_series.values
            else:
                # Handle numpy array case
                values = pixel_series[~np.isnan(pixel_series)]
            
            if len(values) < 1:
                return 255  # No valid data
            
            # Get the last valid observation
            latest_value = values[-1]
            
            # Convert to forest flag (1=forest, 0=non-forest)
            if latest_value == 0:  # Forest
                return 1
            elif latest_value in [1, 4]:  # Non-forest or water
                return 0
            else:
                return 255  # Invalid value
        
        # Apply the latest valid logic to each pixel
        forest_flag = xr.apply_ufunc(
            get_latest_valid,
            masked,
            input_core_dims=[['time']],
            output_core_dims=[[]],
            vectorize=True,
            dask='parallelized',
            output_dtypes=[np.uint8]
        )
        
        # Apply minimum valid observations requirement
        forest_flag = forest_flag.where(valid >= 1, 255)  # Only need 1 valid observation
        
        return forest_flag
    
    def _weighted_temporal_algorithm(self, data, valid):
        """Weighted temporal algorithm that weights recent observations higher."""
        # Mask invalid observations
        masked = data.where(~data.isin([2, 3, 5, 6])) # Don't count cloud, shadow, haze, sensor error, or no data
        
        def weighted_classification(pixel_series):
            # Remove NaN values and get valid time series
            if hasattr(pixel_series, 'dropna'):
                valid_series = pixel_series.dropna('time')
                values = valid_series.values
            else:
                # Handle numpy array case
                values = pixel_series[~np.isnan(pixel_series)]
            
            if len(values) < 1:
                return 255  # No valid data
            n = len(values)
            
            # Create exponential decay weights (recent observations have higher weights)
            # Weight = exp(-0.3 * distance_from_end)
            weights = np.exp(-0.3 * np.arange(n-1, -1, -1))
            
            # Calculate weighted counts for each class
            weighted_counts = {0: 0.0, 1: 0.0, 4: 0.0}  # forest, non-forest, water
            
            for i, val in enumerate(values):
                if val in weighted_counts:
                    weighted_counts[val] += weights[i]
            
            # Find the class with maximum weighted count
            if sum(weighted_counts.values()) == 0:
                return 255  # No valid data
            
            max_weighted_class = max(weighted_counts, key=weighted_counts.get)
            
            # Convert to forest flag (1=forest, 0=non-forest)
            return 1 if max_weighted_class == 0 else 0
        
        # Apply the weighted temporal logic to each pixel
        forest_flag = xr.apply_ufunc(
            weighted_classification,
            masked,
            input_core_dims=[['time']],
            output_core_dims=[[]],
            vectorize=True,
            dask='parallelized',
            output_dtypes=[np.uint8]
        )
        
        # Apply minimum valid observations requirement (2 observations adequate for exponential weighting)
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
            
            # Always upload merged COG to S3 for STAC collection creation
            merged_s3_key = f"datasets/cfw-{self.run_id}/{self.year}/{self.run_id}_{self.year}_merged_composite.tif"
            logger.info(f"⬆️  Uploading merged COG to S3: {merged_s3_key}")
            upload_file(merged_path, merged_s3_key)
            
            if use_local_files:
                # For local workflow, keep local file and return local path
                logger.info(f"🎉 Merge completed successfully, saved locally to: {merged_path}")
                logger.info(f"🎉 Also uploaded to S3 for STAC collection: {merged_s3_key}")
                return str(merged_path)
            else:
                # For S3 workflow, return S3 key  
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
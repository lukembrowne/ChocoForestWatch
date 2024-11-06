import rasterio
import geopandas as gpd
from rasterio.mask import mask
import numpy as np
from datetime import datetime, timedelta

def clip_and_process_alerts(raster_path, shapefile_path, output_path):
    """
    Clip raster to shapefile bounds and process alerts within the clipped area.
    
    Args:
        raster_path (str): Path to input raster file
        shapefile_path (str): Path to shapefile for clipping
        output_path (str): Path where processed raster will be saved
    """
    # Read the shapefile
    gdf = gpd.read_file(shapefile_path)
    
    # Ensure the shapefile is in the same CRS as the raster
    with rasterio.open(raster_path) as src:
        # Reproject shapefile if necessary
        if gdf.crs != src.crs:
            gdf = gdf.to_crs(src.crs)
        
        # Get the geometry for clipping
        shapes = gdf.geometry.values
        
        # Clip the raster
        clipped_data, clipped_transform = mask(src, shapes, crop=True)
        clipped_data = clipped_data[0]  # Get first band
        
        # Copy the metadata
        profile = src.profile.copy()
        
        # Update metadata for clipped raster
        profile.update({
            'height': clipped_data.shape[0],
            'width': clipped_data.shape[1],
            'transform': clipped_transform
        })
        
        # Calculate days since Dec 31, 2014 for our date range
        base_date = datetime(2014, 12, 31)
        start_date = datetime(2023, 3, 1)
        end_date = datetime(2024, 3, 1)
        
        days_start = (start_date - base_date).days  # Should be 3012
        days_end = (end_date - base_date).days      # Should be 3377
        
        # Extract confidence level (first digit)
        confidence_level = clipped_data // 10000
        
        # Extract days (remainder after removing confidence level)
        days = clipped_data - (confidence_level * 10000)
        
        # Create confidence level mask (2, 3, or 4)
        confidence_mask = (confidence_level >= 2) & (confidence_level <= 4)
        
        # Create date range mask
        date_mask = (days >= days_start) & (days <= days_end)
        
        # Combine masks
        final_mask = confidence_mask & date_mask
        
        # Apply mask to data
        filtered_data = np.where(final_mask, clipped_data, 0)
        
        # Write the output raster
        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(filtered_data.astype(profile['dtype']), 1)

if __name__ == "__main__":
    # Set up file paths
    raster_path = "./gfw_alerts/10N_080W_20241105.tif"  # Update with your raster filename
    shapefile_path = "./data/Bilsa AOI.shp"
    output_path = "./gfw_alerts/filtered_alerts.tif"
    
    try:
        clip_and_process_alerts(raster_path, shapefile_path, output_path)
        print("Processing completed successfully!")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
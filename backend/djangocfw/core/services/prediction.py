import rasterio
import numpy as np
from rasterio.mask import mask
from shapely.geometry import shape, mapping
import os
import uuid
from django.utils import timezone
from loguru import logger
from ..models import Prediction, TrainedModel, Project
import joblib
from rasterio.merge import merge
import tempfile
from django.conf import settings
import requests
from requests.auth import HTTPBasicAuth
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .model_training import ModelTrainingService

class PredictionService:
    def __init__(self, model_id, project_id):
        self.model_id = model_id
        self.project_id = project_id
        self.PLANET_API_KEY = settings.PLANET_API_KEY
        self.QUAD_DOWNLOAD_DIR = './data/planet_quads'
        self.channel_layer = get_channel_layer()
        
    def load_model(self):
        """Load the trained model and its metadata"""
        model_record = TrainedModel.objects.get(id=self.model_id)
        model = joblib.load(model_record.file_path)
        model.date_encoder = model_record.date_encoder
        model.month_encoder = model_record.month_encoder
        model.label_encoder = model_record.label_encoder
        return model, model_record

    def predict_landcover_aoi(self, model, model_record, quads, aoi_shape, basemap_date):
        """Generate prediction for the AOI"""
        predicted_rasters = []
        temp_files = []
        
        # Get encoders
        date_encoder = model_record.date_encoder
        month_encoder = model_record.month_encoder
        
        # Encode date and month
        year, month = basemap_date.split('-')
        encoded_date = date_encoder.transform([year])[0]
        encoded_month = month_encoder.transform([int(month)])[0]
        
        for quad in quads:
            with rasterio.open(quad['filename']) as src:
                # Read data
                data = src.read([1, 2, 3, 4])
                meta = src.meta.copy()
                meta.update(count=1)
                
                # Reshape for prediction
                reshaped_data = data.reshape(4, -1).T
                
                # Add date and month features
                date_column = np.full((reshaped_data.shape[0], 1), encoded_date)
                month_column = np.full((reshaped_data.shape[0], 1), encoded_month)
                prediction_data = np.hstack((reshaped_data, date_column, month_column))
                
                # Make prediction
                predictions = model.predict(prediction_data)
                prediction_map = predictions.reshape(data.shape[1], data.shape[2])
                
                # Save to temporary file
                temp_filename = f'temp_prediction_{uuid.uuid4().hex}.tif'
                with rasterio.open(temp_filename, 'w', **meta) as tmp:
                    tmp.write(prediction_map.astype(rasterio.uint8), 1)
                
                predicted_rasters.append(rasterio.open(temp_filename))
                temp_files.append(temp_filename)
        
        # Merge predictions
        mosaic, out_transform = merge(predicted_rasters)
        
        # Apply sieve filter if specified
        sieve_size = model_record.model_parameters.get('sieve_size', 0)
        if sieve_size > 0:
            from rasterio.features import sieve
            sieved_mosaic = sieve(mosaic[0], size=sieve_size)
            mosaic = np.expand_dims(sieved_mosaic, 0)
        
        # Create output file
        output_dir = './predictions'
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"landcover_prediction_{uuid.uuid4().hex}.tif")
        
        # Write final prediction
        merged_meta = predicted_rasters[0].meta.copy()
        merged_meta.update({
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": out_transform,
            "compress": 'lzw',
            "nodata": 255
        })
        
        # Clip to AOI
        with rasterio.open(output_file, 'w', **merged_meta) as dest:
            clipped_data, clipped_transform = mask(
                mosaic, 
                shapes=[aoi_shape], 
                crop=True,
                nodata=255
            )
            dest.write(clipped_data)
        
        # Cleanup
        for raster in predicted_rasters:
            raster.close()
        for temp_file in temp_files:
            os.remove(temp_file)
        
        return output_file

    def calculate_summary_statistics(self, prediction):
        """Calculate and save summary statistics"""
        try:
            with rasterio.open(prediction.file_path) as src:
                raster_data = src.read(1)
                pixel_area_ha = abs(src.transform[0] * src.transform[4]) / 10000
                
                # Get unique values and counts
                unique, counts = np.unique(raster_data, return_counts=True)
                
                # Calculate total area excluding nodata
                valid_pixels = raster_data[raster_data != 255]
                total_area = float(valid_pixels.size * pixel_area_ha)
                
                # Get class names
                model_record = TrainedModel.objects.get(id=prediction.model_id)
                class_names = {i: name for i, name in enumerate(model_record.all_class_names)}
                
                # Calculate statistics
                class_stats = {}
                for value, count in zip(unique, counts):
                    if value in class_names:
                        area = count * pixel_area_ha
                        percentage = (area / total_area) * 100
                        class_stats[int(value)] = {
                            'area_ha': float(area),
                            'percentage': float(percentage)
                        }
                
                # Save statistics
                prediction.summary_statistics = {
                    'prediction_name': prediction.name,
                    'prediction_date': prediction.basemap_date,
                    'type': prediction.type,
                    'total_area_ha': total_area,
                    'class_statistics': class_stats
                }
                prediction.save()
                
        except Exception as e:
            logger.error(f"Error calculating summary statistics: {str(e)}")
            raise

    def get_planet_quads(self, aoi_shape, basemap_date):
        """Get Planet quads for the AOI"""
        year, month = basemap_date.split('-')
        mosaic_name = f"planet_medres_normalized_analytic_{year}-{month}_mosaic"
        
        # Get mosaic ID
        mosaic_id = self.get_mosaic_id(mosaic_name)
        
        # Get bounds from AOI shape
        bounds = shape(aoi_shape).bounds
        
        # Get quad info
        quads = self.get_quad_info(mosaic_id, bounds)
        
        # Download and process quads
        processed_quads = self.download_and_process_quads(quads, year, month)
        
        return processed_quads

    # Add the same Planet API methods as in ModelTrainingService
    get_mosaic_id = ModelTrainingService.get_mosaic_id
    get_quad_info = ModelTrainingService.get_quad_info
    download_and_process_quads = ModelTrainingService.download_and_process_quads

    def send_progress_update(self, progress, message):
        """Send progress update through WebSocket"""
        async_to_sync(self.channel_layer.group_send)(
            f"project_{self.project_id}",
            {
                'type': 'prediction_update',
                'progress': progress,
                'message': message
            }
        )

    def generate_prediction(self, aoi_shape, basemap_date, prediction_name):
        """Generate a new prediction"""
        try:
            self.send_progress_update(0, "Starting prediction...")
            
            # Load model and get quads
            self.send_progress_update(10, "Loading model...")
            model = self.load_model()
            
            self.send_progress_update(20, "Getting Planet quads...")
            quads = self.get_planet_quads(aoi_shape, basemap_date)
            
            # Generate prediction
            self.send_progress_update(50, "Generating prediction...")
            prediction_file = self.predict_landcover_aoi(
                model, quads, aoi_shape, basemap_date
            )
            
            # Save prediction record
            self.send_progress_update(90, "Saving prediction...")
            prediction = self.save_prediction(
                prediction_file, prediction_name, basemap_date
            )
            
            # Calculate statistics
            self.send_progress_update(95, "Calculating statistics...")
            self.calculate_summary_statistics(prediction)
            
            self.send_progress_update(100, "Prediction complete")
            return prediction
            
        except Exception as e:
            self.send_progress_update(100, f"Error: {str(e)}")
            logger.error(f"Error in prediction generation: {str(e)}")
            raise

    def save_prediction(self, prediction_data, name, basemap_date):
        """Save prediction to storage and create record"""
        from django.core.files.base import ContentFile
        
        prediction = Prediction.objects.create(
            project_id=self.project_id,
            model_id=self.model_id,
            type='land_cover',
            name=name,
            basemap_date=basemap_date
        )
        
        # Save the prediction file
        prediction.file.save(
            f"prediction_{uuid.uuid4().hex}.tif",
            ContentFile(prediction_data)
        )
        
        return prediction
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
from .planet_utils import PlanetUtils
from ..exceptions import PredictionError
import pickle
import base64
from ..storage import PlanetQuadStorage
from django.core.files.base import ContentFile
from rasterio.features import sieve


class PredictionService:
    def __init__(self, model_id, project_id):
        self.model_id = model_id
        self.project_id = project_id
        self.PLANET_API_KEY = settings.PLANET_API_KEY
        self.QUAD_DOWNLOAD_DIR = './data/planet_quads'
        self.channel_layer = get_channel_layer()
        
    def load_model(self):
        """Load the trained model and its metadata"""
        try:
            model_record = TrainedModel.objects.get(id=self.model_id)
            model = joblib.load(model_record.model_file)
            
            # Deserialize the encoders from the JSON field
            encoders = {
                name: pickle.loads(base64.b64decode(encoder_str.encode('utf-8')))
                for name, encoder_str in model_record.encoders.items()
            }
            
            # Assign encoders to model
            model.date_encoder = encoders['date_encoder']
            model.month_encoder = encoders['month_encoder']
            model.label_encoder = encoders['label_encoder']
            
            return model, model_record
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise PredictionError(detail=f"Failed to load model: {str(e)}")

    def predict_landcover_aoi(self, model, model_record, quads, aoi_shape, basemap_date):
        """Generate prediction for the AOI"""
        predicted_rasters = []
        temp_files = []
        
        try:
            # Get encoders from the model object
            date_encoder = model.date_encoder
            month_encoder = model.month_encoder
            
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
                    
                    # Make prediction with consecutive integers
                    predictions = model.predict(prediction_data)
                    
                    # Map predictions back to global indices
                    global_predictions = np.array([model.consecutive_to_global[pred] for pred in predictions])
                    prediction_map = global_predictions.reshape(data.shape[1], data.shape[2])
                    
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
                logger.info(f"Applying sieve filter with size {sieve_size}")
                sieved_mosaic = sieve(mosaic[0], size=sieve_size)
                mosaic = np.expand_dims(sieved_mosaic, 0)
            
            # Create output file 
            output_dir = './predictions'
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"landcover_prediction_{uuid.uuid4().hex}.tif")
            
            # Write final prediction with proper metadata
            merged_meta = predicted_rasters[0].meta.copy()
            merged_meta.update({
                "height": mosaic.shape[1],
                "width": mosaic.shape[2],
                "transform": out_transform,
                "compress": 'lzw',
                "nodata": 255
            })
            
            # Create a temporary raster with the merged data
            temp_merged = f'temp_merged_{uuid.uuid4().hex}.tif'
            with rasterio.open(temp_merged, 'w', **merged_meta) as tmp:
                tmp.write(mosaic)
            
            # Now clip to AOI using the temporary merged file
            with rasterio.open(temp_merged) as src:
                # Convert GeoJSON to list of geometries for mask
                geom = [shape(aoi_shape)]
                
                # Perform the clipping
                clipped_data, clipped_transform = mask(
                    src,
                    geom,
                    crop=True,
                    nodata=255
                )
                
                # Update metadata for clipped output
                out_meta = src.meta.copy()
                out_meta.update({
                    "height": clipped_data.shape[1],
                    "width": clipped_data.shape[2],
                    "transform": clipped_transform
                })
                
                # Write final clipped output
                with rasterio.open(output_file, 'w', **out_meta) as dest:
                    dest.write(clipped_data)
            
            # Cleanup
            for raster in predicted_rasters:
                raster.close()
            for temp_file in temp_files:
                os.remove(temp_file)
            os.remove(temp_merged)
            
            return output_file
            
        except Exception as e:
            logger.error(f"Error in predict_landcover_aoi: {str(e)}")
            # Clean up temp files if there's an error
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            for raster in predicted_rasters:
                if not raster.closed:
                    raster.close()
            raise PredictionError(f"Failed to generate prediction: {str(e)}")

    def calculate_summary_statistics(self, prediction):
        """Calculate and save summary statistics"""
        try:
            with rasterio.open(prediction.file.path) as src:
                raster_data = src.read(1)
                pixel_area_ha = abs(src.transform[0] * src.transform[4]) / 10000
                
                # Get unique values and counts
                unique, counts = np.unique(raster_data, return_counts=True)
                
                # Calculate total area excluding nodata
                valid_pixels = raster_data[raster_data != 255]
                total_area = float(valid_pixels.size * pixel_area_ha)
                
                # Get class names from the model's encoders
                model_record = TrainedModel.objects.get(id=prediction.model_id)
                
                # Deserialize the label encoder from the encoders field
                label_encoder = pickle.loads(
                    base64.b64decode(model_record.encoders['label_encoder'].encode('utf-8'))
                )
                class_names = {i: name for i, name in enumerate(label_encoder.classes_)}
                
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
        mosaic_id = PlanetUtils.get_mosaic_id(mosaic_name)
        
        # Convert GeoJSON to shapely shape and get bounds
        geom = shape(aoi_shape)
        bounds = geom.bounds
        
        # Get quad info
        quads = PlanetUtils.get_quad_info(mosaic_id, bounds)
        
        # Download and process quads
        processed_quads = PlanetUtils.download_and_process_quads(
            quads, 
            year, 
            month, 
            PlanetQuadStorage()
        )
        
        return processed_quads

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
        """Generate a new prediction or update existing one"""
        try:
            self.send_progress_update(0, "Starting prediction...")
            
            # Check for existing prediction for this date
            try:
                existing_prediction = Prediction.objects.get(
                    project_id=self.project_id,
                    model_id=self.model_id,
                    basemap_date=basemap_date,
                    type='land_cover'
                )
                self.send_progress_update(5, "Found existing prediction, will update...")
            except Prediction.DoesNotExist:
                existing_prediction = None
            
            # Load model and get quads
            self.send_progress_update(10, "Loading model...")
            model, model_record = self.load_model()
            
            self.send_progress_update(20, "Getting Planet quads...")
            quads = self.get_planet_quads(aoi_shape, basemap_date)
            
            # Generate prediction
            self.send_progress_update(50, "Generating prediction...")
            prediction_file = self.predict_landcover_aoi(
                model, 
                model_record, 
                quads, 
                aoi_shape,
                basemap_date
            )
            
            # Save or update prediction record
            self.send_progress_update(90, "Saving prediction...")
            prediction = self.save_prediction(
                prediction_file, 
                prediction_name, 
                basemap_date,
                existing_prediction
            )
            
            # Calculate statistics
            self.send_progress_update(95, "Calculating statistics...")
            self.calculate_summary_statistics(prediction)
            
            self.send_progress_update(100, "Prediction complete")
            return prediction
            
        except Exception as e:
            logger.error("Error generating prediction")
            logger.exception(e)
            raise PredictionError(detail=str(e))

    def save_prediction(self, prediction_file, name, basemap_date, existing_prediction=None):
        """Save prediction to storage and create/update record"""
        try:
            # Open the prediction file
            with open(prediction_file, 'rb') as f:
                file_content = f.read()

            if existing_prediction:
                # Delete old file if it exists
                if existing_prediction.file:
                    # Get the storage instance
                    storage = existing_prediction.file.storage
                    # Delete the old file
                    if storage.exists(existing_prediction.file.name):
                        storage.delete(existing_prediction.file.name)
                
                # Update existing record
                prediction = existing_prediction
                prediction.name = name
                prediction.type = 'land_cover'  # Ensure type is set
                
                # Save new file
                prediction.file.save(
                    f"landcover_{uuid.uuid4().hex}.tif",
                    ContentFile(file_content),
                    save=False  # Don't save the model yet
                )
                
                # Save all changes
                prediction.save()
                
            else:
                # Create new record
                prediction = Prediction.objects.create(
                    project_id=self.project_id,
                    model_id=self.model_id,
                    type='land_cover',
                    name=name,
                    basemap_date=basemap_date
                )
                
                # Save the prediction file
                prediction.file.save(
                    f"landcover_{uuid.uuid4().hex}.tif",
                    ContentFile(file_content)
                )
            
            # Delete the temporary file
            os.remove(prediction_file)
            
            return prediction
            
        except Exception as e:
            logger.error(f"Error saving prediction: {str(e)}")
            if os.path.exists(prediction_file):
                os.remove(prediction_file)
            raise PredictionError(f"Failed to save prediction: {str(e)}")
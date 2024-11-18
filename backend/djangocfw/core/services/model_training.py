import rasterio
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
from rasterio.mask import mask
from shapely.geometry import shape
import joblib
import os
import uuid
from django.utils import timezone
from loguru import logger
import math
from ..models import TrainedModel, TrainingPolygonSet, Project, ModelTrainingTask
from django.conf import settings
import requests
from requests.auth import HTTPBasicAuth
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.core.files.base import ContentFile
import io
from ..exceptions import ModelTrainingError, PlanetAPIError, InvalidInputError
from pyproj import Transformer
import pickle
import base64
from pathlib import Path
from ..storage import ModelStorage, PlanetQuadStorage

class ModelTrainingService:
    def __init__(self, project_id):
        self.project_id = project_id
        self.PLANET_API_KEY = settings.PLANET_API_KEY
        self.QUAD_DOWNLOAD_DIR = './data/planet_quads'
        self.task_id = str(uuid.uuid4())
        
    def update_progress(self, progress, message, status='running', error=''):
        """Update training progress in database"""
        ModelTrainingTask.objects.update_or_create(
            task_id=self.task_id,
            defaults={
                'progress': progress,
                'message': message,
                'status': status,
                'error': error
            }
        )

    def train_model(self, model_name, model_description, training_set_ids, model_params):
        """Main method to handle the model training process"""
        try:
            self.update_progress(0, "Starting model training...")
            
            # Get training data
            self.update_progress(10, "Preparing training data...")
            X, y, feature_ids, dates, all_class_names = self.prepare_training_data(training_set_ids)
            
            # Train model and get metrics
            self.update_progress(50, "Training model...")
            model, metrics, encoders = self.train_xgboost_model(
                X, y, feature_ids, dates, all_class_names, model_params
            )
            
            # Save the model
            self.update_progress(90, "Saving model...")
            saved_model = self.save_model(
                model, model_name, model_description, metrics, 
                model_params, encoders, training_set_ids, len(X)
            )
            
            self.update_progress(100, "Model training complete", status='completed')
            return saved_model, metrics, self.task_id
            
        except Exception as e:
            logger.exception("Error in model training")
            self.update_progress(
                progress=0,
                message="Training failed",
                status='failed',
                error=str(e)
            )
            raise ModelTrainingError(detail=str(e))

    def prepare_training_data(self, training_set_ids):
        """Prepare training data from training sets"""
        all_X = []
        all_y = []
        all_feature_ids = []
        all_dates = []
        
        # Get training sets
        training_sets = TrainingPolygonSet.objects.filter(
            id__in=training_set_ids,
            excluded=False
        )
        
        for training_set in training_sets:
            X, y, feature_ids = self.extract_pixels_from_polygons(
                training_set.polygons['features'],
                training_set.basemap_date
            )
            all_X.append(X)
            all_y.extend(y)
            all_feature_ids.extend(feature_ids)
            all_dates.extend([training_set.basemap_date] * len(y))
        
        return (
            np.vstack(all_X),
            np.array(all_y),
            np.array(all_feature_ids),
            np.array(all_dates),
            self.get_all_class_names()
        )

    def extract_pixels_from_polygons(self, polygons, basemap_date):
        """Extract pixel values from Planet quads for training polygons"""
        all_pixels = []
        all_labels = []
        all_feature_ids = []

        # Get quads for this date
        quads = self.get_planet_quads(basemap_date)
        
        for quad in quads:
            with rasterio.open(quad['filename']) as src:
                for feature in polygons:
                    geom = shape(feature['geometry'])
                    class_label = feature['properties']['classLabel']
                    feature_id = feature['id']

                    try:
                        out_image, out_transform = mask(src, [geom], crop=True, all_touched=True, indexes=[1, 2, 3, 4])
                        
                        if src.nodata is not None:
                            out_image = np.ma.masked_equal(out_image, src.nodata)
                        
                        pixels = out_image.reshape(4, -1).T
                        
                        if isinstance(pixels, np.ma.MaskedArray):
                            valid_pixels = pixels[~np.all(pixels.mask, axis=1)]
                        else:
                            valid_pixels = pixels[~np.all(pixels == src.nodata, axis=1)] if src.nodata is not None else pixels
                        
                        if valid_pixels.size > 0:
                            all_pixels.extend(valid_pixels.data if isinstance(valid_pixels, np.ma.MaskedArray) else valid_pixels)
                            all_labels.extend([class_label] * valid_pixels.shape[0])
                            all_feature_ids.extend([feature_id] * valid_pixels.shape[0])

                    except Exception as e:
                        logger.warning(f"Error processing polygon in quad: {str(e)}")

        if not all_pixels:
            raise ValueError("No valid pixels extracted from quads")
        
        X = np.array(all_pixels, dtype=float)
        y = np.array(all_labels)
        feature_ids = np.array(all_feature_ids)
        
        return X, y, feature_ids

    def train_xgboost_model(self, X, y, feature_ids, dates, all_class_names, model_params):
        """Train XGBoost model and calculate metrics"""
        # Create label encoder for classes
        le = LabelEncoder()
        y_encoded = le.fit_transform(y)
        
        # Create date and month encoders
        date_encoder = LabelEncoder()
        encoded_dates = date_encoder.fit_transform([d.split('-')[0] for d in dates])
        
        month_encoder = LabelEncoder()
        encoded_months = month_encoder.fit_transform([int(d.split('-')[1]) for d in dates])
        
        # Add encoded dates and months as features
        X = np.column_stack((X, encoded_dates, encoded_months))
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)
        
        # Train model
        model = XGBClassifier(**model_params)
        model.fit(X_train, y_train)
        
        # Get predictions and metrics
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average=None)
        conf_matrix = confusion_matrix(y_test, y_pred)
        
        # Prepare metrics
        metrics = {
            "accuracy": float(accuracy),
            "class_metrics": {
                class_name: {
                    'precision': float(precision[i]),
                    'recall': float(recall[i]),
                    'f1': float(f1[i])
                } for i, class_name in enumerate(le.classes_)
            },
            "confusion_matrix": conf_matrix.tolist(),
            "class_names": le.classes_.tolist()
        }
        
        encoders = {
            'date_encoder': date_encoder,
            'month_encoder': month_encoder,
            'label_encoder': le
        }
        
        return model, metrics, encoders

    def save_model(self, model, model_name, model_description, metrics, model_params, encoders, training_set_ids, num_samples):
        """Save or update the trained model and its metadata"""
        try:
            # Serialize the encoders
            serialized_encoders = {
                name: base64.b64encode(pickle.dumps(encoder)).decode('utf-8')
                for name, encoder in encoders.items()
            }

            # Get the project instance
            project = Project.objects.get(id=self.project_id)

            # Check for existing model for this project
            try:
                model_record = TrainedModel.objects.get(project=project)
                logger.info(f"Updating existing model for project {self.project_id}")
                
                # Update existing model record
                model_record.name = model_name
                model_record.description = model_description
                model_record.training_set_ids = training_set_ids
                model_record.training_periods = len(training_set_ids)
                model_record.num_training_samples = num_samples
                model_record.model_parameters = model_params
                model_record.metrics = metrics
                model_record.encoders = serialized_encoders
                
            except TrainedModel.DoesNotExist:
                logger.info(f"Creating new model for project {self.project_id}")
                # Create new model record
                model_record = TrainedModel.objects.create(
                    name=model_name,
                    description=model_description,
                    project=project,
                    training_set_ids=training_set_ids,
                    training_periods=len(training_set_ids),
                    num_training_samples=num_samples,
                    model_parameters=model_params,
                    metrics=metrics,
                    encoders=serialized_encoders
                )

            # Use ModelStorage to save the file
            storage = ModelStorage()
            
            # Serialize model to bytes
            model_bytes = pickle.dumps(model)
            
            # If updating, delete old model file if it exists
            if model_record.model_file and storage.exists(model_record.model_file):
                storage.delete(model_record.model_file)
            
            # Save new model file with timestamp
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{model_record.id}_model_{timestamp}.pkl"
            model_file = ContentFile(model_bytes)
            saved_path = storage.save(filename, model_file)
            
            # Update model record with the new path
            model_record.model_file = saved_path
            model_record.save()

            return model_record

        except Exception as e:
            logger.exception("Error saving model")
            raise ModelTrainingError(f"Failed to save model: {str(e)}")

    def load_model(self, model_record):
        """Load a trained model and its encoders"""
        try:
            # Load the model file using storage
            storage = ModelStorage()
            with storage.open(model_record.model_file, 'rb') as f:
                model = pickle.load(f)

            # Deserialize the encoders
            encoders = {
                name: pickle.loads(base64.b64decode(encoder_str.encode('utf-8')))
                for name, encoder_str in model_record.encoders.items()
            }

            return model, encoders

        except Exception as e:
            logger.exception("Error loading model")
            raise ModelTrainingError(f"Failed to load model: {str(e)}")

    def get_all_class_names(self):
        """Get all class names from project"""
        project = Project.objects.get(id=self.project_id)
        return [cls['name'] for cls in project.classes] 

    def get_planet_quads(self, basemap_date):
        """Get Planet quads for a given date"""
        year, month = basemap_date.split('-')
        mosaic_name = f"planet_medres_normalized_analytic_{year}-{month}_mosaic"
        
        # Get project AOI
        project = Project.objects.get(id=self.project_id)
        aoi_bounds = project.aoi.extent  # Get bounds of AOI
        
        # Find mosaic ID
        mosaic_id = self.get_mosaic_id(mosaic_name)
        
        # Get quad info
        quads = self.get_quad_info(mosaic_id, aoi_bounds)
        
        # Download and process quads
        processed_quads = self.download_and_process_quads(quads, year, month)
        
        return processed_quads

    def get_mosaic_id(self, mosaic_name):
        """Get mosaic ID from Planet API"""
        try:
            url = "https://api.planet.com/basemaps/v1/mosaics"
            params = {"name__is": mosaic_name}
            response = requests.get(
                url, 
                auth=HTTPBasicAuth(self.PLANET_API_KEY, ''), 
                params=params
            )
            
            # Check if API key is valid
            if response.status_code == 401:
                raise PlanetAPIError("Invalid Planet API key. Please check your configuration.")
            
            response.raise_for_status()
            mosaics = response.json().get('mosaics', [])
            
            if not mosaics:
                raise PlanetAPIError(f"No mosaic found with name: {mosaic_name}")
            
            return mosaics[0]['id']
            
        except requests.exceptions.RequestException as e:
            raise PlanetAPIError(f"Error accessing Planet API: {str(e)}")

    def get_quad_info(self, mosaic_id, bbox):
        """Get quad information for a given mosaic and bounding box"""
        # Create transformer from Web Mercator to WGS84
        transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326")
        
        # Extract coordinates
        minx, miny, maxx, maxy = bbox
        
        # Transform coordinates
        # Note: transform() returns (lat, lon) so we need to swap them for (lon, lat)
        lat_min, lon_min = transformer.transform(minx, miny)
        lat_max, lon_max = transformer.transform(maxx, maxy)
        
        # Create bbox string in lon,lat format (WGS84)
        # Planet API expects: west,south,east,north
        bbox_comma = f"{lon_min},{lat_min},{lon_max},{lat_max}"

        url = f"https://api.planet.com/basemaps/v1/mosaics/{mosaic_id}/quads"
        params = {
            "bbox": bbox_comma,
            "minimal": "true"
        }

        response = requests.get(
            url, 
            auth=HTTPBasicAuth(self.PLANET_API_KEY, ''), 
            params=params
        )
        response.raise_for_status()
        return response.json().get('items', [])

    def download_and_process_quads(self, quads, year, month):
        """Download and process Planet quads"""
        storage = PlanetQuadStorage()
        processed_quads = []

        for quad in quads:
            quad_id = quad['id']
            download_url = quad['_links']['download']
            
            # Get year/month specific path from storage
            relative_path = storage.get_year_month_path(year, month)
            filename = f"{quad_id}_{year}_{month}.tif"
            full_path = os.path.join(relative_path, filename)
            
            # Check if file already exists
            if storage.exists(full_path):
                logger.info(f"Quad {quad_id} already exists at {full_path}, skipping download")
                local_filename = storage.path(full_path)
            else:
                logger.info(f"Downloading quad {quad_id} for {year}-{month}")
                try:
                    # Download the quad
                    response = requests.get(
                        download_url, 
                        auth=HTTPBasicAuth(self.PLANET_API_KEY, ''), 
                        stream=True
                    )
                    response.raise_for_status()
                    
                    # Save using storage
                    quad_file = ContentFile(response.content)
                    saved_path = storage.save(full_path, quad_file)
                    local_filename = storage.path(saved_path)
                    
                    logger.success(f"Successfully downloaded quad {quad_id} to {local_filename}")
                    
                except Exception as e:
                    logger.error(f"Failed to download quad {quad_id}: {str(e)}")
                    continue
            
            processed_quads.append({
                'id': quad_id,
                'filename': local_filename,
                'bbox': quad['bbox']
            })
        
        return processed_quads
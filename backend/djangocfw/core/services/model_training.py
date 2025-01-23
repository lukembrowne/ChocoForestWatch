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
from uuid import uuid4
import asyncio
import threading# 
from .planet_utils import PlanetUtils
from .prediction import PredictionService
import concurrent.futures
from functools import partial

class ModelTrainingService:
    def __init__(self, project_id):
        self.project_id = project_id
        self.PLANET_API_KEY = settings.PLANET_API_KEY
        self.QUAD_DOWNLOAD_DIR = './data/planet_quads'
        self.task_id = None
        self._cancel_flag = False  # Add cancellation flag
        
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

    def create_training_task(self):
        """Create a new training task and return its ID"""
        self.task_id = uuid4()
        ModelTrainingTask.objects.create(
            task_id=self.task_id,
            status='pending',
            progress=0,
            message='Initializing training...'
        )
        return self.task_id

    def start_training_async(self, model_name, model_description, training_set_ids, model_params):
        """Start the training process in a separate thread"""
        def train_thread():
            try:
                self.train_model(model_name, model_description, training_set_ids, model_params)
            except Exception as e:
                logger.exception("Error in training thread")
                self.update_progress(
                    progress=0,
                    message="Training failed",
                    status='failed',
                    error=str(e)
                )

        thread = threading.Thread(
            target=train_thread,
            daemon=True
        )
        thread.start()

    def cancel_training(self):
        """Set the cancel flag to stop training"""
        self._cancel_flag = True

    def train_model(self, model_name, model_description, training_set_ids, model_params):
        """Train the model and generate predictions"""
        try:
            # Check cancellation at major steps
            if self._cancel_flag:
                self.update_progress(0, "Training cancelled", status='cancelled')
                return None, None

            self.update_progress(0, "Starting model training...")
            
            # Get training data
            self.update_progress(10, "Preparing training data...")
            X, y, feature_ids, dates, all_class_names = self.prepare_training_data(training_set_ids)
            
            if self._cancel_flag:
                self.update_progress(0, "Training cancelled", status='cancelled')
                return None, None

            # Train model and get metrics
            self.update_progress(50, "Training model...")
            model, metrics, encoders, all_class_names = self.train_xgboost_model(
                X, y, feature_ids, dates, model_params
            )
            
            if self._cancel_flag:
                self.update_progress(0, "Training cancelled", status='cancelled')
                return None, None

            # Save the model
            self.update_progress(90, "Saving model...")
            saved_model = self.save_model(
                model, model_name, model_description, metrics, 
                model_params, encoders, training_set_ids, len(X), all_class_names
            )
            
            self.update_progress(80, "Model training complete")
            
            # Generate predictions for all dates
            if self._cancel_flag:
                self.update_progress(0, "Training cancelled", status='cancelled')
                return None, None

            # Get dates from training_set_ids
            training_sets = TrainingPolygonSet.objects.filter(
                id__in=training_set_ids
            )
            basemap_dates = [set.basemap_date for set in training_sets]
            
            self.generate_predictions_after_training(saved_model.id, basemap_dates)
            
            self.update_progress(95, "Predictions complete")
            
            # Calculate and save final metrics
            self.update_progress(100, "Training and predictions complete")
            
            return saved_model, metrics
            
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

    def train_xgboost_model(self, X, y, feature_ids, dates, model_params):
        # Extract splitting params and remove them from model_params
        # split_params = {
        #     'split_method': model_params.pop('split_method', 'feature'),
        #     'train_test_split': model_params.pop('train_test_split', 0.2)
        # }

        split_params = {
            'split_method': model_params['split_method'],
            'train_test_split': model_params['train_test_split']
        }
        
        # Get project and classes
        project = Project.objects.get(id=self.project_id)
        all_class_names = [cls['name'] for cls in project.classes]

        # Define the desired class order with fixed indices
        desired_class_order = ['Forest', 'Non-Forest', 'Cloud', 'Shadow', 'Water']
        global_class_to_int = {class_name: idx for idx, class_name in enumerate(desired_class_order)}
        
        # Get classes actually present in training data
        classes_in_training = np.unique(y).tolist()
        
        # Create mapping for XGBoost that uses consecutive integers
        present_classes = [c for c in desired_class_order if c in classes_in_training]
        training_class_to_int = {class_name: idx for idx, class_name in enumerate(present_classes)}
        
        # Create reverse mapping from consecutive to global indices
        consecutive_to_global = {
            training_class_to_int[class_name]: global_class_to_int[class_name]
            for class_name in present_classes
        }
        
        # Transform labels using consecutive integers for training
        y_encoded = np.array([training_class_to_int[label] for label in y])

        # Create a custom LabelEncoder that remembers the mapping
        le = LabelEncoder()
        le.classes_ = np.array(all_class_names)
        
        ## Get classes actually present in training data
        ## classes_in_training = le.classes_.tolist()

        # Create date and month encoders
        date_encoder = LabelEncoder()
        encoded_dates = date_encoder.fit_transform([d.split('-')[0] for d in dates])
        
        month_encoder = LabelEncoder()
        encoded_months = month_encoder.fit_transform([int(d.split('-')[1]) for d in dates])
        
        # Add encoded dates and months as features
        X = np.column_stack((X, encoded_dates, encoded_months))
        
        # Split data based on method
        if split_params['split_method'] == 'feature':
            unique_features, unique_indices = np.unique(feature_ids, return_index=True)
            unique_classes = y[unique_indices]
            
            train_features, test_features = train_test_split(
                unique_features, 
                test_size=split_params['train_test_split'], 
                random_state=42, 
                stratify=unique_classes
            )
            
            train_mask = np.isin(feature_ids, train_features)
            test_mask = np.isin(feature_ids, test_features)
            
            X_train, X_test = X[train_mask], X[test_mask]
            y_train, y_test = y_encoded[train_mask], y_encoded[test_mask]
        else:
            # Pixel-based split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y_encoded, 
                test_size=split_params['train_test_split'], 
                random_state=42
            )
        
        # Only add num_class for multi-class problems (>2 classes)
        if len(classes_in_training) > 2:
            model_params['num_class'] = len(classes_in_training)
            # For multi-class, we need to set objective
            model_params['objective'] = 'multi:softmax'
        else:
            # For binary classification, remove num_class if present ##
            model_params.pop('num_class', None)
            # For binary classification, we can use binary:logistic
            model_params['objective'] = 'binary:logistic'


        # Add random seed and early stopping
        model_params['random_state'] = 42
        model_params['early_stopping_rounds'] = 10
        
        # Now create and train the model
        model = XGBClassifier(**model_params)
        model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=True)
        
        # Get predictions and metrics
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average=None)
        
        # Create confusion matrix for training classes
        conf_matrix_training = confusion_matrix(y_test, y_pred)
        
        # Create full-size confusion matrix including all possible classes
        full_conf_matrix = np.zeros((len(all_class_names), len(all_class_names)), dtype=int)
        for i, class_name in enumerate(classes_in_training):
            for j, other_class in enumerate(classes_in_training):
                full_index_i = all_class_names.index(class_name)
                full_index_j = all_class_names.index(other_class)
                full_conf_matrix[full_index_i, full_index_j] = conf_matrix_training[i, j]
        
        # Prepare class metrics for all classes
        class_metrics = {}
        for i, class_name in enumerate(all_class_names):
            if class_name in classes_in_training:
                index = classes_in_training.index(class_name)
                class_metrics[class_name] = {
                    'precision': float(precision[index]),
                    'recall': float(recall[index]),
                    'f1': float(f1[index])
                }
            else:
                class_metrics[class_name] = {
                    'precision': None,
                    'recall': None,
                    'f1': None
                }

        # Get feature importance scores
        importance_scores = model.feature_importances_
        
        # Prepare metrics
        metrics = {
            "accuracy": float(accuracy),
            "class_metrics": class_metrics,
            "confusion_matrix": full_conf_matrix.tolist(),
            "class_names": all_class_names,
            "classes_in_training": classes_in_training,
            "feature_importance": importance_scores.tolist()
        }
        
        encoders = {
            'date_encoder': date_encoder,
            'month_encoder': month_encoder,
            'label_encoder': le
        }
        
        # After getting predictions, map them back to global indices
        y_pred_global = np.array([consecutive_to_global[pred] for pred in y_pred])
        
        # Store both mappings in the model for use during prediction
        model.training_class_to_int = training_class_to_int
        model.consecutive_to_global = consecutive_to_global
        
        return model, metrics, encoders, all_class_names

    def save_model(self, model, model_name, model_description, metrics, model_params, encoders, training_set_ids, num_samples, all_class_names):
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
                    encoders=serialized_encoders,
                    all_class_names=all_class_names
                )

            # Use ModelStorage to save the file
            storage = ModelStorage()
            
            # Serialize model to bytes
            model_bytes = pickle.dumps(model)
            
            # If updating, delete old model file if it exists
            if model_record.model_file and storage.exists(model_record.model_file.name):
                storage.delete(model_record.model_file.name)
            
            # Save new model file with timestamp - REMOVE the leading slash
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            filename = f"model_{model_record.id}_{timestamp}.pkl"  # Remove the leading '/'
            
            # Save the file
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
        aoi_bounds = project.aoi.extent
        
        mosaic_id = PlanetUtils.get_mosaic_id(mosaic_name)
        quads = PlanetUtils.get_quad_info(mosaic_id, aoi_bounds)
        processed_quads = PlanetUtils.download_and_process_quads(quads, year, month, PlanetQuadStorage())
        
        return processed_quads

    def generate_predictions_after_training(self, model_id, basemap_dates):
        """Generate predictions for all basemap dates after training completes"""
        try:
            project = Project.objects.get(id=self.project_id)
            prediction_service = PredictionService(model_id, self.project_id)

            # Convert GeoDjango geometry to GeoJSON dict
            aoi_geojson = {
                'type': 'Polygon',
                'coordinates': [[[coord[0], coord[1]] for coord in project.aoi.coords[0]]]
            }

            self.update_progress(85, "Generating predictions...")
            
            # Create a partial function with fixed arguments
            generate_prediction_for_date = partial(
                self._generate_single_prediction,
                prediction_service=prediction_service,
                aoi_geojson=aoi_geojson
            )
            
            # Use ThreadPoolExecutor to parallelize predictions
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                # Submit all prediction tasks
                future_to_date = {
                    executor.submit(generate_prediction_for_date, date): date 
                    for date in basemap_dates
                }
                
                # Process completed predictions
                for i, future in enumerate(concurrent.futures.as_completed(future_to_date)):
                    date = future_to_date[future]
                    progress = 85 + (10 * (i + 1) / len(basemap_dates))
                    try:
                        future.result()  # This will raise any exceptions that occurred
                        self.update_progress(
                            progress, 
                            f"Completed prediction for {date}"
                        )
                    except Exception as e:
                        logger.error(f"Error predicting for date {date}: {str(e)}")
                        raise

        except Exception as e:
            logger.error(f"Error generating predictions: {str(e)}")
            raise

    def _generate_single_prediction(self, date, prediction_service, aoi_geojson):
        """Helper method to generate prediction for a single date"""
        try:
            prediction_name = f"Landcover_{date}"
            return prediction_service.generate_prediction(
                aoi_geojson,
                date,
                prediction_name
            )
        except Exception as e:
            logger.error(f"Error generating prediction for {date}: {str(e)}")
            raise
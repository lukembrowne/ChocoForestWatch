from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import rasterio
import json
from shapely.geometry import shape, mapping
from rasterio.mask import mask
import numpy as np
import os
from werkzeug.utils import secure_filename
import requests
from flask_sqlalchemy import SQLAlchemy
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape, from_shape
from geoalchemy2.functions import ST_AsGeoJSON
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm.exc import NoResultFound
import h5py
from sklearn.model_selection import train_test_split, cross_val_score
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib
from sklearn.preprocessing import LabelEncoder
import pdb
from datetime import datetime
from rasterio.windows import Window
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit
import threading
from requests.auth import HTTPBasicAuth
from shapely.geometry import shape, box
from loguru import logger
import sys
from flask.cli import with_appcontext
import click
from flask import current_app
from rasterio.merge import merge
import rasterio
from rasterio.warp import transform_bounds
from shapely import geometry
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
import uuid
from shapely.ops import transform
import pyproj



# Load environment variables from the .env file
load_dotenv()

# Load the Planet API key from an environment variable
PLANET_API_KEY = os.getenv('PLANET_API_KEY')
QUAD_DOWNLOAD_DIR = './data/planet_quads'


if not PLANET_API_KEY:
    raise ValueError("No PLANET_API_KEY set for Flask application. Did you follow the setup instructions?")

# Setup Planet base URL
API_URL = "https://api.planet.com/basemaps/v1/mosaics"

# Setup session
session = requests.Session()
session.auth = (PLANET_API_KEY, "")

# Create the Flask application
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
CORS(app, resources={r"/api/*": {"origins": "http://localhost:9000"}})
socketio = SocketIO(app, cors_allowed_origins="*")


# Configure loguru logger
log_file = "app.log"
logger.remove()  # Remove default handler
logger.add(sys.stderr, format="{time} {level} {message}", level="INFO")
logger.add(log_file, rotation="10 MB", retention="10 days", level="DEBUG")

# Middleware to log all requests
@app.before_request
def log_request_info():
    logger.info(f"Request: {request.method} {request.url}")
    logger.debug(f"Headers: {request.headers}")
    logger.debug(f"Body: {request.get_data()}")

@app.after_request
def log_response_info(response):
    logger.info(f"Response: {response.status}")
    return response

# Error handler to log exceptions
@app.errorhandler(Exception)
def handle_exception(e):
    logger.exception(f"An unhandled exception occurred: {str(e)}")
    return jsonify(error=str(e)), 500

# Define a directory to temporarily store uploaded files
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://cfwuser:1234d@localhost/cfwdb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Define models

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    aoi = db.Column(Geometry('GEOMETRY', srid=4326))  # This can store any geometry type
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    classes = db.Column(db.JSON)
    training_polygon_sets = db.relationship("TrainingPolygonSet", back_populates="project")
    trained_model = db.relationship("TrainedModel", back_populates="project")
    predictions = db.relationship('Prediction', back_populates='project')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'classes': self.classes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class TrainingPolygonSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    basemap_date = db.Column(db.String(7), nullable=False)
    polygons = db.Column(JSONB)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    feature_count = db.Column(db.Integer)

    project = db.relationship("Project", back_populates="training_polygon_sets")


class TrainedModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    training_set_ids = db.Column(db.JSON, nullable=False)  # Store as JSON array
    training_periods = db.Column(db.JSON)  # Store as a list of date ranges
    num_training_samples = db.Column(db.Integer)
    accuracy = db.Column(db.Float)
    class_metrics = db.Column(db.JSON)  # This will store precision, recall, and F1 for each class
    confusion_matrix = db.Column(db.JSON)
    file_path = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    model_parameters = db.Column(db.JSON)
    class_names = db.Column(db.JSON)  # Add this line
    date_encoder = db.Column(db.PickleType)  # Add this field to store the encoder
    month_encoder = db.Column(db.PickleType)  # Add this field to store the encoder
    label_encoder = db.Column(db.PickleType)
    all_class_names = db.Column(db.JSON)

    predictions = db.relationship("Prediction", back_populates="model", cascade="all, delete-orphan")
    project = db.relationship("Project", back_populates="trained_model")


    @classmethod
    def save_or_update_model(cls, model, name, description, project_id, training_set_ids, metrics, model_parameters, date_encoder, month_encoder, num_samples, training_periods, label_encoder, all_class_names):
        existing_model = cls.query.filter_by(project_id=project_id).first()
        
        if existing_model:
            # Update existing model
            logger.info(f"Updating existing model for project {project_id}")
            existing_model.name = name
            existing_model.description = description
            existing_model.training_set_ids = training_set_ids
            existing_model.training_periods = training_periods
            existing_model.num_training_samples = num_samples
            existing_model.accuracy = metrics['accuracy']
            existing_model.class_metrics = metrics['class_metrics']
            existing_model.class_names = metrics['class_names']
            existing_model.confusion_matrix = metrics['confusion_matrix']
            existing_model.model_parameters = model_parameters
            existing_model.date_encoder = date_encoder
            existing_model.month_encoder = month_encoder
            existing_model.label_encoder = label_encoder
            existing_model.all_class_names = all_class_names

            # Update the file
            model_dir = './trained_models'
            file_name = f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.joblib"
            file_path = os.path.join(model_dir, file_name)
            joblib.dump(model, file_path)
            
            # Remove old file if it exists
            if os.path.exists(existing_model.file_path):
                os.remove(existing_model.file_path)
            
            existing_model.file_path = file_path
            
            db.session.commit()
            return existing_model
        else:
            # Create new model (using existing save_model logic)
            return cls.save_model(model, name, description, project_id, training_set_ids, metrics, model_parameters, date_encoder, month_encoder, num_samples, training_periods, label_encoder, all_class_names)





    @classmethod
    def save_model(cls, model, name, description, project_id, training_set_ids, metrics, model_parameters, date_encoder, month_encoder, num_samples, training_periods,label_encoder, all_class_names):
        logger.info(f"Saving model for project {project_id}")
        model_dir = './trained_models'
        os.makedirs(model_dir, exist_ok=True)
        file_name = f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.joblib"
        file_path = os.path.join(model_dir, file_name)
        
        joblib.dump(model, file_path)
        
        new_model = cls(
            name=name,
            description=description,
            project_id=project_id,
            training_set_ids=training_set_ids,
            training_periods=training_periods,
            num_training_samples=num_samples,
            accuracy=metrics['accuracy'],
            class_metrics=metrics['class_metrics'],
            class_names=metrics['class_names'],
            confusion_matrix=metrics['confusion_matrix'],
            file_path=file_path,
            model_parameters=model_parameters,
            date_encoder=date_encoder,
            month_encoder=month_encoder,
            label_encoder=label_encoder,
            all_class_names=all_class_names

        )
        db.session.add(new_model)
        db.session.commit()
        return new_model
    
    # Add methods for renaming and deleting models
    def rename(self, new_name):
        self.name = new_name
        db.session.commit()

    def delete(self):
        file_path = str(self.file_path)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as e:
                current_app.logger.error(f"Error deleting file {file_path}: {e}")
        
        try:
            db.session.delete(self)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error when deleting model: {e}")
            raise

    @classmethod
    def get_by_id(cls, model_id):
        try:
            return cls.query.filter_by(id=model_id).one()
        except NoResultFound:
            return None

    @classmethod
    def load_model(cls, model_id):
        model_record = cls.query.get(model_id)
        if model_record:
            model = joblib.load(model_record.file_path)
            model.date_encoder = model_record.date_encoder  # Attach the date encoder to the model
            return model
        return None

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'project_id': self.project_id,
            'training_set_ids': self.training_set_ids,
            'accuracy': self.accuracy,
            'class_metrics': self.class_metrics,
            'class_names': self.class_names,  # Add this line
            'confusion_matrix': self.confusion_matrix,
            'created_at': self.created_at.isoformat(),
            'model_parameters': self.model_parameters
        }

class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    model_id = db.Column(db.Integer, db.ForeignKey('trained_model.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    basemap_date = db.Column(db.String(7), nullable=False)  # Store as 'YYYY-MM'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    project = db.relationship('Project', back_populates='predictions')
    model = db.relationship('TrainedModel', back_populates='predictions')

# Create tables
with app.app_context():
    db.create_all()


# Command for clearing databases for testing
@click.command('clear_db')
@with_appcontext
def clear_db_command():
    """Clear all data from the database."""
    if click.confirm('Are you sure you want to delete all data from the database?', abort=True):
        meta = db.metadata
        for table in reversed(meta.sorted_tables):
            click.echo(f'Clearing table {table}')
            db.session.execute(table.delete())
        db.session.commit()
        click.echo('All data has been cleared from the database.')

# Add this command to your Flask app
app.cli.add_command(clear_db_command)


# Serve static files from the 'data' directory
@app.route('/data/<path:filename>')
def data_files(filename):
    return send_from_directory('data', filename)

# Serve static files from the 'predictions' directory
@app.route('/predictions/<path:filename>')
def prediction_files(filename):
    return send_from_directory('predictions', filename)


# Project routes
@app.route('/api/projects', methods=['POST'])
def create_project():
    data = request.json

    project = Project(
        name=data.get('name', 'Untitled Project'),
        description=data.get('description', ''),
        classes=data.get('classes', [])
    )
    
    db.session.add(project)
    db.session.commit()
    
    return jsonify({
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "classes": project.classes
        # "aoi": json.loads(db.session.scalar(project.aoi.ST_AsGeoJSON()))
    }), 201

@app.route('/api/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    project = Project.query.get_or_404(project_id)
    
    project_data = {
        'id': project.id,
        'name': project.name,
        'description': project.description,
        'aoi': None,
        'classes': project.classes
    }
    
    if project.aoi:
        # Convert the PostGIS geometry to a GeoJSON
        shape = to_shape(project.aoi)
        geojson = mapping(shape)
        project_data['aoi'] = geojson

    return jsonify(project_data), 200

@app.route('/api/projects/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    project = Project.query.get_or_404(project_id)
    data = request.json
    
    if 'name' in data:
        project.name = data['name']
    if 'description' in data:
        project.description = data['description']
    if 'classes' in data:
        project.classes = data['classes']
    
    try:
        db.session.commit()
        return jsonify(project.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    
    try:
        db.session.delete(project)
        db.session.commit()
        return jsonify({'message': 'Project deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects', methods=['GET'])
def list_projects():
    print("getting projects")
    projects = Project.query.all()
    return jsonify([project.to_dict() for project in projects])

@app.route('/api/projects/<int:project_id>/aoi', methods=['POST'])
def set_project_aoi(project_id):
    project = Project.query.get_or_404(project_id)
    data = request.json

    if 'aoi' not in data:
        return jsonify({'error': 'AOI data is required'}), 400

    try:
        # Convert GeoJSON to shapely geometry
        geojson = data['aoi']
        shape = geometry.shape(geojson['geometry'])
        
        # Convert shapely geometry to WKT
        wkt = shape.wkt
        
        # Create a PostGIS geometry from WKT
        project.aoi = from_shape(shape, srid=4326)  # Assuming WGS84 projection
        db.session.commit()
        return jsonify({'message': 'AOI updated successfully', 'aoi': db.session.scalar(project.aoi.ST_AsGeoJSON())}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500





@app.route('/api/training_polygons', methods=['POST'])
def save_training_polygons():
    data = request.json
    project_id = data.get('project_id')
    basemap_date = data.get('basemap_date')
    polygons = data.get('polygons')
    name = data.get('name')  # New field for the name

    if not project_id or not basemap_date or not polygons or not name:
        return jsonify({'error': 'Missing required data'}), 400

    # If basemap_date is an object, extract the value
    if isinstance(basemap_date, dict):
        basemap_date = basemap_date.get('value')

    # Validate basemap_date format
    try:
        datetime.strptime(basemap_date, '%Y-%m')
    except ValueError:
        return jsonify({'error': 'Invalid basemap_date format. Use YYYY-MM.'}), 400

    training_set = TrainingPolygonSet(
        project_id=project_id,
        basemap_date=basemap_date,
        polygons=polygons,
        name=name,
        feature_count=len(polygons['features'])
    )
    db.session.add(training_set)

    try:
        db.session.commit()
        return jsonify({'message': 'Training polygons saved successfully', 'id': training_set.id}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/training_polygons/<int:project_id>', methods=['GET'])
def get_training_polygons(project_id):
    sets = TrainingPolygonSet.query.filter_by(project_id=project_id).all()
    return jsonify([{
        'id': s.id,
        'name': s.name,
        'basemap_date': s.basemap_date,
        'feature_count': s.feature_count,
        'created_at': s.created_at.isoformat(),
        'updated_at': s.updated_at.isoformat()
    } for s in sets])


@app.route('/api/training_polygons/<int:project_id>/<int:set_id>', methods=['GET'])
def get_specific_training_polygons(project_id, set_id):
    training_set = TrainingPolygonSet.query.filter_by(project_id=project_id, id=set_id).first()
    if training_set:
        return jsonify(training_set.polygons), 200
    else:
        return jsonify({'message': 'No training polygons found for this date'}), 404

@app.route('/api/training_polygons/<int:project_id>/<int:set_id>', methods=['PUT'])
def update_training_polygons(project_id, set_id):
    data = request.json
    name = data.get('name')
    basemap_date = data.get('basemap_date')
    polygons = data.get('polygons')

    try:
        training_set = TrainingPolygonSet.query.filter_by(id=set_id, project_id=project_id).first()
        if not training_set:
            return jsonify({'error': 'Training set not found'}), 404

        if name:
            training_set.name = name
        if basemap_date:
            training_set.basemap_date = basemap_date
        if polygons:
            training_set.polygons = polygons
            training_set.feature_count = len(polygons['features'])

        training_set.updated_at = datetime.utcnow()

        db.session.commit()
        return jsonify({'message': 'Training set updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/training_polygons/<int:project_id>/<int:set_id>', methods=['DELETE'])
def delete_training_set(project_id, set_id):
    try:
        training_set = TrainingPolygonSet.query.filter_by(id=set_id, project_id=project_id).first()
        if not training_set:
            return jsonify({'error': 'Training set not found'}), 404

        db.session.delete(training_set)
        db.session.commit()
        return jsonify({'message': 'Training set deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


def nan_to_null(obj):
    if isinstance(obj, float) and math.isnan(obj):
        return None
    return obj

@app.route('/api/training_data_summary/<int:project_id>', methods=['GET'])
def get_training_data_summary(project_id):
    try:
        training_sets = TrainingPolygonSet.query.filter_by(project_id=project_id).all()
        
        summary = {
            'totalSets': len(training_sets),
            'dateRange': {
                'start': min(set.basemap_date for set in training_sets),
                'end': max(set.basemap_date for set in training_sets)
            },
            'classStats': {}
        }

        project = Project.query.get(project_id)
        class_names = [cls['name'] for cls in project.classes]

        for class_name in class_names:
            summary['classStats'][class_name] = {
                'featureCount': 0,
                'totalArea': 0
            }

        for training_set in training_sets:
            for feature in training_set.polygons['features']:
                class_name = feature['properties']['classLabel']
                summary['classStats'][class_name]['featureCount'] += 1
                
                # # Calculate area in square kilometers
                # geom = shape(feature['geometry'])
                # geom_3857 = transform(
                #     pyproj.Transformer.from_crs('EPSG:4326', 'EPSG:3857', always_xy=True).transform,
                #     geom
                # )
                # area_km2 = geom_3857.area / 1_000_000  # Convert from square meters to square kilometers
                # summary['classStats'][class_name]['totalArea'] += area_km2

        # Convert NaN to null
        summary_json = json.dumps(summary, default=nan_to_null)
        summary = json.loads(summary_json)

        return jsonify(summary), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500




 ## Prediction routes   

@app.route('/api/predictions/<int:project_id>', methods=['GET'])
def get_predictions(project_id):
    predictions = Prediction.query.filter_by(project_id=project_id).all()
    return jsonify([{
        'id': p.id,
        'project_id': p.project_id,
        'model_id': p.model_id,
        'model_name': TrainedModel.query.get(p.model_id).name, 
        'name': p.name,
        'basemap_date': p.basemap_date,
        'created_at': p.created_at.isoformat(),
        'file_path': p.file_path
        } for p in predictions])

@app.route('/api/prediction/<int:prediction_id>', methods=['GET'])
def get_prediction(prediction_id):
    prediction = Prediction.query.get_or_404(prediction_id)
    
    # Read the extent from the GeoTIFF file
    with rasterio.open(prediction.file_path) as src:
        bounds = src.bounds

    return jsonify({
        'id': prediction.id,
        'basemap_date': prediction.basemap_date,
        'created_at': prediction.created_at.isoformat(),
        'file_path': prediction.file_path,
        'extent': [bounds.left, bounds.bottom, bounds.right, bounds.top]
    })


@app.route('/api/trained_models/<int:project_id>', methods=['GET'])
def get_trained_models(project_id):
   
    models =  TrainedModel.query.filter_by(project_id=project_id).all()
    
    return jsonify([{
            'id': model.id,
            'name': model.name,
            'description': model.description,
            'created_at': model.created_at.isoformat(),
            'accuracy': model.accuracy,
            'training_periods': model.training_periods,
            'num_training_samples': model.num_training_samples,
            'model_parameters': model.model_parameters
        } for model in models])


@app.route('/api/trained_models/<int:model_id>/metrics', methods=['GET'])
def get_model_metrics(model_id):
    try:
        model = TrainedModel.query.get_or_404(model_id)
        return jsonify(model.to_dict())
    except SQLAlchemyError as e:
        return jsonify({'error': 'Database error occurred', 'details': str(e)}), 500


@app.route('/api/trained_models/<int:model_id>/rename', methods=['PUT'])
def rename_model(model_id):
    data = request.json
    new_name = data.get('new_name')
    
    if not new_name:
        return jsonify({'error': 'New name is required'}), 400

    try:
        model = TrainedModel.query.get_or_404(model_id)
        model.rename(new_name)
        return jsonify({'message': 'Model renamed successfully', 'new_name': new_name}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred', 'details': str(e)}), 500

@app.route('/api/trained_models/<int:model_id>', methods=['DELETE'])
def delete_model(model_id):
    model = TrainedModel.get_by_id(model_id)
    if model is None:
        return jsonify({"error": "Model not found"}), 404

    try:
        model.delete()
        return jsonify({"message": "Model deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting model: {str(e)}")
        return jsonify({"error": "Database error occurred", "details": str(e)}), 500

@app.route('/api/train_model', methods=['POST'])
def train_model():
    data = request.json
    project_id = data['projectId']
    model_name = data['modelName']
    aoi_extent = data['aoiExtent']
    model_description = data.get('modelDescription', '')
    split_method = data.get('splitMethod', 'feature')
    train_test_split = data.get('trainTestSplit', 0.2)

    model_params = {
        'objective': 'multi:softmax',
        'n_estimators': data.get('n_estimators', 100),
        'max_depth': data.get('max_depth', 3),
        'learning_rate': data.get('learning_rate', 0.1),
        'min_child_weight': data.get('min_child_weight', 1),
        'gamma': data.get('gamma', 0),
        'colsample_bytree': data.get('colsample_bytree', 0.8),
        'subsample': data.get('subsample', 0.8),
    }

    
    try:
        # Fetch all training sets
        training_sets = TrainingPolygonSet.query.filter_by(project_id=project_id).all()
        if not training_sets:
            return jsonify({"error": "No training sets found for this project"}), 404

        # Get unique basemap dates
        unique_dates = set(ts.basemap_date for ts in training_sets)

        # Step 1: Get Planet quads
        update_progress(project_id, 0.1, "Fetching Planet quads")
        
        quads_by_date = {}
        for date in unique_dates:
            update_progress(project_id, 0.2, f"Fetching Planet quads for {date}")
            quads_by_date[date] = get_planet_quads(aoi_extent, date)

        # Step 2: Extract pixels from quads using training polygons
        update_progress(project_id, 0.3, "Extracting pixels from quads")
        all_X = []
        all_y = []
        all_feature_ids = []
        all_basemap_dates = []

        for training_set in training_sets:
            update_progress(project_id, 0.3, f"Extracting pixels from quads for {training_set.basemap_date}")
            X, y, feature_ids = extract_pixels_from_quads(quads_by_date[training_set.basemap_date], training_set.polygons['features']) 
            all_X.append(X)
            all_y.extend(y)
            all_feature_ids.extend(feature_ids)
            all_basemap_dates.extend([training_set.basemap_date] * len(y))

        # Combine all data
        X = np.vstack(all_X)
        y = np.array(all_y)
        feature_ids = np.array(all_feature_ids)
        basemap_dates = np.array(all_basemap_dates)

        # Convert basemap dates to numerical values
        date_encoder = LabelEncoder()
        encoded_dates = date_encoder.fit_transform(basemap_dates)

        # Create month column
        months = np.array([datetime.strptime(date, '%Y-%m').month for date in basemap_dates])
        month_encoder = LabelEncoder()
        encoded_months = month_encoder.fit_transform(months)

        # Add encoded dates as a new feature
        X = np.column_stack((X, encoded_dates, encoded_months))

        # Step 3: Train XGBoost model
        update_progress(project_id, 0.6, "Training XGBoost model")
        # Train the model
        model, metrics = train_xgboost_model(X, y, feature_ids, project_id, [ts.id for ts in training_sets], model_name, model_description, model_params, date_encoder, month_encoder, split_method, train_test_split)

        # Step 5: Return results
        update_progress(project_id, 1.0, "Training complete")
        return {
            **metrics, 
            "model_id": model.id,
        }

    except Exception as e:
        logger.exception(f"Error in training process: {str(e)}")
        update_progress(project_id, 1.0, f"Error: {str(e)}")



def extract_pixels_from_training_set(training_set, quads):
    X = []
    y = []

    for feature in training_set.polygons['features']:
        geom = shape(feature['geometry'])
        class_label = feature['properties']['classLabel']

        # Find the quad(s) that intersect with this feature
        intersecting_quads = [quad for quad in quads if intersects(geom.bounds, quad['extent'])]

        for quad in intersecting_quads:
            with rasterio.open(quad['filename']) as src:
                out_image, out_transform = mask(src, [geom], crop=True, all_touched=True, indexes=[1, 2, 3, 4])
                
                pixels = out_image.reshape(4, -1).T
                
                X.extend(pixels)
                y.extend([class_label] * pixels.shape[0])

    return np.array(X), np.array(y)

def intersects(bounds1, bounds2):
    return not (bounds1[2] < bounds2[0] or bounds1[0] > bounds2[2] or 
                bounds1[3] < bounds2[1] or bounds1[1] > bounds2[3])

def update_progress(project_id, progress, message, data=None):
    socketio.emit('training_update', {
        'projectId': project_id,
        'progress': progress,
        'message': message,
        'data': data
    })

    logger.info(f"Project {project_id}: {message} - Progress: {progress * 100}%")
    if data:
        logger.debug(f"Project {project_id}: Additional data - {data}")



def get_planet_quads(aoi_extent, basemap_date):
    if not PLANET_API_KEY:
        raise ValueError("PLANET_API_KEY environment variable is not set")

    year, month = basemap_date.split('-')
    mosaic_name = f"planet_medres_normalized_analytic_{year}-{month}_mosaic"
    
    # Find the mosaic ID
    mosaic_id = get_mosaic_id(mosaic_name)
    
    # Get quad info for the AOI
    quads = get_quad_info(mosaic_id, aoi_extent)

    # Download and process quads
    processed_quads = download_and_process_quads(quads, year, month)
    
    return processed_quads

def get_quad_info(mosaic_id, bbox):

    # Get the bounding box
    minx, miny, maxx, maxy = bbox
    bbox_comma = f"{minx},{miny},{maxx},{maxy}"

    url = f"https://api.planet.com/basemaps/v1/mosaics/{mosaic_id}/quads"
    params = {
        "bbox": bbox_comma,
        "minimal": "true"  # Use string "true" instead of boolean True
    }

    response = requests.get(url, auth=HTTPBasicAuth(PLANET_API_KEY, ''), params=params)
    response.raise_for_status()

    return response.json().get('items', [])


def get_mosaic_id(mosaic_name):
    url = "https://api.planet.com/basemaps/v1/mosaics"
    params = {"name__is": mosaic_name}
    response = requests.get(url, auth=HTTPBasicAuth(PLANET_API_KEY, ''), params=params)
    response.raise_for_status()
    mosaics = response.json().get('mosaics', [])
    if not mosaics:
        raise ValueError(f"No mosaic found with name: {mosaic_name}")
    


    return mosaics[0]['id']


def download_and_process_quads(quads, year, month):
    processed_quads = []
    for quad in quads:
        quad_id = quad['id']
        download_url = quad['_links']['download']
        
        # Create directory for storing quads
        quad_dir = os.path.join(QUAD_DOWNLOAD_DIR, year, month)
        try:
            os.makedirs(quad_dir, exist_ok=True)
            logger.info(f"Created directory: {quad_dir}")
        except Exception as e:
            logger.error(f"Failed to create directory {quad_dir}: {str(e)}")
            continue
        
        # Download the quad
        local_filename = os.path.join(quad_dir, f"{quad_id}_{year}_{month}.tif")
        if not os.path.exists(local_filename):
            logger.info(f"Downloading quad {quad_id} for {year}-{month}")
            try:
                response = requests.get(download_url, auth=HTTPBasicAuth(PLANET_API_KEY, ''), stream=True)
                response.raise_for_status()
                with open(local_filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.success(f"Successfully downloaded quad {quad_id} to {local_filename}")
            except Exception as e:
                logger.error(f"Failed to download quad {quad_id}: {str(e)}")
                continue
        else:
            logger.info(f"Quad {quad_id} already exists at {local_filename}, skipping download")

        processed_quads.append({
            'id': quad_id,
            'filename': local_filename,
            'bbox': quad['bbox']
        })
    
    return processed_quads



def extract_pixels_from_quads(quads, polygons):
    all_pixels = []
    all_labels = []
    all_feature_ids = []  # New list to store feature IDs


    for quad in quads:
        logger.info(f"Extracting pixels from quad {quad['id']}")

        with rasterio.open(quad['filename']) as src:
            
            for feature in polygons:

                geom = shape(feature['geometry'])
                class_label = feature['properties']['classLabel']
                feature_id = feature['id']  # Assuming each feature has an 'id' property
                try:
                    # Read only the first 4 bands
                    out_image, out_transform = mask(src, [geom], crop=True, all_touched=True, indexes=[1, 2, 3, 4])
                    
                    # Handle nodata values
                    if src.nodata is not None:
                        out_image = np.ma.masked_equal(out_image, src.nodata)
                    
                    # Reshape the output to have pixels as rows and bands as columns
                    pixels = out_image.reshape(4, -1).T
                    
                    # Remove any pixels where all bands are masked or invalid
                    if isinstance(pixels, np.ma.MaskedArray):
                        valid_pixels = pixels[~np.all(pixels.mask, axis=1)]
                    else:
                        # If it's not a masked array, we'll consider a pixel invalid if all bands are equal to nodata
                        valid_pixels = pixels[~np.all(pixels == src.nodata, axis=1)] if src.nodata is not None else pixels
                    
                    if valid_pixels.size > 0:
                        all_pixels.extend(valid_pixels.data if isinstance(valid_pixels, np.ma.MaskedArray) else valid_pixels)
                        all_labels.extend([class_label] * valid_pixels.shape[0])
                        all_feature_ids.extend([feature_id] * valid_pixels.shape[0])  # Add feature IDs


                except Exception as e:
                    logger.warning(f"Error processing polygon in quad {quad['id']}: {str(e)}")

    if not all_pixels:
        raise ValueError("No valid pixels extracted from quads")
    
    X = np.array(all_pixels, dtype=float)
    y = np.array(all_labels)
    feature_ids = np.array(all_feature_ids)
    
    logger.debug(f"Extracted X shape: {X.shape}")
    logger.debug(f"Extracted X first few rows: \n{X[:5]}")
    logger.debug(f"Feature IDs shape: {feature_ids.shape}")
    logger.debug(f"Feature IDs first few values: {feature_ids[:5]}")
    
    return X, y, feature_ids




def train_xgboost_model(X, y, feature_ids, project_id, training_set_ids, model_name, model_description, model_params, date_encoder, month_encoder, split_method='feature', test_size=0.2):
    
     # Fetch all project classes
    project = Project.query.get(project_id)
    all_class_names = [cls['name'] for cls in project.classes]
    
    # Create a LabelEncoder for classes in the training data
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    np.unique(y, return_counts = True)
    np.unique(y_encoded, return_counts = True)
    
    # Get the classes actually present in the training data
    classes_in_training = le.classes_.tolist()

    # Extract encoded dates and months from X
    encoded_dates = X[:, -2].astype(int)
    encoded_months = X[:, -1].astype(int)
    # X = X[:, :-2]  # Remove the date and month columns from X

    logger.debug(f"X shape: {X.shape}")
    logger.debug(f"X data type: {X.dtype}")
    logger.debug(f"X first few rows: \n{X[:5]}")
    logger.debug(f"Feature IDs shape: {feature_ids.shape}")
    logger.debug(f"Feature IDs first few values: {feature_ids[:5]}")

    if split_method == 'feature':

            # Get unique feature IDs and their corresponding classes
            unique_features, unique_indices = np.unique(feature_ids, return_index=True)
            unique_classes = y[unique_indices]
        
            # Split features into train and test, stratified by class
            train_features, test_features = train_test_split(
                unique_features, 
                test_size=test_size, 
                random_state=42, 
                stratify=unique_classes
            )
            
            # Create masks for train and test sets
            train_mask = np.isin(feature_ids, train_features)
            test_mask = np.isin(feature_ids, test_features)
            
            # Split data using the masks
            X_train, X_test = X[train_mask], X[test_mask]
            y_train, y_test = y_encoded[train_mask], y_encoded[test_mask]
    else:
            # Pixel-based split
            X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=test_size, random_state=42)

    # Adjust num_class parameter to account for classes present in the data
    model_params['num_class'] = len(classes_in_training)

    # Create and train model
    model = XGBClassifier(**model_params)
    model.fit(
            X_train, 
            y_train, 
            eval_set=[(X_test, y_test)], 
            verbose=False
        )

    # Predictions and metrics
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    # Calculate metrics
    precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average=None)
    
    # Create confusion matrix
    conf_matrix_training = confusion_matrix(y_test, y_pred)

    # Create full-size confusion matrix
    full_conf_matrix = np.zeros((len(all_class_names), len(all_class_names)), dtype=int)
    for i, class_name in enumerate(classes_in_training):
        for j, other_class in enumerate(classes_in_training):
            full_index_i = all_class_names.index(class_name)
            full_index_j = all_class_names.index(other_class)
            full_conf_matrix[full_index_i, full_index_j] = conf_matrix_training[i, j]
    
    # Prepare class metrics
    class_metrics = {}
    for i, class_name in enumerate(all_class_names):
        if class_name in classes_in_training:
            index = classes_in_training.index(class_name)
            class_metrics[class_name] = {
                'precision': precision[index],
                'recall': recall[index],
                'f1': f1[index]
            }
        else:
            class_metrics[class_name] = {
                'precision': None,
                'recall': None,
                'f1': None
            }
    
    metrics = {
        "accuracy": accuracy,
        "class_metrics": class_metrics,
        "confusion_matrix": full_conf_matrix.tolist(),
        "class_names": all_class_names,
        "classes_in_training": classes_in_training
    }

     # Calculate number of training samples
    num_training_samples = X_train.shape[0]


    # Determine training periods
    unique_encoded_dates = np.unique(encoded_dates)
    training_periods = date_encoder.inverse_transform(unique_encoded_dates).tolist()

   # Save the trained model
    saved_model = TrainedModel.save_or_update_model(
        model, 
        model_name,
        model_description,
        project_id, 
        training_set_ids, 
        metrics, 
        model_params,
        date_encoder,
        month_encoder,
        num_training_samples,
        training_periods,
        le,
        all_class_names
    )

    return saved_model, metrics


### Prediction


@app.route('/api/predictions/<int:prediction_id>/rename', methods=['PUT'])
def rename_prediction(prediction_id):
    try:
        prediction = Prediction.query.get_or_404(prediction_id)
        data = request.json
        new_name = data.get('new_name')
        
        if not new_name:
            return jsonify({'error': 'New name is required'}), 400
        
        prediction.name = new_name
        db.session.commit()
        
        return jsonify({'message': 'Prediction renamed successfully', 'new_name': new_name})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/predictions/<int:prediction_id>', methods=['DELETE'])
def delete_prediction(prediction_id):
    try:
        prediction = Prediction.query.get_or_404(prediction_id)
        
        # Delete the associated file
        if os.path.exists(prediction.file_path):
            os.remove(prediction.file_path)
        
        db.session.delete(prediction)
        db.session.commit()
        
        return jsonify({'message': 'Prediction deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500







@app.route('/api/predict_landcover', methods=['POST'])
def predict_landcover():
    data = request.json
    project_id = data['projectId']
    model_id = data['modelId']
    basemap_date = data['basemapDate']
    prediction_name = data['predictionName']
    aoi_extent = data['aoiExtent']
    aoi_extent_lat_lon = data['aoiExtentLatLon']


    # Fetch the model
    model = TrainedModel.query.get(model_id)
    if not model:
        return jsonify({"error": "Model not found"}), 404

    # Fetch the quads for the AOI and basemap date
    quads = get_planet_quads(aoi_extent_lat_lon, basemap_date)

    # Perform the prediction
    prediction_file = predict_landcover_aoi(model.id, quads, aoi_extent, project_id, basemap_date)

    # Save prediction to database
    prediction = Prediction(
        project_id=project_id,
        model_id=model.id,
        file_path=prediction_file,
        basemap_date=basemap_date,
        name=prediction_name
    )
    db.session.add(prediction)
    db.session.commit()

    return jsonify({
        "message": "Prediction completed",
        "prediction_id": prediction.id,
        "file_path": prediction.file_path
    })


def predict_landcover_aoi(model_id, quads, aoi, project_id, basemap_date):
    model_record = TrainedModel.query.get(model_id)
    if model_record is None:
        raise ValueError("Model not found")

    logger.debug(f"AOI: {aoi}")

    # Create a list to store the predicted rasters
    predicted_rasters = []
    temp_files = []  # To keep track of temporary files for cleanup
    quad_bounds = []

    model = joblib.load(model_record.file_path)


    # Load the date encoder used during training
    date_encoder = model_record.date_encoder  
    month_encoder = model_record.month_encoder 
    label_encoder = model_record.label_encoder  # Load the LabelEncoder 
    all_class_names = model_record.all_class_names

    # Create a mapping from model output to full class set indices
    model_classes = label_encoder.classes_
    class_index_map = {i: all_class_names.index(class_name) for i, class_name in enumerate(model_classes)}
    
    
# If the current basemap_date wasn't in the training data, we need to handle it
    if basemap_date not in date_encoder.classes_:
        logger.warning(f"Basemap date {basemap_date} not in training data. Using nearest date.")
        nearest_date = min(date_encoder.classes_, key=lambda x: abs(int(x.replace('-', '')) - int(basemap_date.replace('-', ''))))
        encoded_date = date_encoder.transform([nearest_date])[0]
    else:
        encoded_date = date_encoder.transform([basemap_date])[0]

    # Extract and encode the month
    month = int(basemap_date.split('-')[1])
    encoded_month = month_encoder.transform([month])[0]


    for i, quad in enumerate(quads):
        with rasterio.open(quad['filename']) as src:
            logger.debug(f"Processing quad: {quad['filename']}")
            logger.debug(f"Quad CRS: {src.crs}")
            logger.debug(f"Quad bounds: {src.bounds}")
            quad_bounds.append(src.bounds)

            # Read only the first 4 bands
            data = src.read(list(range(1, 5)))
            meta = src.meta.copy()
            meta.update(count=1)

            # Reshape the data for prediction
            reshaped_data = data.reshape(4, -1).T
            
            # Add the encoded date and month as features
            date_column = np.full((reshaped_data.shape[0], 1), encoded_date)
            month_column = np.full((reshaped_data.shape[0], 1), encoded_month)
            prediction_data = np.hstack((reshaped_data, date_column, month_column))
            predictions = model.predict(prediction_data)

           # Map predictions to full class set indices
            prediction_map = np.vectorize(class_index_map.get)(predictions)
    
            # Reshape the prediction map
            prediction_map = prediction_map.reshape(data.shape[1], data.shape[2])
    
            # Create a temporary file for this quad's prediction with a unique name
            temp_filename = f'temp_prediction_{i}.tif'
            with rasterio.open(temp_filename, 'w', **meta) as tmp:
                tmp.write(prediction_map.astype(rasterio.uint8), 1)

            predicted_rasters.append(rasterio.open(temp_filename))
            temp_files.append(temp_filename)

    # # Check if quads are adjacent or overlapping
    # are_quads_adjacent = check_quads_adjacent(quad_bounds)
    # logger.debug(f"Are quads adjacent or overlapping: {are_quads_adjacent}")

    # if are_quads_adjacent:
    #     # Use rasterio merge if quads are adjacent or overlapping
    #     mosaic, out_transform = merge(predicted_rasters)
    # else:
    #     # Manual merging if quads are not adjacent
    #     mosaic, out_transform = manual_merge(predicted_rasters, quad_bounds)


    # Ensure AOI is in the same CRS as the raster
    # aoi_geom = box(*aoi)
    # pdb.set_trace()
    # aoi_bounds = transform_bounds("EPSG:4326", src.crs, *aoi)
    # aoi_geom = box(*aoi_bounds)
    # logger.debug(f"Transformed AOI bounds: {aoi_bounds}")
    mosaic, out_transform = merge(predicted_rasters, bounds = aoi)

    
    logger.debug(f"Merged raster shape: {mosaic.shape}")
    logger.debug(f"Merged raster transform: {out_transform}")
    
    # Create a temporary file for the merged prediction
    merged_temp_filename = 'temp_merged_prediction.tif'
    merged_meta = src.meta.copy()
    merged_meta.update({
            "driver": "GTiff",
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": out_transform,
            "compress": 'lzw'
        })
    merged_meta.update(count=1)

    # Create the final output file
    unique_id = uuid.uuid4().hex
    output_file = f"./predictions/landcover_prediction_project{project_id}_{basemap_date}_{unique_id}.tif"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Write the clipped raster
    with rasterio.open(output_file, "w", **merged_meta) as dest:
        dest.write(mosaic)

    # Clean up temporary files
    for raster in predicted_rasters:
        raster.close()
    for temp_file in temp_files:
        os.remove(temp_file)

    logger.debug(f"Final prediction file: {output_file}")

    return output_file




## Analysis endpoints
@app.route('/api/analysis/summary/<int:prediction_id>', methods=['GET'])
def get_summary_statistics(prediction_id):
    try:
        prediction = Prediction.query.get_or_404(prediction_id)

        with rasterio.open(prediction.file_path) as src:
            raster_data = src.read(1)  # Assuming single band raster
            pixel_area_ha = abs(src.transform[0] * src.transform[4]) / 10000  # Convert to hectares
            
            # Get unique class values and their counts
            unique, counts = np.unique(raster_data, return_counts=True)
            
            # Calculate total area
            total_area = raster_data.size * pixel_area_ha
            # Get class names from the project
            project = Project.query.get(prediction.project_id)
            class_names = {i: cls['name'] for i, cls in enumerate(project.classes)}
            
            # Calculate statistics
            class_stats = {}
            for value, count in zip(unique, counts):
                if value in class_names:
                    area = count * pixel_area_ha
                    percentage = (count / raster_data.size) * 100
                    class_stats[int(value)] = { 'area_km2': area, 'percentage': percentage}

                    logger.debug(f"Class {value} has area {area} and percentage {percentage}")
                    logger.debug(print(class_stats))
            
            # Prepare the result
            result = {
                'prediction_name': prediction.name,
                'prediction_date': prediction.basemap_date,
                'total_area_km2': total_area,
                'class_statistics': class_stats
            }
            

            return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error in get_summary_statistics: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/analysis/change/<int:prediction1_id>/<int:prediction2_id>', methods=['GET'])
def analyze_change(prediction1_id, prediction2_id):
    try:
        prediction1 = Prediction.query.get_or_404(prediction1_id)
        prediction2 = Prediction.query.get_or_404(prediction2_id)

        model1 = TrainedModel.query.get(prediction1.model_id)
        model2 = TrainedModel.query.get(prediction2.model_id)

        if model1 is None or model2 is None:
            return jsonify({'error': 'Associated model not found'}), 404

        # Ensure both predictions use the same set of classes
        if model1.all_class_names != model2.all_class_names:
            return jsonify({'error': 'Predictions use different class sets'}), 400

        all_class_names = model1.all_class_names
        class_index_map1 = {i: all_class_names.index(class_name) for i, class_name in enumerate(model1.label_encoder.classes_)}
        class_index_map2 = {i: all_class_names.index(class_name) for i, class_name in enumerate(model2.label_encoder.classes_)}

        with rasterio.open(prediction1.file_path) as src1, rasterio.open(prediction2.file_path) as src2:
            if src1.bounds != src2.bounds or src1.res != src2.res:
                return jsonify({"error": "Predictions have different extents or resolutions"}), 400

            data1 = src1.read(1)
            data2 = src2.read(1)

            pixel_area_ha = abs(src1.transform[0] * src1.transform[4]) / 10000  # Area in hectares

            # Map the raster data to the full class set indices
            mapped_data1 = np.vectorize(class_index_map1.get)(data1)
            mapped_data2 = np.vectorize(class_index_map2.get)(data2)

            # Calculate areas for each class in both predictions
            areas1 = {all_class_names[i]: np.sum(mapped_data1 == i) * pixel_area_ha for i in range(len(all_class_names))}
            areas2 = {all_class_names[i]: np.sum(mapped_data2 == i) * pixel_area_ha for i in range(len(all_class_names))}

            # Calculate changes
            changes = {name: areas2[name] - areas1[name] for name in all_class_names}

            # Calculate percentages
            total_area = data1.size * pixel_area_ha
            percentages1 = {name: (area / total_area) * 100 for name, area in areas1.items()}
            percentages2 = {name: (area / total_area) * 100 for name, area in areas2.items()}

            # Calculate total changed area
            total_change = sum(abs(change) for change in changes.values()) / 2  # Divide by 2 to avoid double counting

            # Generate confusion matrix
            cm = confusion_matrix(mapped_data1.flatten(), mapped_data2.flatten(), labels=range(len(all_class_names)))
            cm_percent = cm / cm.sum() * 100

            results = {
                "prediction1_name": prediction1.name,
                "prediction1_date": prediction1.basemap_date,
                "prediction2_name": prediction2.name,
                "prediction2_date": prediction2.basemap_date,
                "total_area_ha": float(total_area),
                "areas_time1_ha": {name: float(area) for name, area in areas1.items()},
                "areas_time2_ha": {name: float(area) for name, area in areas2.items()},
                "percentages_time1": {name: float(pct) for name, pct in percentages1.items()},
                "percentages_time2": {name: float(pct) for name, pct in percentages2.items()},
                "changes_ha": {name: float(change) for name, change in changes.items()},
                "total_change_ha": float(total_change),
                "change_rate": float((total_change / total_area) * 100),
                "confusion_matrix": cm.tolist(),
                "confusion_matrix_percent": cm_percent.tolist(),
                "class_names": all_class_names
            }

            return jsonify(results)

    except Exception as e:
        logger.error(f"Error in analyze_change: {str(e)}")
        return jsonify({'error': str(e)}), 500


# def analyze_change(prediction1_id, prediction2_id):
#     # Fetch the prediction rasters
#     prediction1 = Prediction.query.get_or_404(prediction1_id)
#     prediction2 = Prediction.query.get_or_404(prediction2_id)

#     # Read the rasters
#     with rasterio.open(prediction1.file_path) as src1, rasterio.open(prediction2.file_path) as src2:
#         # Ensure the rasters have the same extent and resolution
#         if src1.bounds != src2.bounds or src1.res != src2.res:
#             return jsonify({"error": "Predictions have different extents or resolutions"}), 400

#         # Read the data
#         data1 = src1.read(1)
#         data2 = src2.read(1)

#         # Calculate areas
#         pixel_area = src1.res[0] * src1.res[1] / 1_000_000  # Area in sq km

#         previous_forest = np.sum(data1 == 1) * pixel_area
#         previous_non_forest = np.sum(data1 == 0) * pixel_area
#         current_forest = np.sum(data2 == 1) * pixel_area
#         current_non_forest = np.sum(data2 == 0) * pixel_area

#         # Calculate change
#         deforested = np.sum((data1 == 1) & (data2 == 0)) * pixel_area
#         reforested = np.sum((data1 == 0) & (data2 == 1)) * pixel_area

#         total_area = previous_forest + previous_non_forest
#         deforestation_rate = (deforested - reforested) / previous_forest * 100
#         total_area_changed = deforested + reforested

#         results = {
#             "previousForestArea": float(previous_forest),
#             "previousNonForestArea": float(previous_non_forest),
#             "currentForestArea": float(current_forest),
#             "currentNonForestArea": float(current_non_forest),
#             "deforestedArea": float(deforested),
#             "reforestedArea": float(reforested),
#             "deforestationRate": float(deforestation_rate),
#             "totalAreaChanged": float(total_area_changed),
#             "totalArea": float(total_area)
#         }

#         logger.info(f"Change analysis results: {results}")

#         return jsonify(results)

# # Add this route to your Flask app
# @app.route('/api/analyze_change', methods=['POST'])
# def api_analyze_change():
#     data = request.json
#     prediction1_id = data.get('prediction1_id')
#     prediction2_id = data.get('prediction2_id')
    
#     if not prediction1_id or not prediction2_id:
#         return jsonify({"error": "Both prediction IDs are required"}), 400

#     return analyze_change(prediction1_id, prediction2_id)



if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(debug=True)






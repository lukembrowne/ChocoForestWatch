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
from sklearn.model_selection import train_test_split, cross_val_score
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib
from sklearn.preprocessing import LabelEncoder
import pdb
from datetime import datetime, timedelta
from rasterio.windows import Window
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit
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
from pyproj import Transformer
from celery import Celery, group, shared_task
from contextlib import contextmanager
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine
from celery.result import AsyncResult
import time
from rasterio.features import sieve
from rasterio.mask import mask
from shapely.geometry import box, mapping
import tempfile
from flask_migrate import Migrate
from rasterio import features
import shapely.ops
from shapely.geometry import shape, mapping
# import geopandas as gpd
import math
from flask_cors import cross_origin


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

db = SQLAlchemy()
migrate = Migrate()
celery = Celery(__name__)

# Initialize database engine and session factory
engine = None
SessionFactory = None

def create_app():
    app = Flask(__name__)
    
    # App configurations
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
    app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

    # Add these configurations for the database pool
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,
        'max_overflow': 20,
        'pool_pre_ping': True,
    }
    
    db.init_app(app)
    migrate.init_app(app, db)  # Initialize Flask-Migrate with the app and db

    # Initialize engine and SessionFactory
    global engine, SessionFactory
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'], **app.config['SQLALCHEMY_ENGINE_OPTIONS'])
    SessionFactory = sessionmaker(bind=engine)
    
    # Update Celery config
    celery.conf.update(
        broker_url=app.config['CELERY_BROKER_URL'],
        result_backend=app.config['CELERY_RESULT_BACKEND']
    )

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return app

app = create_app()

# Create the Flask application
# app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
CORS(app, resources={r"/api/*": {"origins": "http://localhost:9000"}})
socketio = SocketIO(app, cors_allowed_origins="*")



# Configure loguru logger
log_file = "app.log"
logger.remove()  # Remove default handler
logger.add(sys.stderr, format="{time} {level} {message}", level="INFO")
logger.add(log_file, rotation="10 MB", retention="10 days", level="DEBUG")


# Define a directory to temporarily store uploaded files
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


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




# Define models
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    aoi = db.Column(Geometry('GEOMETRY', srid=4326))  # This can store any geometry type
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    classes = db.Column(db.JSON)
    training_polygon_sets = db.relationship("TrainingPolygonSet", back_populates="project", cascade="all, delete-orphan")
    trained_model = db.relationship("TrainedModel", back_populates="project", cascade="all, delete-orphan")
    predictions = db.relationship('Prediction', back_populates='project', cascade="all, delete-orphan")
    aoi_area_ha = db.Column(db.Float)  # Area in hectares


    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'classes': self.classes,
            'aoi_area_ha': self.aoi_area_ha,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class TrainingPolygonSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    basemap_date = db.Column(db.String(7), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    feature_count = db.Column(db.Integer)
    excluded = db.Column(db.Boolean, default=False)
    polygons = db.Column(JSONB)

    project = db.relationship("Project", back_populates="training_polygon_sets")


class TrainedModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Add this line
    training_set_ids = db.Column(db.JSON, nullable=False)  # Store as JSON array
    training_periods = db.Column(db.JSON)  # Store as a list of date ranges
    num_training_samples = db.Column(db.Integer)
    accuracy = db.Column(db.Float)
    class_metrics = db.Column(db.JSON)  # This will store precision, recall, and F1 for each class
    confusion_matrix = db.Column(db.JSON)
    file_path = db.Column(db.String(255), nullable=False)
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
            existing_model.updated_at = datetime.utcnow()  # Add this line
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
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,  # Add this line
            'model_parameters': self.model_parameters
        }

class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    model_id = db.Column(db.Integer, db.ForeignKey('trained_model.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'land_cover' or 'deforestation'
    name = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    basemap_date = db.Column(db.String(7), nullable=True)  # Store as 'YYYY-MM'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    summary_statistics = db.Column(JSONB, nullable=True)

    project = db.relationship('Project', back_populates='predictions')
    model = db.relationship('TrainedModel', back_populates='predictions')
    hotspots = db.relationship('DeforestationHotspot', back_populates='prediction', cascade="all, delete-orphan")

class DeforestationHotspot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prediction_id = db.Column(db.Integer, db.ForeignKey('prediction.id'), nullable=False)
    geometry = db.Column(JSONB, nullable=False)
    area_ha = db.Column(db.Float, nullable=False)
    perimeter_m = db.Column(db.Float, nullable=False)
    compactness = db.Column(db.Float, nullable=False)
    edge_density = db.Column(db.Float, nullable=False)  # perimeter/area ratio
    centroid_lon = db.Column(db.Float, nullable=False)
    centroid_lat = db.Column(db.Float, nullable=False)
    verification_status = db.Column(db.String(20), nullable=True)  # 'verified', 'rejected', 'unsure'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    source = db.Column(db.String(20), nullable=False, default='ml')  # 'ml' or 'gfw'
    confidence = db.Column(db.Integer, nullable=True)  # For GFW confidence levels

    prediction = db.relationship('Prediction', back_populates='hotspots')


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

# Serve static files from the 'deforestation' directory
@app.route('/deforestation/<path:filename>')
def deforestation_files(filename):
    return send_from_directory('deforestation', filename)

@app.route('/favicon.ico')
def favicon():
    return '', 204


@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

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
    
    # Initialize TrainingPolygonSet entries
    basemap_dates = data.get('basemap_dates', [])
    initialize_training_polygon_sets(project.id, basemap_dates)
    
    return jsonify({
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "classes": project.classes
    }), 201

def initialize_training_polygon_sets(project_id, basemap_dates):
    for date in basemap_dates:
        training_set = TrainingPolygonSet(
            project_id=project_id,
            basemap_date=date,
            name=f"Training_Set_{date}",
            polygons={"type": "FeatureCollection", "features": []},
            feature_count=0,
            excluded=False
        )
        db.session.add(training_set)
    db.session.commit()

@celery.task
def download_quads_for_aoi(aoi_extent, basemap_dates):
    ## Assumes basemap_date is in the format 'YYYY-MM'
    logger.info(f"Starting quad download for AOI: {aoi_extent}")
    total_dates = len(basemap_dates)
    
    for index, date in enumerate(basemap_dates, start=1):
        try:
            logger.info(f"Downloading quads for date {date} ({index}/{total_dates})")
            quads = get_planet_quads(aoi_extent, date) 
            logger.info(f"Successfully downloaded {len(quads)} quads for date {date}")
        except Exception as e:
            logger.error(f"Error downloading quads for date {date}: {str(e)}")
    
    logger.info(f"Completed quad download for AOI: {aoi_extent}")


@app.route('/api/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    project = Project.query.get_or_404(project_id)
    
    project_data = {
        'id': project.id,
        'name': project.name,
        'description': project.description,
        'aoi': None,
        'classes': project.classes,
        'aoi_area_ha': project.aoi_area_ha
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
    
    if 'aoi' in data:
        project.aoi = from_shape(shape(data['aoi']), srid=4326)
        project.update_aoi_area()  # Update area when AOI changes
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

        ## If downloading the imagery in the background when the projetc AOI is created, use the code below
        # # Convert GeoJSON to shapely geometry
        geojson = data['aoi'] ## In web mercator projection
        shape = geometry.shape(geojson['geometry'])
        # aoi_extent = data['aoi_extent']
        # basemap_dates = data['basemap_dates']

        # # Trigger background download of imagery
        # download_quads_for_aoi.delay(aoi_extent, basemap_dates)
        
        # Convert shapely geometry to WKT
        wkt = shape.wkt
        
        # Create a PostGIS geometry from WKT
        project.aoi = from_shape(shape, srid=4326)  # Assuming WGS84 projection

        project.aoi_area_ha = shape.area / 10000  # Convert square meters to hectares

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
    excluded = data.get('excluded', False)  # Add this line


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
        feature_count=len(polygons['features']),
        excluded=excluded 
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
        'updated_at': s.updated_at.isoformat(),
        'excluded': s.excluded
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
    excluded = data.get('excluded')  # Add this line

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
        if excluded is not None:  # Add this block
            training_set.excluded = excluded

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
    
@app.route('/api/training_data_summary/<int:project_id>', methods=['GET'])
def get_training_data_summary(project_id):
    try:
        training_sets = TrainingPolygonSet.query.filter_by(project_id=project_id, excluded=False).filter(TrainingPolygonSet.feature_count > 0).all()
        
        summary = {
            'totalSets': len(training_sets),
            'classStats': {},
            'trainingSetDates': []
        }

        project = Project.query.get(project_id)
        class_names = [cls['name'] for cls in project.classes]

        for class_name in class_names:
            summary['classStats'][class_name] = {
                'featureCount': 0,
                'totalAreaHa': 0
            }

        # Create a transformer for area calculations
        transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

        for training_set in training_sets:
            summary['trainingSetDates'].append(training_set.basemap_date)
            for feature in training_set.polygons['features']:
                class_name = feature['properties']['classLabel']
                summary['classStats'][class_name]['featureCount'] += 1

                
                # Calculate area in hectares
                geom = shape(feature['geometry'])
                area_ha = geom.area / 10000  # Convert from square meters to hectares
                summary['classStats'][class_name]['totalAreaHa'] += area_ha

        # Round the area values to two decimal places
        for class_stats in summary['classStats'].values():
            class_stats['totalAreaHa'] = class_stats['totalAreaHa']

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
        'type': p.type,
        'basemap_date': p.basemap_date,
        'created_at': p.created_at.isoformat(),
        'file_path': p.file_path,
        'summary_statistics': p.summary_statistics
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


@app.route('/api/trained_models/<int:project_id>/metrics', methods=['GET'])
def get_model_metrics(project_id):
    try:
        model = TrainedModel.query.filter_by(project_id=project_id).first()
        if model:
            model_dict = model.to_dict()
            model_dict['created_at'] = model.created_at.isoformat()
            model_dict['updated_at'] = model.updated_at.isoformat() if model.updated_at else None
            return jsonify(model_dict)
        else:
            return jsonify({'error': 'No model found for this project'}), 404
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
    aoi_shape = data['aoiShape']
    aoi_extent = data['aoiExtent']
    aoi_extent_lat_lon = data['aoiExtentLatLon']
    model_description = data.get('modelDescription', '')
    split_method = data.get('splitMethod', 'feature')
    train_test_split = data.get('trainTestSplit', 0.2)
    basemap_dates_for_prediction = data.get('basemapDates', [])

    model_params = {
        'objective': 'multi:softmax',
        'n_estimators': data.get('n_estimators', 100),
        'max_depth': data.get('max_depth', 3),
        'learning_rate': data.get('learning_rate', 0.1),
        'min_child_weight': data.get('min_child_weight', 1),
        'gamma': data.get('gamma', 0),
        'colsample_bytree': data.get('colsample_bytree', 0.8),
        'subsample': data.get('subsample', 0.8),
        'sieve_size': data.get('sieve_size', 0)
    }

    
    try:
        # Fetch all training sets
        training_sets = TrainingPolygonSet.query.filter_by(project_id=project_id, excluded=False).filter(TrainingPolygonSet.feature_count > 0).all()
        if not training_sets:
            return jsonify({"error": "No training sets found for this project"}), 404

        # Get unique basemap dates
        unique_dates = set(ts.basemap_date for ts in training_sets)

        # Step 1: Get Planet quads
        update_progress(project_id, 0.1, "Fetching Planet quads")
        
        quads_by_date = {}
        for date in unique_dates:
            update_progress(project_id, 0.2, f"Fetching Planet quads for {date}")
            quads_by_date[date] = get_planet_quads(aoi_extent_lat_lon, date)

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

        # Step 4: Generate predictions
        update_progress(project_id, 0.7, "Generating predictions")

        # Get the latest trained model for the project
        model = TrainedModel.query.filter_by(project_id=project_id).order_by(TrainedModel.created_at.desc()).first()

        # Start predictions for all dates
        # Create a group of tasks to run in parallel
        tasks = [generate_prediction_for_date.s(model.id, project_id, aoi_shape, aoi_extent, aoi_extent_lat_lon, date) for date in basemap_dates_for_prediction]
        job = group(tasks)
        
        # Execute the group of tasks
        result = job.apply_async()

        total_tasks = len(basemap_dates_for_prediction)
        completed_tasks = 0

        while not result.ready():
            completed_tasks = sum(1 for r in result.results if r.ready())
            progress = completed_tasks / total_tasks
            update_progress(project_id, 0.7 + progress * .3, f"Predicted {completed_tasks}/{total_tasks} dates")
            time.sleep(5)  # Wait for 5 seconds before checking again

       # Wait for the main prediction task to complete
        result.get() 

        # Step 5: Return results
        update_progress(project_id, 1.0, "Training and prediction complete!")

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
    ## Assumes basemap_date is in the format 'YYYY-MM'
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




# @app.route('/api/predict_landcover', methods=['POST'])
# def predict_landcover():
#     data = request.json
#     project_id = data['projectId']
#     model_id = data['modelId']
#     basemap_date = data['basemapDate']
#     prediction_name = data['predictionName']
#     aoi_shape = data['aoiShape']
#     aoi_extent = data['aoiExtent']
#     aoi_extent_lat_lon = data['aoiExtentLatLon']


#     # Fetch the model
#     model = TrainedModel.query.get(model_id)
#     if not model:
#         return jsonify({"error": "Model not found"}), 404

#     # Fetch the quads for the AOI and basemap date
#     quads = get_planet_quads(aoi_extent_lat_lon, basemap_date)

#     # Perform the prediction
#     prediction_file = predict_landcover_aoi(model.id, quads, aoi_shape, project_id, basemap_date)

#     # Save prediction to database
#     prediction = Prediction(
#         project_id=project_id,
#         model_id=model.id,
#         file_path=prediction_file,
#         basemap_date=basemap_date,
#         name=prediction_name
#     )
#     db.session.add(prediction)
#     db.session.commit()

#     return jsonify({
#         "message": "Prediction completed",
#         "prediction_id": prediction.id,
#         "file_path": prediction.file_path
#     })


def predict_landcover_aoi(model_id, quads, aoi_shape, aoi_extent, project_id, basemap_date, session):
    
    model_record = session.query(TrainedModel).get(model_id)
    if model_record is None:
        raise ValueError("Model not found")

    if project_id is None:
        raise ValueError("Project ID is required")

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

        ## Extract and encode the month
        month = int(nearest_date.split('-')[1])
        encoded_month = month_encoder.transform([month])[0]

    else:
        encoded_date = date_encoder.transform([basemap_date])[0]
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
            unique_id = uuid.uuid4().hex
            temp_filename = f'temp_prediction_{unique_id}.tif'
            with rasterio.open(temp_filename, 'w', **meta) as tmp:
                tmp.write(prediction_map.astype(rasterio.uint8), 1)

            predicted_rasters.append(rasterio.open(temp_filename))
            temp_files.append(temp_filename)

    mosaic, out_transform = merge(predicted_rasters)

    # Get the sieve size from the model parameters
    sieve_size = model_record.model_parameters.get('sieve_size', 0)  # Default to 10 if not specified

    # Apply sieve filter only if sieve_size > 0
    if sieve_size > 0:
        sieved_mosaic = np.zeros_like(mosaic)
        for i in range(len(all_class_names)):
            # Create a binary mask for this class
            class_mask = (mosaic[0] == i).astype('uint8')
            # Apply sieve filter to this class
            sieved_class = sieve(class_mask, size=sieve_size)
            # Add back to the final mosaic
            sieved_mosaic[0][sieved_class == 1] = i
        
        mosaic = sieved_mosaic

    # Create merged metadata
    merged_meta = predicted_rasters[0].meta.copy()
    merged_meta.update({
        "driver": "GTiff",
        "height": mosaic.shape[1],
        "width": mosaic.shape[2],
        "transform": out_transform,
        "compress": 'lzw',
        "nodata": 255
    })

    # Create a temporary file for the merged raster
    with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp:
        temp_tif = tmp.name

    # Write the merged raster to the temporary file
    with rasterio.open(temp_tif, 'w', **merged_meta) as dst:
        dst.write(mosaic)

    # Clip the mosaic to the AOI
    # Use the AOI GeoJSON directly if it's already in the correct format
    if isinstance(aoi_shape, dict) and aoi_shape.get('type') == 'Polygon':
        aoi_geojson = aoi_shape
    else:
        # Convert to shapely geometry if it's not already a GeoJSON
        aoi_shape = shape(aoi_shape) if isinstance(aoi_shape, dict) else aoi_shape
        aoi_geojson = mapping(aoi_shape)

    # Clip the mosaic to the AOI
    with rasterio.open(temp_tif) as src:

        clipped_mosaic, clipped_transform = mask(
            src,
            shapes=[aoi_geojson],
            crop=True,
            filled=True,
            nodata=255  # Use 255 as the nodata value
        )
    
    logger.info(f"Merged raster shape: {mosaic.shape}")
    logger.info(f"Merged raster transform: {out_transform}")

    # Update merged_meta with clipped raster information
    merged_meta.update({
        "height": clipped_mosaic.shape[1],
        "width": clipped_mosaic.shape[2],
        "transform": clipped_transform,
    })
    
    # Create the final output file
    unique_id = uuid.uuid4().hex
    output_file = f"./predictions/landcover_prediction_project{project_id}_{basemap_date}_{unique_id}.tif"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Write the final raster
    with rasterio.open(output_file, "w", **merged_meta) as dest:
        dest.write(clipped_mosaic[0], 1)  # Write the first (and only) band

    # Clean up the temporary file
    os.unlink(temp_tif)
    # Clean up temporary files
    for raster in predicted_rasters:
        raster.close()
    for temp_file in temp_files:
        os.remove(temp_file)

    logger.debug(f"Final prediction file: {output_file}")

    return output_file


@app.route('/api/prediction_status/<task_id>', methods=['GET'])
def get_prediction_status(task_id):
    task = AsyncResult(task_id)
    if task.state == 'PROGRESS':
        # This is the parent task
        group_id = task.info.get('group_id')
        total = task.info.get('total', 0)
        if group_id:
            group_result = AsyncResult(group_id)
            completed_tasks = [r for r in group_result.results if r.ready()]
            current = len(completed_tasks)
            successful = sum(1 for r in completed_tasks if r.result and r.result.get('status') == 'success')
            failed = sum(1 for r in completed_tasks if r.result and r.result.get('status') == 'error')
            response = {
                'state': 'PROGRESS',
                'current': current,
                'total': total,
                'successful': successful,
                'failed': failed,
                'status': f'Processing: {current}/{total} completed'
            }
        else:
            response = {
                'state': 'PROGRESS',
                'current': 0,
                'total': total,
                'status': 'Initializing...'
            }
    elif task.state == 'SUCCESS':
        response = {
            'state': 'SUCCESS',
            'current': task.result.get('total', 0),
            'total': task.result.get('total', 0),
            'status': 'All predictions completed'
        }
    else:
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': str(task.info)
        }
    return jsonify(response)


@celery.task
def generate_prediction_for_date(model_id, project_id, aoi_shape, aoi_extent, aoi_extent_lat_lon, date):
    try:
        logger.info(f"Generating prediction for date {date}")
        prediction = generate_prediction(model_id, project_id, aoi_shape, aoi_extent, aoi_extent_lat_lon, date)
        logger.info(f"Successfully generated prediction for date {date}")
        return prediction   
    except Exception as e:
        logger.error(f"Error generating prediction for date {date}: {str(e)}")
        return None



@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

def generate_prediction(model_id, project_id, aoi_shape, aoi_extent, aoi_extent_lat_lon, date):
    try:
        # Get Planet quads for the date
        quads = get_planet_quads(aoi_extent_lat_lon, date)
       
        with session_scope() as session:

             # Generate prediction
            new_prediction_file = predict_landcover_aoi(model_id, quads, aoi_shape, aoi_extent, project_id, date, session)

            # Check for existing prediction
            existing_prediction = session.query(Prediction).filter_by(
                project_id=project_id,
                basemap_date=date
            ).first()

            if existing_prediction:

                logger.debug(f"Existing prediction found for date {date}")
                logger.debug(f"Deleting old prediction file {existing_prediction.file_path}")

                # Delete the old file
                if os.path.exists(existing_prediction.file_path):
                    os.remove(existing_prediction.file_path)
                
                # Update existing prediction
                logger.debug(f"Updating existing prediction for date {date}")
                existing_prediction.model_id = model_id
                existing_prediction.file_path = new_prediction_file
                existing_prediction.name = f"Prediction_{date}"
                existing_prediction.created_at = datetime.utcnow()
                prediction = existing_prediction
            else:
                # Create new prediction
                logger.debug(f"Creating new prediction for date {date}")
                prediction = Prediction(
                    project_id=project_id,
                    model_id=model_id,
                    type='land_cover',
                    file_path=new_prediction_file,
                    basemap_date=date,
                    name=f"Prediction_{date}"
                )
                session.add(prediction)


            # Calculate and store summary statistics in dadtabase
            summary_stats = calculate_summary_statistics(prediction)
            if summary_stats:
                try:
                    json_stats = json.dumps(summary_stats)
                    logger.debug(f"Serialized summary stats: {json_stats}")
                    prediction.summary_statistics = json.loads(json_stats)
                    session.commit()
                    logger.info(f"Successfully saved summary statistics for prediction {prediction.id}")
                except json.JSONDecodeError as e:
                    logger.error(f"Error serializing summary stats: {str(e)}")
                except SQLAlchemyError as e:
                    session.rollback()
                    logger.error(f"Error saving summary statistics: {str(e)}")


            # Flush to ensure the prediction gets an ID if it's new
            session.flush()

            # Return a dictionary representation of the prediction
            return {
                'id': prediction.id,
                'file_path': prediction.file_path,
                'basemap_date': prediction.basemap_date,
                'name': prediction.name,
                'type': prediction.type,
                'summary_statistics': prediction.summary_statistics
            }

    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in generate_prediction: {str(e)}")
        raise
    except Exception as e:
        current_app.logger.error(f"Error in generate_prediction: {str(e)}")
        raise


def calculate_summary_statistics(prediction):
    try:
        with rasterio.open(prediction.file_path) as src:

            raster_data = src.read(1)  # Assuming single band raster
            pixel_area_ha = abs(src.transform[0] * src.transform[4]) / 10000  # Convert to hectares
            
            # Get unique class values and their counts
            unique, counts = np.unique(raster_data, return_counts=True)

            # Calculate total area excluding nodata pixels
            valid_pixels = raster_data[raster_data != 255]
            total_area = float(valid_pixels.size * pixel_area_ha)

            # Get class names from the project
            project = Project.query.get(prediction.project_id)
            class_names = {i: cls['name'] for i, cls in enumerate(project.classes)}
            
            # Calculate statistics
            class_stats = {}
            for value, count in zip(unique, counts):
                if value in class_names:
                    area = count * pixel_area_ha
                    percentage = (area / total_area) * 100
                    class_stats[int(value)] = { 'area_ha': area, 'percentage': percentage}

                    logger.debug(f"Class {value} has area {area} and percentage {percentage}")
                    logger.debug(print(class_stats))
            
            # Prepare the result
            result = {
                'prediction_name': prediction.name,
                'prediction_date': prediction.basemap_date,
                'type': prediction.type,
                'total_area_ha': total_area,
                'class_statistics': class_stats
            }

            return result
    except Exception as e:
        logger.error(f"Error calculating summary statistics: {str(e)}")
        return None


## Analysis endpoints
@app.route('/api/analysis/summary/<int:prediction_id>', methods=['GET'])
def get_summary_statistics(prediction_id):
    prediction = Prediction.query.get_or_404(prediction_id)
    if prediction.summary_statistics:
        return jsonify(prediction.summary_statistics)
    else:
        return jsonify({'error': 'Summary statistics not available'}), 404


@app.route('/api/analysis/change/', methods=['POST'])
def  analyze_change():
    # try:
        data = request.json
        prediction1_id = data.get('prediction1_id')
        prediction2_id = data.get('prediction2_id')
        aoi_shape = data.get('aoi_shape')

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

        with rasterio.open(prediction1.file_path) as src1, rasterio.open(prediction2.file_path) as src2:
            if src1.bounds != src2.bounds or src1.res != src2.res:
                return jsonify({"error": "Predictions have different extents or resolutions"}), 400

            data1 = src1.read(1)
            data2 = src2.read(1)

            pixel_area_ha = abs(src1.transform[0] * src1.transform[4]) / 10000  # Area in hectares

            # Calculate areas for each class in both predictions
            areas1 = {all_class_names[i]: np.sum(data1 == i) * pixel_area_ha for i in range(len(all_class_names))}
            areas2 = {all_class_names[i]: np.sum(data2 == i) * pixel_area_ha for i in range(len(all_class_names))}

            # Calculate changes
            changes = {name: areas2[name] - areas1[name] for name in all_class_names}

            # Calculate percentages
            # Calculate total area excluding nodata pixels
            valid_pixels = data1[data1 != 255]
            total_area = float(valid_pixels.size * pixel_area_ha)
            percentages1 = {name: (area / total_area) * 100 for name, area in areas1.items()}
            percentages2 = {name: (area / total_area) * 100 for name, area in areas2.items()}

            # Calculate total changed area
            total_change = sum(abs(change) for change in changes.values()) / 2  # Divide by 2 to avoid double counting

            # Generate confusion matrix
            cm = confusion_matrix(data1.flatten(), data2.flatten(), labels=range(len(all_class_names)))
            cm_percent = cm / cm.sum() * 100

            # # Generate deforestation raster

            forest_class = all_class_names.index('Forest')
            cloud_shadow_classes = [all_class_names.index(cls) for cls in ['Cloud', 'Shadow'] if cls in all_class_names]

            # Initialize deforestation array
            deforestation = np.full_like(data1, 255, dtype=np.uint8)  # Start with all no data

            # Mark areas that are valid (not cloud/shadow) in both periods
            valid_mask = ~np.isin(data1, cloud_shadow_classes) & ~np.isin(data2, cloud_shadow_classes)

            # Within valid areas, mark no deforestation (0) where it's not forest in first period or where it remains forest
            deforestation[valid_mask & ((data1 != forest_class) | (data2 == forest_class))] = 0

            # Within valid areas, mark deforestation (1) where it changes from forest to non-forest
            deforestation[valid_mask & (data1 == forest_class) & (data2 != forest_class)] = 1
            
            # Optional: Apply sieve filter to remove small isolated pixels
            deforestation = sieve(deforestation, size=10)

            # Create a temporary file for the deforestation raster
            with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp:
                temp_tif = tmp.name

            # Write the merged raster to the temporary file
            with rasterio.open(temp_tif, 'w', **src1.profile) as dst:
                dst.write(deforestation, 1)

            # Create merged metadata
            meta = src1.meta.copy()
            meta.update({
                "driver": "GTiff",
                "compress": 'lzw',
                "nodata": 255
            })

            # Clip the deforestation raster to the AOI
            # Use the AOI GeoJSON directly if it's already in the correct format
            if isinstance(aoi_shape, dict) and aoi_shape.get('type') == 'Polygon':
                aoi_geojson = aoi_shape
            else:
                # Convert to shapely geometry if it's not already a GeoJSON
                aoi_shape = shape(aoi_shape) if isinstance(aoi_shape, dict) else aoi_shape
                aoi_geojson = mapping(aoi_shape)

            # Clip the mosaic to the AOI
            with rasterio.open(temp_tif) as src:

                clipped_deforestation, clipped_transform = mask(
                    src,
                    shapes=[aoi_geojson],
                    crop=True,
                    filled=True,
                    nodata=255  # Use 255 as the nodata value
                )
            
            # Save deforestation raster
            deforestation_dir = './deforestation'
            if not os.path.exists(deforestation_dir):
                os.makedirs(deforestation_dir)

            deforestation_path = f"{deforestation_dir}/defor_project{prediction1.project_id}_{prediction1.basemap_date}_{prediction2.basemap_date}_{uuid.uuid4().hex}.tif"
            with rasterio.open(deforestation_path, 'w', **meta) as dst:
                dst.write(clipped_deforestation[0], 1)

            # Calculate deforestation statistics
            total_forest_pixels = np.sum(data1 == forest_class)
            deforested_pixels = np.sum(deforestation == 1)
            deforestation_rate = (deforested_pixels / total_forest_pixels) * 100 if total_forest_pixels > 0 else 0


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
                "class_names": all_class_names,
                "deforestation_raster_path": deforestation_path,
                "deforestation_rate": float(deforestation_rate),
                "deforested_area_ha": float(deforested_pixels * pixel_area_ha),
                "total_forest_area_ha": float(total_forest_pixels * pixel_area_ha)
            }



            # Check for existing prediction
            existing_prediction = Prediction.query.filter_by(
                project_id=prediction1.project_id,
                name=f"Deforestation_{prediction1.basemap_date}_to_{prediction2.basemap_date}",
            ).first()

            if existing_prediction:
                logger.debug(f"Deleting old prediction file {existing_prediction.file_path}")

                # Delete the old file
                if os.path.exists(existing_prediction.file_path):
                    os.remove(existing_prediction.file_path)
                
                # Update existing prediction
                existing_prediction.model_id = prediction1.model_id
                existing_prediction.file_path = deforestation_path
                existing_prediction.name = f"Deforestation_{prediction1.basemap_date}_to_{prediction2.basemap_date}"
                existing_prediction.created_at = datetime.utcnow()
                existing_prediction.summary_statistic = results
                deforestation_prediction = existing_prediction
            else:
                # Create a new Prediction record for the deforestation analysis
                deforestation_prediction = Prediction(
                    project_id=prediction1.project_id,  # Assuming both predictions are from the same project
                    model_id=prediction1.model_id,  # Use the model from the first prediction
                    name=f"Deforestation_{prediction1.basemap_date}_to_{prediction2.basemap_date}",
                    file_path=deforestation_path,
                    created_at=datetime.utcnow(),
                    summary_statistics=results,
                    type='deforestation'
                )
       
            db.session.add(deforestation_prediction)
            db.session.commit()

            # Add the new prediction ID to the results
            results["deforestation_prediction_id"] = deforestation_prediction.id

            return jsonify(results)

    # except Exception as e:
    #     db.session.rollback()
    #     logger.error(f"Error in analyze_change: {str(e)}")
    #     return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<int:project_id>/training-sets/<int:set_id>/excluded', methods=['PUT'])
def update_training_set_excluded(project_id, set_id):
    try:
        data = request.json
        excluded = data.get('excluded', False)
        training_set = TrainingPolygonSet.query.filter_by(id=set_id, project_id=project_id).first_or_404()
        training_set.excluded = excluded
        db.session.commit()
        
        return jsonify({'message': 'Training set excluded status updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    

@app.route('/api/hotspots/<int:hotspot_id>/verify', methods=['PUT', 'OPTIONS'])
@cross_origin()
def verify_hotspot(hotspot_id):
    print(f"=== VERIFY HOTSPOT ENDPOINT ===")
    print(f"Method: {request.method}")
    print(f"Hotspot ID: {hotspot_id}")
    print(f"Request JSON: {request.json}")
    print(f"Headers: {dict(request.headers)}")
    
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        status = request.json.get('status')
        print(f"Processing status: {status}")
        
        if status not in ['verified', 'rejected', 'unsure']:
            print(f"Invalid status: {status}")
            return jsonify({"error": "Invalid status"}), 400
            
        hotspot = DeforestationHotspot.query.get_or_404(hotspot_id)
        print(f"Found hotspot: {hotspot.id}")
        
        hotspot.verification_status = status
        db.session.commit()
        print("Successfully updated hotspot")
        
        return jsonify({"message": "Hotspot verification updated"})
    except Exception as e:
        print(f"Error in verify_hotspot: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Add this right after your route definition
# print("=== DEBUG ===")
# print("All registered routes:")
# for rule in app.url_map.iter_rules():
#     print(f"{rule.endpoint}: {rule.methods} {rule}")
# print("============")

@app.route('/api/analysis/deforestation_hotspots/<int:prediction_id>', methods=['GET'])
def get_deforestation_hotspots(prediction_id):
    try:
        prediction = Prediction.query.get_or_404(prediction_id)
        min_area_ha = float(request.args.get('min_area_ha', 1.0))
        source = request.args.get('source', 'all')  # 'all', 'ml', or 'gfw'

        # Query existing hotspots with source filter
        query = DeforestationHotspot.query.filter_by(prediction_id=prediction_id)
        if source != 'all':
            query = query.filter_by(source=source)
        existing_hotspots = query.all()
        
        features_list = []
        
        if existing_hotspots:
            # Convert existing hotspots to GeoJSON
            for hotspot in existing_hotspots:
                properties = {
                    "id": str(hotspot.id),
                    "area_ha": round(hotspot.area_ha, 2),
                    "perimeter_m": round(hotspot.perimeter_m, 2),
                    "compactness": round(hotspot.compactness, 3),
                    "edge_density": round(hotspot.edge_density, 3),
                    "verification_status": hotspot.verification_status,
                    "source": hotspot.source
                }
                
                if hotspot.source == 'gfw':
                    properties["confidence"] = hotspot.confidence
                
                feature = {
                    "type": "Feature",
                    "id": str(hotspot.id),
                    "geometry": hotspot.geometry,
                    "properties": properties
                }
                features_list.append(feature)
        else:
            # Generate new hotspots if none exist
            # First generate ML hotspots if requested
            if source in ['all', 'ml']:
                with rasterio.open(prediction.file_path) as src:
                    # Read the deforestation raster (1 = deforestation, 0 = no deforestation, 255 = nodata)
                    defor_data = src.read(1)
                    
                    # Create mask of deforested pixels
                    defor_mask = defor_data == 1
                    
                    # Get pixel area in hectares
                    pixel_area_ha = abs(src.transform[0] * src.transform[4]) / 10000

                    # Get shapes of connected components
                    shapes = features.shapes(
                        defor_data, 
                        mask=defor_mask,
                        transform=src.transform
                    )
                    
                    for idx, (geom, value) in enumerate(shapes):
                        if value == 1:
                            polygon = shape(geom)
                            area_ha = float(polygon.area / 10000)
                            perimeter_m = float(polygon.length)
                            
                            # Calculate centroid
                            centroid = polygon.centroid
                            # Calculate edge density
                            edge_density = float(perimeter_m / (area_ha * 10000))  # m/m²
                            compactness = float(4 * math.pi * polygon.area / (perimeter_m ** 2))  # Convert to float
                            # Store geometry as GeoJSON
                            geojson_geometry = mapping(polygon)
                            
                            # Create database record
                            hotspot = DeforestationHotspot(
                                prediction_id=prediction_id,
                                geometry=geojson_geometry,
                                area_ha=area_ha,
                                perimeter_m=perimeter_m,
                                compactness=compactness,
                                edge_density=edge_density,
                                centroid_lon=float(centroid.x),
                                centroid_lat=float(centroid.y),
                                source='ml'
                            )
                            db.session.add(hotspot)
                            
                            # Create GeoJSON feature
                            feature = {
                                "type": "Feature",
                                "id": str(hotspot.id),
                                "geometry": geojson_geometry,
                                "properties": {
                                    "area_ha": round(area_ha, 2),
                                    "perimeter_m": round(perimeter_m, 2),
                                    "compactness": round(hotspot.compactness, 3),
                                    "edge_density": round(edge_density, 3),
                                    "verification_status": None,
                                    "source": "ml"
                                }
                            }
                            features_list.append(feature)

            # Then generate GFW hotspots if requested
            if source in ['all', 'gfw']:
                # Get project AOI
                project = Project.query.get(prediction.project_id)
                aoi_shape = shape(json.loads(db.session.scalar(project.aoi.ST_AsGeoJSON())))
                
                # Process GFW alerts
                gfw_hotspots = process_gfw_alerts(prediction_id, aoi_shape)
                
                # Add GFW hotspots to features list
                for hotspot in gfw_hotspots:
                    properties = {
                        "id": str(hotspot.id),
                        "area_ha": round(hotspot.area_ha, 2),
                        "perimeter_m": round(hotspot.perimeter_m, 2),
                        "compactness": round(hotspot.compactness, 3),
                        "edge_density": round(hotspot.edge_density, 3),
                        "verification_status": hotspot.verification_status,
                        "source": 'gfw',
                        "confidence": hotspot.confidence
                    }
                    
                    feature = {
                        "type": "Feature",
                        "id": str(hotspot.id),
                        "geometry": hotspot.geometry,
                        "properties": properties
                    }
                    features_list.append(feature)
                
                db.session.commit()

                # Update features with database IDs after commit
                for idx, feature in enumerate(features_list):
                    feature["id"] = str(hotspot.id)
                    feature["properties"]["id"] = str(hotspot.id)
        
        # Filter hotspots by minimum area
        features_list = [f for f in features_list if f["properties"]["area_ha"] >= min_area_ha]

        # Filter hotspots by source
        if source != 'all':
            features_list = [f for f in features_list if f["properties"]["source"] == source]
        
        # Sort features by area
        features_list.sort(key=lambda x: x["properties"]["area_ha"], reverse=True)
        
        # Calculate statistics by source
        ml_hotspots = [f for f in features_list if f["properties"]["source"] == "ml"]
        gfw_hotspots = [f for f in features_list if f["properties"]["source"] == "gfw"]
        
        metadata = {
            "total_hotspots": len(features_list),
            "min_area_ha": min_area_ha,
            "total_area_ha": sum(f["properties"]["area_ha"] for f in features_list),
            "prediction_id": prediction_id,
            "by_source": {
                "ml": {
                    "count": len(ml_hotspots),
                    "total_area_ha": sum(f["properties"]["area_ha"] for f in ml_hotspots)
                },
                "gfw": {
                    "count": len(gfw_hotspots),
                    "total_area_ha": sum(f["properties"]["area_ha"] for f in gfw_hotspots)
                }
            }
        }
        
        return jsonify({
            "type": "FeatureCollection",
            "features": features_list,
            "metadata": metadata
        })
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in get_deforestation_hotspots: {str(e)}")
        return jsonify({"error": str(e)}), 500

def download_and_merge_gfw_alerts():
    """Downloads and merges GFW alert tiles, returns path to merged raster"""
    
    logger.info("Starting GFW alert download and merge process")
    
    # This is only for Ecuador - store as tuples of (url, filename)
    GFW_TILES = [
        ("https://data-api.globalforestwatch.org/dataset/gfw_integrated_alerts/latest/download/geotiff?grid=10/100000&tile_id=10N_080W&pixel_meaning=date_conf&x-api-key=2d60cd88-8348-4c0f-a6d5-bd9adb585a8c", "10N_080W.tif"),
        ("https://data-api.globalforestwatch.org/dataset/gfw_integrated_alerts/latest/download/geotiff?grid=10/100000&tile_id=00N_080W&pixel_meaning=date_conf&x-api-key=2d60cd88-8348-4c0f-a6d5-bd9adb585a8c", "00N_080W.tif"),
        ("https://data-api.globalforestwatch.org/dataset/gfw_integrated_alerts/latest/download/geotiff?grid=10/100000&tile_id=00N_090W&pixel_meaning=date_conf&x-api-key=2d60cd88-8348-4c0f-a6d5-bd9adb585a8c", "00N_090W.tif"),
        ("https://data-api.globalforestwatch.org/dataset/gfw_integrated_alerts/latest/download/geotiff?grid=10/100000&tile_id=10N_090W&pixel_meaning=date_conf&x-api-key=2d60cd88-8348-4c0f-a6d5-bd9adb585a8c", "10N_090W.tif")
    ]
    
    # Create directory for GFW data if it doesn't exist
    gfw_data_dir = './gfw_alerts'
    os.makedirs(gfw_data_dir, exist_ok=True)
    
    # Clean up old merged files
    cleanup_old_merged_files(gfw_data_dir)
    
    # Download and save tiles
    tile_paths = []
    total_size = 0
    for url, filename in GFW_TILES:
        try:
            logger.info(f"Downloading GFW tile {filename} from {url}")
            response = requests.get(url, stream=True)  # Stream the response
            response.raise_for_status()
            
            tile_path = os.path.join(gfw_data_dir, filename)
            
            # Write in chunks to manage memory
            with open(tile_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            size_mb = os.path.getsize(tile_path) / (1024 * 1024)
            total_size += size_mb
            tile_paths.append(tile_path)
            logger.info(f"Successfully saved GFW tile {filename} ({size_mb:.1f} MB)")
            
        except Exception as e:
            logger.error(f"Error downloading GFW tile {filename}: {str(e)}")
            raise
    
    logger.info(f"Total download size: {total_size:.1f} MB")
    
    # Merge tiles with memory management
    try:
        logger.info("Starting tile merge process")
        
        # Get metadata and bounds from all files first
        src_files = [rasterio.open(path) for path in tile_paths]
        
        # Calculate overall bounds
        dest_width = max(src.width for src in src_files)
        dest_height = max(src.height for src in src_files)
        
        # Get metadata from first raster
        out_meta = src_files[0].meta.copy()
        out_meta.update({
            "height": dest_height,
            "width": dest_width,
            "compress": 'lzw',  # Add compression
            "tiled": True,      # Enable tiling
            "blockxsize": 256,  # Set tile size
            "blockysize": 256
        })
        
        # Close the source files temporarily
        for src in src_files:
            src.close()
        
        # Create the destination file
        merged_path = os.path.join(gfw_data_dir, f'gfw_merged_{datetime.now().strftime("%Y%m%d")}.tif')
        
        with rasterio.open(merged_path, 'w', **out_meta) as dest:
            # Process each source file individually
            for path in tile_paths:
                with rasterio.open(path) as src:
                    # Read and write in windows
                    window_size = 1024
                    for i in range(0, src.height, window_size):
                        for j in range(0, src.width, window_size):
                            window = Window(j, i, 
                                         min(window_size, src.width - j),
                                         min(window_size, src.height - i))
                            data = src.read(1, window=window)
                            dest.write(data, 1, window=window)
        
        merged_size_mb = os.path.getsize(merged_path) / (1024 * 1024)
        logger.info(f"Successfully saved merged file ({merged_size_mb:.1f} MB) to {merged_path}")
        
        return merged_path
        
    except Exception as e:
        logger.error(f"Error merging GFW tiles: {str(e)}")
        raise
    finally:
        # Clean up individual tiles
        for path in tile_paths:
            try:
                os.remove(path)
                logger.debug(f"Cleaned up temporary tile: {path}")
            except Exception as e:
                logger.warning(f"Error removing temporary tile {path}: {str(e)}")

def cleanup_old_merged_files(directory, keep_latest=True):
    """Clean up old merged GFW alert files, optionally keeping the latest one"""
    try:
        merged_files = [f for f in os.listdir(directory) if f.startswith('gfw_merged_')]
        merged_files.sort(reverse=True)  # Sort by date (newest first)
        
        # Keep the latest file if requested
        if keep_latest and merged_files:
            merged_files = merged_files[1:]
        
        # Delete old files
        for file in merged_files:
            file_path = os.path.join(directory, file)
            try:
                os.remove(file_path)
                logger.info(f"Deleted old merged file: {file}")
            except Exception as e:
                logger.warning(f"Error deleting old merged file {file}: {str(e)}")
    except Exception as e:
        logger.error(f"Error during cleanup of old merged files: {str(e)}")

def should_update_merged_file(file_path, max_age_days=30):
    """Check if merged file should be updated based on age"""
    try:
        if not os.path.exists(file_path):
            return True
            
        file_date = datetime.strptime(os.path.basename(file_path).split('_')[2].split('.')[0], '%Y%m%d')
        age = datetime.now() - file_date
        
        return age.days >= max_age_days
    except Exception as e:
        logger.warning(f"Error checking file age, will update: {str(e)}")
        return True

def decode_gfw_date(encoded_value):
    """Decode GFW alert value into date and confidence"""
    if encoded_value == 0:
        return None, None
        
    # Convert to string for easier processing
    encoded_str = str(encoded_value)
    
    # Get confidence level from first digit
    confidence = int(encoded_str[0])
    
    # Get days since Dec 31, 2014
    days = int(encoded_str[1:])
    
    # Calculate date
    base_date = datetime(2014, 12, 31)
    alert_date = base_date + timedelta(days=days)

    logger.info(f"Alert date: {alert_date} - str was: {encoded_str}")
    
    return alert_date, confidence

def process_gfw_alerts(prediction_id, aoi_shape):
    """Process GFW alerts for a given prediction's time period"""
    try:
        logger.info(f"Starting GFW alert processing for prediction {prediction_id}")
        
        # Get prediction details
        prediction = Prediction.query.get_or_404(prediction_id)
        
        # Get date range from prediction
        start_date = datetime.strptime(prediction.summary_statistics['prediction1_date'], '%Y-%m')
        end_date = datetime.strptime(prediction.summary_statistics['prediction2_date'], '%Y-%m')
        logger.info(f"Processing alerts between {start_date} and {end_date}")

        # Reproject AOI from Web Mercator (EPSG:3857) to WGS84 (EPSG:4326)
        project = Transformer.from_crs('EPSG:3857', 'EPSG:4326', always_xy=True).transform
        aoi_shape_4326 = transform(project, aoi_shape)
        
        # GFW tiles for Ecuador
        GFW_TILES = [
            ("https://data-api.globalforestwatch.org/dataset/gfw_integrated_alerts/latest/download/geotiff?grid=10/100000&tile_id=10N_080W&pixel_meaning=date_conf&x-api-key=2d60cd88-8348-4c0f-a6d5-bd9adb585a8c", "10N_080W.tif"),
            ("https://data-api.globalforestwatch.org/dataset/gfw_integrated_alerts/latest/download/geotiff?grid=10/100000&tile_id=00N_080W&pixel_meaning=date_conf&x-api-key=2d60cd88-8348-4c0f-a6d5-bd9adb585a8c", "00N_080W.tif"),
            ("https://data-api.globalforestwatch.org/dataset/gfw_integrated_alerts/latest/download/geotiff?grid=10/100000&tile_id=00N_090W&pixel_meaning=date_conf&x-api-key=2d60cd88-8348-4c0f-a6d5-bd9adb585a8c", "00N_090W.tif"),
            ("https://data-api.globalforestwatch.org/dataset/gfw_integrated_alerts/latest/download/geotiff?grid=10/100000&tile_id=10N_090W&pixel_meaning=date_conf&x-api-key=2d60cd88-8348-4c0f-a6d5-bd9adb585a8c", "10N_090W.tif")
        ]

        gfw_data_dir = './gfw_alerts'
        os.makedirs(gfw_data_dir, exist_ok=True)

        features_list = []
        
        # Process each tile individually
        for url, filename in GFW_TILES:
            
            # Add date to filename (before extension)
            name, ext = os.path.splitext(filename)
            dated_filename = f"{name}_{datetime.now().strftime('%Y%m%d')}{ext}"
            tile_path = os.path.join(gfw_data_dir, dated_filename)
            
            # Download if doesn't exist or is old
            if not os.path.exists(tile_path) or should_update_merged_file(tile_path):
                logger.info(f"Downloading tile {filename}")
                response = requests.get(url, stream=True)
                response.raise_for_status()
                
                with open(tile_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            
            # Process the tile
            with rasterio.open(tile_path) as src:
                logger.info(f"Processing tile {filename}")
                logger.info(f"Tile bounds: {src.bounds}")
                
                # Check if tile intersects with AOI
                tile_bounds = box(*src.bounds)

                if not tile_bounds.intersects(aoi_shape_4326):
                    logger.info(f"Tile {filename} does not intersect with AOI, skipping")
                    continue
                
                try:
                    clipped_data, clipped_transform = mask(src, [aoi_shape_4326], crop=True)

                    if np.sum(clipped_data) == 0:
                        logger.warning(f"No data found in clipped tile {filename}")
                    
                    # Create alert mask for this tile
                    alert_mask = np.zeros_like(clipped_data[0], dtype=bool)
                    confidence_data = np.zeros_like(clipped_data[0], dtype=np.uint8)
                    
                    # Process each pixel
                    for idx in np.ndindex(clipped_data[0].shape):
                        value = clipped_data[0][idx]
                        if value > 0:  # Skip nodata
                            alert_date, confidence = decode_gfw_date(value)
                            if alert_date and start_date <= alert_date <= end_date:
                                alert_mask[idx] = True
                                confidence_data[idx] = confidence

                    # Get shapes from this tile
                    shapes = features.shapes(
                        alert_mask.astype(np.uint8),
                        mask=alert_mask,
                        transform=clipped_transform
                    )
                    
                    # Process shapes from this tile
                    for geom, value in shapes:
                        if value == 1:
                            polygon = shape(geom)

                            # Project to Web Mercator
                            project = Transformer.from_crs('EPSG:4326', 'EPSG:3857', always_xy=True).transform
                            polygon_3857 = transform(project, polygon)
                            
                            # Calculate area and other metrics in meters
                            area_ha = polygon_3857.area / 10000
                            
                            # Create hotspot record using projected geometry
                            hotspot = DeforestationHotspot(
                                prediction_id=prediction_id,
                                geometry=mapping(polygon_3857),  # Store in Web Mercator
                                area_ha=float(area_ha),
                                perimeter_m=float(polygon_3857.length),
                                compactness=float(4 * math.pi * polygon_3857.area / (polygon_3857.length ** 2)),
                                edge_density=float(polygon_3857.length / (area_ha * 10000)),
                                centroid_lon=float(polygon.centroid.x),  # Store centroids in lat/long for convenience
                                centroid_lat=float(polygon.centroid.y),
                                source='gfw',
                                confidence=int(np.mean(confidence_data[features.rasterize(
                                    [(geom, 1)],
                                    out_shape=alert_mask.shape,
                                    transform=clipped_transform
                                ) == 1]))
                            )
                                
                            db.session.add(hotspot)
                            features_list.append(hotspot)
                
                except Exception as e:
                    logger.error(f"Error processing tile {filename}: {str(e)}")
                    continue
        
        if features_list:
            db.session.commit()
            logger.info(f"Successfully processed {len(features_list)} hotspots from GFW alerts")
        else:
            logger.warning("No valid hotspots found in GFW alerts")
            
        return features_list
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing GFW alerts: {str(e)}")
        raise


if __name__ == '__main__':
    logger.info("Starting Flask application")

    print("Registered routes:")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule.methods} {rule}")
    app.run(debug=True)






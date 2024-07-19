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
    training_polygon_sets = db.relationship("TrainingPolygonSet", back_populates="project")
    trained_models = db.relationship("TrainedModel", back_populates="project")
    predictions = db.relationship('Prediction', back_populates='project')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            # 'aoi': db.session.scalar(self.aoi.ST_AsGeoJSON()),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class TrainingPolygonSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    basemap_date = db.Column(db.String(7), nullable=False)  # Store as 'YYYY-MM'
    polygons = db.Column(JSONB)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    __table_args__ = (db.UniqueConstraint('project_id', 'basemap_date', name='uq_project_basemap_date'),)

    project = db.relationship("Project", back_populates="training_polygon_sets")
    trained_models = db.relationship("TrainedModel", back_populates="training_polygon_set")


class Raster(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    filepath = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(200))

class PixelDataset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    raster_id = db.Column(db.Integer, db.ForeignKey('raster.id'))
    file_path = db.Column(db.String(255))
    num_pixels = db.Column(db.Integer)
    class_distribution = db.Column(db.String)  # JSON string of class counts


class TrainedModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    training_polygon_set_id = db.Column(db.Integer, db.ForeignKey('training_polygon_set.id'), nullable=False)
    basemap_date = db.Column(db.String(7), nullable=False)  # Store as 'YYYY-MM'
    accuracy = db.Column(db.Float)
    file_path = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    parameters = db.Column(db.JSON)  # Store model parameters as JSON
    predictions = db.relationship('Prediction', back_populates='model')

    project = db.relationship("Project", back_populates="trained_models")
    training_polygon_set = db.relationship("TrainingPolygonSet", back_populates="trained_models")

    @classmethod
    def save_model(cls, model, name, project_id, training_polygon_set_id, basemap_date, accuracy, parameters):
        model_dir = './trained_models'
        os.makedirs(model_dir, exist_ok=True)
        file_name = f"{name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.joblib"
        file_path = os.path.join(model_dir, file_name)
        
        joblib.dump(model, file_path)
        
        new_model = cls(
            name=name,
            project_id=project_id,
            training_polygon_set_id=training_polygon_set_id,
            basemap_date=basemap_date,
            accuracy=accuracy,
            file_path=file_path,
            parameters=parameters
        )
        db.session.add(new_model)
        db.session.commit()
        return new_model

    @classmethod
    def load_model(cls, model_id):
        model_record = cls.query.get(model_id)
        if model_record:
            return joblib.load(model_record.file_path)
        return None

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'project_id': self.project_id,
            'training_polygon_set_id': self.training_polygon_set_id,
            'basemap_date': self.basemap_date,
            'accuracy': self.accuracy,
            'created_at': self.created_at.isoformat(),
            'parameters': self.parameters
        }


class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    model_id = db.Column(db.Integer, db.ForeignKey('trained_model.id'), nullable=False)
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

# Serve static files from the 'data' directory
@app.route('/rasters/<path:filename>')
def upload_files(filename):
    return send_from_directory('rasters', filename)

# Serve static files from the 'predictions' directory
@app.route('/predictions/<path:filename>')
def prediction_files(filename):
    return send_from_directory('predictions', filename)


# Project routes
@app.route('/api/projects', methods=['POST'])
def create_project():
    data = request.json
    # aoi_geojson = data.get('aoi')
    
    # if not aoi_geojson:
    #     return jsonify({"error": "AOI is required"}), 400
    
    # try:
    #     aoi_shape = shape(aoi_geojson)
    # except Exception as e:
    #     return jsonify({"error": f"Invalid AOI geometry: {str(e)}"}), 400
    
    project = Project(
        name=data.get('name', 'Untitled Project'),
        description=data.get('description', ''),
        # aoi=from_shape(aoi_shape, srid=4326)
    )
    
    db.session.add(project)
    db.session.commit()
    
    return jsonify({
        "id": project.id,
        "name": project.name,
        "description": project.description,
        # "aoi": json.loads(db.session.scalar(project.aoi.ST_AsGeoJSON()))
    }), 201

@app.route('/api/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    project = Project.query.get_or_404(project_id)
    
    project_data = {
        'id': project.id,
        'name': project.name,
        'description': project.description,
        'aoi': None
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
    # if 'aoi' in data:
    #     aoi_shape = shape(data['aoi'])
    #     project.aoi = from_shape(aoi_shape, srid=4326)
    
    db.session.commit()
    return jsonify(project.to_dict())

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

    if not project_id or not basemap_date or not polygons:
        return jsonify({'error': 'Missing required data'}), 400

    # If basemap_date is an object, extract the value
    if isinstance(basemap_date, dict):
        basemap_date = basemap_date.get('value')

    # Validate basemap_date format
    try:
        datetime.strptime(basemap_date, '%Y-%m')
    except ValueError:
        return jsonify({'error': 'Invalid basemap_date format. Use YYYY-MM.'}), 400

    training_set = TrainingPolygonSet.query.filter_by(project_id=project_id, basemap_date=basemap_date).first()
    if training_set:
        training_set.polygons = polygons
        training_set.updated_at = datetime.utcnow()
    else:
        training_set = TrainingPolygonSet(project_id=project_id, basemap_date=basemap_date, polygons=polygons)
        db.session.add(training_set)

    try:
        db.session.commit()
        return jsonify({'message': 'Training polygons saved successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/training_polygons/<int:project_id>', methods=['GET'])
def get_training_polygons(project_id):
    training_sets = TrainingPolygonSet.query.filter_by(project_id=project_id).all()
    result = [{
        'id': ts.id,
        'basemap_date': ts.basemap_date,
        'has_polygons': bool(ts.polygons),
        'updated_at': ts.updated_at.isoformat()
    } for ts in training_sets]
    return jsonify(result), 200

@app.route('/api/training_polygons/<int:project_id>/<string:basemap_date>', methods=['GET'])
def get_specific_training_polygons(project_id, basemap_date):
    training_set = TrainingPolygonSet.query.filter_by(project_id=project_id, basemap_date=basemap_date).first()
    if training_set:
        return jsonify(training_set.polygons), 200
    else:
        return jsonify({'message': 'No training polygons found for this date'}), 404

def get_training_polygon_set_id(project_id, basemap_date):
    try:
        # Try to find an existing TrainingPolygonSet
        training_set = TrainingPolygonSet.query.filter_by(
            project_id=project_id,
            basemap_date=basemap_date
        ).first()

        if training_set:
            return training_set.id

        # If not found, create a new TrainingPolygonSet
        new_training_set = TrainingPolygonSet(
            project_id=project_id,
            basemap_date=basemap_date
        )
        db.session.add(new_training_set)
        db.session.commit()

        return new_training_set.id

    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in get_training_polygon_set_id: {str(e)}")
        db.session.rollback()
        raise
    except Exception as e:
        current_app.logger.error(f"Unexpected error in get_training_polygon_set_id: {str(e)}")
        raise

@app.route('/api/predictions/<int:project_id>', methods=['GET'])
def get_predictions(project_id):
    predictions = Prediction.query.filter_by(project_id=project_id).all()
    return jsonify([{
        'id': p.id,
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

# 
def store_pixel_data(raster_id, pixel_data, class_labels):
    
    file_name = f"pixel_data_{raster_id}.h5"
    file_path = os.path.join('./training_data', file_name)

    # Convert class labels to ASCII if they're Unicode
    if class_labels.dtype.kind == 'U':
        class_labels = np.array([label.encode('ascii', 'ignore') for label in class_labels])

    
    # Store pixel data in HDF5 file
    with h5py.File(file_path, 'w') as f:
        f.create_dataset('pixels', data=pixel_data, dtype='float32')
        f.create_dataset('labels', data=class_labels, dtype=h5py.special_dtype(vlen=str))
        f.attrs['band_count'] = pixel_data.shape[1]
        f.attrs['pixel_count'] = pixel_data.shape[0]
    
    # Store metadata in database
    dataset = PixelDataset(
        raster_id=raster_id,
        file_path=file_path,
        num_pixels=len(pixel_data),
        class_distribution=str(dict(zip(*np.unique(class_labels, return_counts=True))))
    )
    db.session.add(dataset)
    db.session.commit()

def load_pixel_data(file_path):
    with h5py.File(file_path, 'r') as f:
        pixel_data = f['pixels'][:].astype(np.float32)  # Ensure float type for pixel data
        class_labels = f['labels'][:].astype(str)
    return pixel_data, class_labels


@app.route('/api/list_pixel_datasets', methods=['GET'])
def list_pixel_datasets():
    datasets = db.session.query(PixelDataset, Raster.filename).\
        join(Raster, PixelDataset.raster_id == Raster.id).all()
    
    return jsonify([{
        'id': dataset.PixelDataset.id,
        'raster_id': dataset.PixelDataset.raster_id,
        'raster_filename': dataset.filename,
        'num_pixels': dataset.PixelDataset.num_pixels,
        'class_distribution': dataset.PixelDataset.class_distribution
    } for dataset in datasets])


def fetch_raster_file_path(raster_id):
    try:
        raster = Raster.query.filter_by(id=raster_id).one()
        return raster.filepath
    except NoResultFound:
        abort(404, description=f"Raster with id {raster_id} not found")


# Upload raster and save description
@app.route('/api/upload_raster', methods=['POST'])
def upload_raster():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    description = request.form.get('description', '')
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        filename = file.filename
        filepath = os.path.join('rasters', filename)  # Assuming a 'rasters' directory in your project
        os.makedirs('rasters', exist_ok=True)  # Create the 'rasters' directory if it doesn't exist
        file.save(filepath)
        
        new_raster = Raster(filename=filename, filepath=filepath, description=description)
        db.session.add(new_raster)
        db.session.commit()
        
        return jsonify({"message": "File uploaded successfully", "id": new_raster.id}), 200
    
    
@app.route('/api/list_rasters', methods=['GET'])
def get_rasters():
    rasters = Raster.query.all()
    raster_list = []
    for raster in rasters:
        raster_list.append({
            'id': raster.id,
            'filename': raster.filename,
            'filepath': raster.filepath,
            'description': raster.description
        })
    return jsonify(raster_list)

@app.route('/api/list_models', methods=['GET'])
def get_models():
    models = TrainedModel.query.all()
    model_list = []
    for model in models:
        model_list.append({
            'id': model.id,
            'name': model.name,
            'filepath': model.file_path,
            'pixel_dataset_id': model.pixel_dataset_id,
            'accuracy': model.accuracy,
            'created_at': model.created_at
        })
    return jsonify(model_list)


@app.route('/api/rasters/<int:raster_id>', methods=['GET'])
def get_raster_by_id(raster_id):
    try:
        raster = Raster.query.get(raster_id)
        if raster is None:
            return jsonify({"error": "Raster not found"}), 404
        return jsonify({
            "id": raster.id,
            "filename": raster.filename,
            "filepath": raster.filepath,
            "description": raster.description
        })
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500


# Model training

@app.route('/api/train_model', methods=['POST'])
def train_model():
    data = request.json
    project_id = data['projectId']
    aoi_extent = data['aoiExtent']
    basemap_date = data['basemapDate']
    training_polygons = data['trainingPolygons']
    model_params = {
            'n_estimators': data.get('n_estimators', 100),
            'max_depth': data.get('max_depth', 3),
            'learning_rate': data.get('learning_rate', 0.1),
            'min_child_weight': data.get('min_child_weight', 1),
            'gamma': data.get('gamma', 0)
        }
    # Start a background task for the training process
    thread = threading.Thread(target=run_training_process, args=(app, project_id, aoi_extent, basemap_date, training_polygons, model_params))
    thread.start()

    return jsonify({"message": "Training process started"}), 202

def run_training_process(app, project_id, aoi, basemap_date, training_polygons, model_params):
    with app.app_context():
        try:
            # Step 1: Get Planet quads
            update_progress(project_id, 0.1, "Fetching Planet quads")
            quads = get_planet_quads(aoi, basemap_date)
            
            # import time
            # time.sleep(5)

            # Step 2: Extract pixels from quads using training polygons
            update_progress(project_id, 0.3, "Extracting pixels from quads")

            X, y = extract_pixels_from_quads(quads, training_polygons)

            # Step 3: Train XGBoost model
            update_progress(project_id, 0.6, "Training XGBoost model")

            training_polygon_set_id = get_training_polygon_set_id(project_id, basemap_date) 
            saved_model, metrics = train_xgboost_model(X, y, project_id, training_polygon_set_id, basemap_date, model_params)

            # Step 4: Predict land cover across AOI
            update_progress(project_id, 0.6, "Predicting land cover across AOI")
            prediction_file = predict_landcover_aoi(saved_model.id, quads, aoi, project_id, basemap_date)

            # Save prediction to database
            prediction = Prediction(
                project_id=project_id,
                model_id=saved_model.id,
                file_path=prediction_file,
                basemap_date=basemap_date
            )
            db.session.add(prediction)
            db.session.commit()

           # Step 5: Return results
            update_progress(project_id, 1.0, "Training and prediction complete", {
                **metrics, 
                "prediction_id": prediction.id,
                "model_id": saved_model.id
            })

        except Exception as e:
            logger.exception(f"Error in training process: {str(e)}")
            update_progress(project_id, 1.0, f"Error: {str(e)}")




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

    for quad in quads:
        logger.info(f"Extracting pixels from quad {quad['id']}")

        with rasterio.open(quad['filename']) as src:
            
            for feature in polygons:

                geom = shape(feature['geometry'])
                class_label = feature['properties']['classLabel']

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

                except Exception as e:
                    logger.warning(f"Error processing polygon in quad {quad['id']}: {str(e)}")

    if not all_pixels:
        raise ValueError("No valid pixels extracted from quads")
    
    return np.array(all_pixels), np.array(all_labels)




def train_xgboost_model(X, y,project_id, training_polygon_set_id, basemap_date, model_params):

    # Encode class labels
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)

   # Create and train model

    logger.info(f"Training XGBoost model with parameters: {model_params}")


    model = XGBClassifier(**model_params)
    model.fit(X_train, y_train)

    # Cross-validation
    cv_scores = cross_val_score(model, X_train, y_train, cv=model_params.get('n_folds', 5))

    # Predictions and metrics
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, target_names=le.classes_)

    # Save the trained model
    saved_model = TrainedModel.save_model(
        model, 
        f"XGBoost_Model_{datetime.now().strftime('%Y%m%d_%H%M%S')}", 
        project_id, 
        training_polygon_set_id, 
        basemap_date, 
        accuracy, 
        model_params
    )

    metrics = {
        "accuracy": float(accuracy),
        "cv_scores": cv_scores.tolist(),
        "classification_report": report
    }

    return saved_model, metrics


def predict_landcover_aoi(model_id, quads, aoi, project_id, basemap_date):
    model = TrainedModel.load_model(model_id)
    if model is None:
        raise ValueError("Model not found")

    logger.debug(f"AOI: {aoi}")

    # Create a list to store the predicted rasters
    predicted_rasters = []
    temp_files = []  # To keep track of temporary files for cleanup
    quad_bounds = []


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
            predictions = model.predict(reshaped_data)
            prediction_map = predictions.reshape(data.shape[1], data.shape[2])

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
    aoi_geom = box(*aoi)
    aoi_bounds = transform_bounds("EPSG:4326", src.crs, *aoi)
    aoi_geom = box(*aoi_bounds)
    logger.debug(f"Transformed AOI bounds: {aoi_bounds}")
    mosaic, out_transform = merge(predicted_rasters, bounds = aoi_bounds)

    
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
    output_file = f"./predictions/landcover_prediction_project{project_id}_{basemap_date}.tif"
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



def analyze_change(prediction1_id, prediction2_id):
    # Fetch the prediction rasters
    prediction1 = Prediction.query.get_or_404(prediction1_id)
    prediction2 = Prediction.query.get_or_404(prediction2_id)

    # Read the rasters
    with rasterio.open(prediction1.file_path) as src1, rasterio.open(prediction2.file_path) as src2:
        # Ensure the rasters have the same extent and resolution
        if src1.bounds != src2.bounds or src1.res != src2.res:
            return jsonify({"error": "Predictions have different extents or resolutions"}), 400

        # Read the data
        data1 = src1.read(1)
        data2 = src2.read(1)

        # Calculate areas
        pixel_area = src1.res[0] * src1.res[1] / 1_000_000  # Area in sq km

        previous_forest = np.sum(data1 == 1) * pixel_area
        previous_non_forest = np.sum(data1 == 0) * pixel_area
        current_forest = np.sum(data2 == 1) * pixel_area
        current_non_forest = np.sum(data2 == 0) * pixel_area

        # Calculate change
        deforested = np.sum((data1 == 1) & (data2 == 0)) * pixel_area
        reforested = np.sum((data1 == 0) & (data2 == 1)) * pixel_area

        total_area = previous_forest + previous_non_forest
        deforestation_rate = (deforested - reforested) / previous_forest * 100
        total_area_changed = deforested + reforested

        results = {
            "previousForestArea": float(previous_forest),
            "previousNonForestArea": float(previous_non_forest),
            "currentForestArea": float(current_forest),
            "currentNonForestArea": float(current_non_forest),
            "deforestedArea": float(deforested),
            "reforestedArea": float(reforested),
            "deforestationRate": float(deforestation_rate),
            "totalAreaChanged": float(total_area_changed),
            "totalArea": float(total_area)
        }

        logger.info(f"Change analysis results: {results}")

        return jsonify(results)

# Add this route to your Flask app
@app.route('/api/analyze_change', methods=['POST'])
def api_analyze_change():
    data = request.json
    prediction1_id = data.get('prediction1_id')
    prediction2_id = data.get('prediction2_id')
    
    if not prediction1_id or not prediction2_id:
        return jsonify({"error": "Both prediction IDs are required"}), 400

    return analyze_change(prediction1_id, prediction2_id)



if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(debug=True)






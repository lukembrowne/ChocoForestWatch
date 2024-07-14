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



# Load environment variables from the .env file
load_dotenv()

# Load the Planet API key from an environment variable
PLANET_API_KEY = os.getenv('PLANET_API_KEY')

if not PLANET_API_KEY:
    raise ValueError("No PLANET_API_KEY set for Flask application. Did you follow the setup instructions?")

# Setup Planet base URL
API_URL = "https://api.planet.com/basemaps/v1/mosaics"

# Setup session
session = requests.Session()
session.auth = (PLANET_API_KEY, "")


app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

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
    aoi = db.Column(Geometry('POLYGON'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'aoi': db.session.scalar(self.aoi.ST_AsGeoJSON()),
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


class Raster(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    filepath = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(200))

class TrainingPolygons(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    geojson = db.Column(JSONB)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)



class PixelDataset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    raster_id = db.Column(db.Integer, db.ForeignKey('raster.id'))
    file_path = db.Column(db.String(255))
    num_pixels = db.Column(db.Integer)
    class_distribution = db.Column(db.String)  # JSON string of class counts



class TrainedModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    pixel_dataset_id = db.Column(db.Integer, db.ForeignKey('pixel_dataset.id'))
    accuracy = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def save_model(cls, model, name, pixel_dataset_id, accuracy):
        model_dir = './trained_models'
        os.makedirs(model_dir, exist_ok=True)
        file_path = os.path.join(model_dir, f"{name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.joblib")
        
        joblib.dump(model, file_path)
        
        new_model = cls(name=name, file_path=file_path, pixel_dataset_id=pixel_dataset_id, accuracy=accuracy)
        db.session.add(new_model)
        db.session.commit()
        return new_model

    @classmethod
    def load_model(cls, model_id):
        model_record = cls.query.get(model_id)
        if model_record:
            return joblib.load(model_record.file_path)
        return None
        


# Create tables
with app.app_context():
    db.create_all()

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
    aoi_geojson = data.get('aoi')
    
    if not aoi_geojson:
        return jsonify({"error": "AOI is required"}), 400
    
    try:
        aoi_shape = shape(aoi_geojson)
    except Exception as e:
        return jsonify({"error": f"Invalid AOI geometry: {str(e)}"}), 400
    
    project = Project(
        name=data.get('name', 'Untitled Project'),
        description=data.get('description', ''),
        aoi=from_shape(aoi_shape, srid=4326)
    )
    
    db.session.add(project)
    db.session.commit()
    
    return jsonify({
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "aoi": json.loads(db.session.scalar(project.aoi.ST_AsGeoJSON()))
    }), 201

@app.route('/api/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    project = Project.query.get_or_404(project_id)
    return jsonify(project.to_dict())

@app.route('/api/projects/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    project = Project.query.get_or_404(project_id)
    data = request.json
    
    if 'name' in data:
        project.name = data['name']
    if 'description' in data:
        project.description = data['description']
    if 'aoi' in data:
        aoi_shape = shape(data['aoi'])
        project.aoi = from_shape(aoi_shape, srid=4326)
    
    db.session.commit()
    return jsonify(project.to_dict())

@app.route('/api/projects', methods=['GET'])
def list_projects():
    projects = Project.query.all()
    return jsonify([project.to_dict() for project in projects])






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




# Extract pixel values from raster based on polygons
@app.route('/api/extract_pixels', methods=['POST'])
def extract_pixels():
    data = request.json
    raster_id = data.get('rasterId')
    polygons = data.get('polygons')

    if not raster_id or not polygons:
        return jsonify({'error': 'Missing raster ID or polygons'}), 400

    raster_file = fetch_raster_file_path(raster_id)

    if not os.path.exists(raster_file):
        return jsonify({'error': 'Raster file not found'}), 404

    all_pixels = []
    all_labels = []

    with rasterio.open(raster_file) as src:
        if src.count != 4:
            return jsonify({'error': 'Raster file does not have 4 bands'}), 400

        for feature in polygons:

            geom = shape(feature['geometry'])
            class_label = feature['properties']['classLabel']
            
            out_image, out_transform = mask(src, [geom], crop=True, all_touched=True)
            out_image = np.ma.masked_equal(out_image, src.nodata)
            
            # Reshape the output to have pixels as rows and bands as columns
            pixels = out_image.reshape(out_image.shape[0], -1).T
            
            # Remove any pixels where all bands are masked
            valid_pixels = pixels[~np.all(pixels.mask, axis=1)]
            
            if valid_pixels.size > 0:
                all_pixels.extend(valid_pixels.data)
                all_labels.extend([class_label] * valid_pixels.shape[0])

    all_pixels = np.array(all_pixels)
    all_labels = np.array(all_labels)

    if all_pixels.size == 0:
        return jsonify({'error': 'No valid pixels extracted'}), 400

    store_pixel_data(raster_id, all_pixels, all_labels)

    return jsonify({
        "message": "Pixel data extracted and stored successfully",
        "pixel_count": all_pixels.shape[0],
        "band_count": all_pixels.shape[1]
    })


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

@app.route('/api/list_vectors', methods=['GET'])
def list_vectors():
    vectors = TrainingPolygons.query.all()
    return jsonify([{
        "id": v.id,
        "filename": v.filename,
        "description": v.description,
        "feature_count": len(v.geojson['features'])
    } for v in vectors])


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

@app.route('/api/upload_vector', methods=['POST'])
def upload_vector():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    description = request.form.get('description', '')
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and file.filename.endswith('.geojson'):
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        with open(filepath, 'r') as f:
            geojson = json.load(f)
        
        # Ensure the GeoJSON is a FeatureCollection
        if geojson['type'] != 'FeatureCollection':
            geojson = {
                "type": "FeatureCollection",
                "features": [geojson] if geojson['type'] == 'Feature' else []
            }
        
        new_vector = TrainingPolygons(
            filename=filename,
            description=description,
            geojson=geojson
        )
        db.session.add(new_vector)
        db.session.commit()
        
        return jsonify({
            "message": "Vector file uploaded successfully.",
            "id": new_vector.id,
            "feature_count": len(geojson['features'])
        }), 200
    
    return jsonify({"error": "Invalid file format"}), 400



@app.route('/api/save_drawn_polygons', methods=['POST'])
def save_drawn_polygons():
    data = request.json
    if not data or 'polygons' not in data:
        return jsonify({"error": "No polygon data provided"}), 400

    description = data.get('description', 'Drawn polygons')
    polygons = data['polygons']

    geojson = {
        "type": "FeatureCollection",
        "features": []
    }

    for polygon in polygons:
        feature = {
            "type": "Feature",
            "properties": {
                "classLabel": polygon['properties']['classLabel']
            },
            "geometry": polygon['geometry']
        }
        geojson['features'].append(feature)

    new_vector = TrainingPolygons(
        filename=f"drawn_polygons_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.geojson",
        description=description,
        geojson=geojson
    )

    try:
        db.session.add(new_vector)
        db.session.commit()

        return jsonify({
            "message": "Drawn polygons saved successfully",
            "id": new_vector.id,
            "filename": new_vector.filename,
            "feature_count": len(geojson['features'])
        }), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


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

@app.route('/api/vectors/<int:vector_id>', methods=['GET'])
def get_vector_by_id(vector_id):
    try:
        vector = TrainingPolygons.query.get(vector_id)
        if vector is None:
            return jsonify({"error": "Vector not found"}), 404
        return jsonify({
            "id": vector.id,
            "filename": vector.filename,
            "description": vector.description,
            "geojson": vector.geojson
        })
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/train_model', methods=['POST'])
def train_model():
    params = request.json
    pixel_dataset_id = params['pixel_dataset_id']
    model_name = params.get('model_name', 'XGBoost_LandCover')
    
    dataset = PixelDataset.query.get(pixel_dataset_id)
    if not dataset:
        return jsonify({"error": "Pixel dataset not found"}), 404

    pixel_data, class_labels = load_pixel_data(dataset.file_path)
    if pixel_data is None or class_labels is None:
        return jsonify({"error": "Failed to load pixel data"}), 500

    # Encode class labels
    le = LabelEncoder()
    y = le.fit_transform(class_labels)

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(pixel_data, y, test_size=0.2, random_state=42)

   # pdb.set_trace()

    # Create and train model
    model = XGBClassifier(
        n_estimators=params.get('n_estimators', 100),
        max_depth=params.get('max_depth', 3),
        learning_rate=params.get('learning_rate', 0.1)
    )
    model.fit(X_train, y_train)


    # Cross-validation
    cv_scores = cross_val_score(model, X_train, y_train, cv=params.get('n_folds', 5))

    # Predictions and metrics
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, target_names=le.classes_)
    
    # Save the trained model
    saved_model = TrainedModel.save_model(model, model_name, pixel_dataset_id, accuracy)


    return jsonify({
        "message": "Model trained successfully",
        "model_id": saved_model.id,
        "accuracy": float(accuracy),
        "cv_scores": cv_scores.tolist(),
        "classification_report": report
    })


# Predict landcover using a trained model
@app.route('/api/predict_landcover', methods=['POST'])
def predict_landcover():
    params = request.json
    model_id = params['model_id']
    raster_id = params['raster_id']
    
    model = TrainedModel.load_model(model_id)
    if model is None:
        return jsonify({"error": "Model not found"}), 404
    
    raster = Raster.query.get(raster_id)
    if raster is None:
        return jsonify({"error": "Raster not found"}), 404
    
    raster_file = raster.filepath
    if not os.path.exists(raster_file):
        return jsonify({"error": "Raster file not found"}), 404
    
    with rasterio.open(raster_file) as src:
        data = src.read()
        meta = src.meta
        
        reshaped_data = data.reshape(data.shape[0], -1).T
        predictions = model.predict(reshaped_data)
        prediction_map = predictions.reshape(data.shape[1], data.shape[2])
        
        output_meta = {
            'driver': 'GTiff',
            'dtype': 'uint8',
            'nodata': None,
            'width': meta['width'],
            'height': meta['height'],
            'count': 1,
            'crs': meta['crs'],
            'transform': meta['transform'],
            'compress': 'lzw',
        }
        
        output_file = f"./predictions/landcover_prediction_{raster_id}.tif"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with rasterio.open(output_file, 'w', **output_meta) as dst:
            dst.write(prediction_map.astype(rasterio.uint8), 1)
    
    return jsonify({
        "message": "Landcover prediction completed",
        "prediction_file": output_file
    })



@app.route('/api/planet/quads', methods=['POST'])
def get_available_quads():
    try:
        data = request.json
        bbox = data.get('bbox')
        mosaic_name = data.get('mosaic_name', 'planet_medres_normalized_analytic_2022-08_mosaic')  # You can change the default or always require it from the frontend
        
        if not bbox or len(bbox) != 4:
            return jsonify({"error": "Invalid bounding box"}), 400

        # First, get the mosaic ID
        parameters = {
            "name__is": mosaic_name
        }
        res = session.get(API_URL, params=parameters)
        if res.status_code != 200:
            return jsonify({"error": f"Failed to fetch mosaic. Status code: {res.status_code}"}), res.status_code

        mosaic_data = res.json()
        if not mosaic_data['mosaics']:
            return jsonify({"error": "No mosaic found with the given name"}), 404

        mosaic_id = mosaic_data['mosaics'][0]['id']

        # Now, search for quads using the provided bbox
        string_bbox = ','.join(map(str, bbox))
        search_parameters = {
            'bbox': string_bbox,
            'minimal': True
        }

        quads_url = f"{API_URL}/{mosaic_id}/quads"
        res = session.get(quads_url, params=search_parameters)
        if res.status_code != 200:
            return jsonify({"error": f"Failed to fetch quads. Status code: {res.status_code}"}), res.status_code

        quads_data = res.json()
        items = quads_data['items']

        # Process the quads data
        quads = []
        for item in items:
            quads.append({
                "id": item['id'],
                "name": item.get('name', 'N/A'),
                "date": item.get('acquired', 'N/A'),
                "download_link": item['_links']['download']
            })

        return jsonify(quads)

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=True)



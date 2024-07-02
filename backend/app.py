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
from geoalchemy2.shape import to_shape
from geoalchemy2.functions import ST_AsGeoJSON
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm.exc import NoResultFound

import datetime



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
class Raster(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    filepath = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(200))

class Vectors(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    geojson = db.Column(JSONB)

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

# Extract pixel values from raster based on polygons
@app.route('/api/extract_pixels', methods=['POST'])
def extract_pixels():
    data = request.json
    raster_id = data.get('rasterId')
    polygons = data.get('polygons')

    if not raster_id or not polygons:
        return jsonify({'error': 'Missing raster ID or polygons'}), 400

    # Fetch raster file path from database based on raster_id
    raster_file = fetch_raster_file_path(raster_id)  # You need to implement this function

    if not os.path.exists(raster_file):
        return jsonify({'error': 'Raster file not found'}), 404

    extracted_values = []

    with rasterio.open(raster_file) as src:

        for feature in polygons:
            geom = shape(feature['geometry']['geometry'])
            class_label = feature['properties']['classLabel']
            
            out_image, out_transform = mask(src, [geom], crop=True)
            out_image = np.ma.masked_equal(out_image, src.nodata)
            
            # Calculate statistics for the masked area
            stats = {
                'min': float(out_image.min()),
                'max': float(out_image.max()),
                'mean': float(out_image.mean()),
                'std': float(out_image.std())
            }

            extracted_values.append({
                'classLabel': class_label,
                'stats': stats,
                'data': out_image.data.tolist()
            })

    return jsonify(extracted_values)



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
    vectors = Vectors.query.all()
    return jsonify([{
        "id": v.id,
        "filename": v.filename,
        "description": v.description,
        "feature_count": len(v.geojson['features'])
    } for v in vectors])


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
        
        new_vector = Vectors(
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




@app.route('/api/get_vector/<int:vector_id>', methods=['GET'])
def get_vector(vector_id):
    vector = Vectors.query.get_or_404(vector_id)
    return jsonify(vector.geojson)

@app.route('/api/save_drawn_polygons', methods=['POST'])
def save_drawn_polygons():
    data = request.json
    if not data or 'polygons' not in data:
        return jsonify({"error": "No polygon data provided"}), 400

    description = data.get('description', '')
    polygons = data['polygons']

    geojson = {
        "type": "FeatureCollection",
        "features": []
    }

    for polygon in polygons:
        feature = {
            "type": "Feature",
            "properties": {
                "classLabel": polygon['classLabel']
            },
            "geometry": polygon['geometry']
        }
        geojson['features'].append(feature)

    new_vector = Vectors(
        filename=f"drawn_polygons.geojson",
        description=description,
        geojson=geojson
    )

    db.session.add(new_vector)
    db.session.commit()

    return jsonify({
        "message": "Drawn polygons saved successfully.",
        "id": new_vector.id,
        "feature_count": len(geojson['features'])
    }), 200




if __name__ == '__main__':
    app.run(debug=True)
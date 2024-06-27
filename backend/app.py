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

class VectorData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    geom = db.Column(Geometry('POLYGON'))

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


# Extract pixel values from a raster file for a given polygon
@app.route('/extract_pixels', methods=['POST'])
def extract_pixels():
    # Get the raster URL
    raster_url = request.form.get('raster')
    if not raster_url:
        return jsonify({'error': 'No raster URL provided'}), 400

    # Get the polygons
    polygons = json.loads(request.form['polygons'])
    
    # Download the raster file
    try:
        response = requests.get(raster_url)
        response.raise_for_status()
        raster_filename = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_raster.tif')
        with open(raster_filename, 'wb') as f:
            f.write(response.content)
    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500

    extracted_values = []

    with rasterio.open(raster_filename) as src:
        for feature in polygons:
            geom = shape(feature['geometry']['geometry'])  # Ensure this is the geometry object
            out_image, out_transform = mask(src, [mapping(geom)], crop=True)
            out_image = np.ma.masked_equal(out_image, src.nodata)
            extracted_values.append(out_image.data.tolist())
    
    # Clean up the downloaded file
    os.remove(raster_filename)

    return jsonify(extracted_values)


# Upload raster and save description
@app.route('/upload_raster', methods=['POST'])
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
    

@app.route('/upload_vector', methods=['POST'])
def upload_vector():
    data = request.json
    if not data or 'name' not in data or 'geometry' not in data:
        return jsonify({"error": "Invalid data"}), 400

    new_vector = VectorData(name=data['name'], geom=data['geometry'])
    db.session.add(new_vector)
    db.session.commit()
    
    return jsonify({"message": "Vector data uploaded successfully", "id": new_vector.id}), 200

    
@app.route('/api/rasters', methods=['GET'])
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


if __name__ == '__main__':
    app.run(debug=True)
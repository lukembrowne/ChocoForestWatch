from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import rasterio
import json
from shapely.geometry import shape, mapping
from rasterio.mask import mask
import numpy as np
import os
from werkzeug.utils import secure_filename


app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Define a directory to temporarily store uploaded files
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Serve static files from the 'data' directory
@app.route('/data/<path:filename>')
def data_files(filename):
    return send_from_directory('data', filename)

# Serve static files from the 'data' directory
@app.route('/uploads/<path:filename>')
def upload_files(filename):
    return send_from_directory('uploads', filename)


# Extract pixel values from a raster file for a given polygon
@app.route('/extract_pixels', methods=['POST'])
def extract_pixels():
    # Get the uploaded file
    if 'raster' not in request.files:
        return jsonify({'error': 'No raster file provided'}), 400

    file = request.files['raster']
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Get the polygons
    polygons = json.loads(request.form['polygons'])
    
    extracted_values = []

    with rasterio.open(filepath) as src:
        for feature in polygons:
            geom = shape(feature['geometry']['geometry'])  # Ensure this is the geometry object
            out_image, out_transform = mask(src, [mapping(geom)], crop=True)
            out_image = np.ma.masked_equal(out_image, src.nodata)
            extracted_values.append(out_image.data.tolist())
    
    # Clean up the uploaded file
    os.remove(filepath)

    return jsonify(extracted_values)


# Upload raster and save description
@app.route('/upload_raster', methods=['POST'])
def upload_raster():
    if 'raster' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['raster']
    description = request.form.get('description', '')

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Save the metadata
        metadata = {
            'filename': filename,
            'description': description
        }
        with open(os.path.join(app.config['UPLOAD_FOLDER'], f'{filename}.json'), 'w') as f:
            json.dump(metadata, f)

        file_url = f"http://127.0.0.1:5000/uploads/{filename}"
        return jsonify({'url': file_url}), 200
    
@app.route('/list_rasters', methods=['GET'])
def list_rasters():
    files = []
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        if filename.endswith('.tiff'):
            metadata_file = os.path.join(app.config['UPLOAD_FOLDER'], f'{filename}.json')
            if os.path.exists(metadata_file):
                with open(metadata_file) as f:
                    metadata = json.load(f)
            else:
                metadata = {'filename': filename, 'description': ''}
            files.append(metadata)
    return jsonify(files)   


if __name__ == '__main__':
    app.run(debug=True)
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

if __name__ == '__main__':
    app.run(debug=True)
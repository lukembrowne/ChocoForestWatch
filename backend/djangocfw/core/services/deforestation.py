import numpy as np
import rasterio
from rasterio.mask import mask
from sklearn.metrics import confusion_matrix
from shapely.geometry import shape as shapely_shape, mapping as shapely_mapping
import tempfile
import uuid
import os
from datetime import datetime
from rasterio.features import sieve
import json
from rasterio import features
from shapely.geometry import shape, mapping
import math
from core.models import Prediction, TrainedModel, Project, DeforestationHotspot
from django.conf import settings
from core.storage import PredictionStorage
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from loguru import logger
from datetime import timedelta
import requests
from pyproj import Transformer
from shapely.geometry import box
from rasterio.mask import mask
import numpy as np
import os
import tempfile
from shapely.ops import transform

def analyze_change(prediction1_id, prediction2_id, aoi_shape):
    """
    Analyze deforestation between two predictions
    """
    prediction1 = Prediction.objects.get(id=prediction1_id)
    prediction2 = Prediction.objects.get(id=prediction2_id)

    model1 = TrainedModel.objects.get(id=prediction1.model_id)
    model2 = TrainedModel.objects.get(id=prediction2.model_id)

    
    # Ensure both predictions use the same set of classes
    if model1.all_class_names != model2.all_class_names:
        raise ValueError('Predictions use different class sets')

    all_class_names = model1.all_class_names

    with rasterio.open(prediction1.file) as src1, rasterio.open(prediction2.file) as src2:
        if src1.bounds != src2.bounds or src1.res != src2.res:
            raise ValueError("Predictions have different extents or resolutions")

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

        # Generate deforestation raster
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
        
        # Apply sieve filter to remove small isolated pixels
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

        # Handle AOI shape conversion
        try:
            # If aoi_shape is a string, try to parse it as JSON
            if isinstance(aoi_shape, str):
                aoi_shape = json.loads(aoi_shape)
            
            # If it's a dict with __geo_interface__, use that
            if hasattr(aoi_shape, '__geo_interface__'):
                aoi_geojson = aoi_shape.__geo_interface__
            # If it's already a GeoJSON dict with type 'Polygon'
            elif isinstance(aoi_shape, dict) and aoi_shape.get('type') == 'Polygon':
                aoi_geojson = aoi_shape
            # If it's a dict but needs conversion to proper GeoJSON
            elif isinstance(aoi_shape, dict):
                aoi_geojson = {
                    'type': 'Polygon',
                    'coordinates': aoi_shape.get('coordinates', [])
                }
            else:
                raise ValueError(f"Invalid AOI shape format: {type(aoi_shape)}")

        except Exception as e:
            raise ValueError(f"Error processing AOI shape: {str(e)}")

        # Clip the mosaic to the AOI
        with rasterio.open(temp_tif) as src:
            clipped_deforestation, clipped_transform = mask(
                src,
                shapes=[aoi_geojson],
                crop=True,
                filled=True,
                nodata=255
            )
        
        # Save deforestation raster
        deforestation_dir = os.path.join(settings.MEDIA_ROOT, 'deforestation')
        if not os.path.exists(deforestation_dir):
            os.makedirs(deforestation_dir)

        deforestation_path = os.path.join(
            deforestation_dir,
            f"defor_project{prediction1.project_id}_{prediction1.basemap_date}_{prediction2.basemap_date}_{uuid.uuid4().hex}.tif"
        )
        
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

        # Use PredictionStorage for saving the file
        storage = PredictionStorage()
        
        # Create a unique filename - shorter version
        filename = f"defor_{prediction1.project_id}_{uuid.uuid4().hex[:8]}.tif"
        
        # Save the deforestation raster using the storage
        with rasterio.open(temp_tif, 'r') as src:
            # Get the metadata from the source file
            meta = src.meta.copy()
            meta.update({
                'driver': 'GTiff',
                'dtype': 'uint8',
                'nodata': 255,
                'compress': 'lzw',
                'count': 1,
                'width': clipped_deforestation.shape[2],
                'height': clipped_deforestation.shape[1],
                'transform': clipped_transform
            })
            
            # Create a temporary file with the proper metadata
            with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp:
                temp_output = tmp.name
                
            # Write the data to the temporary file with proper metadata
            with rasterio.open(temp_output, 'w', **meta) as dst:
                dst.write(clipped_deforestation[0], 1)
                
            # Read the properly written file and save it using storage
            with open(temp_output, 'rb') as f:
                saved_path = storage.save(filename, ContentFile(f.read()))
                
            # Clean up the temporary output file
            os.remove(temp_output)

        # Update the prediction creation/update code
        deforestation_prediction, created = Prediction.objects.get_or_create(
            project_id=prediction1.project_id,
            name=f"Deforestation_{prediction1.basemap_date}_to_{prediction2.basemap_date}",
            defaults={
                'model_id': prediction1.model_id,
                'file': saved_path,
                'created_at': datetime.now(),
                'summary_statistics': results,
                'type': 'deforestation',
                'basemap_date': prediction1.basemap_date
            }
        )

        if not created:
            # Update existing prediction
            if deforestation_prediction.file:
                storage.delete(deforestation_prediction.file.name)
            
            deforestation_prediction.file = saved_path
            deforestation_prediction.created_at = datetime.now()
            deforestation_prediction.summary_statistics = results
            deforestation_prediction.save()

        # Add deforestation prediction ID to results
        results["deforestation_prediction_id"] = deforestation_prediction.id
        
        # Clean up temporary file
        if os.path.exists(temp_tif):
            os.remove(temp_tif)
            
        return results 

def get_deforestation_hotspots(prediction_id, min_area_ha=1.0, source='all'):
    """Get or generate deforestation hotspots for a prediction"""
    try:
        prediction = get_object_or_404(Prediction, id=prediction_id)
        
        # Query existing hotspots with source filter
        hotspots = DeforestationHotspot.objects.filter(prediction=prediction)
        if source != 'all':
            hotspots = hotspots.filter(source=source)
        
        features_list = []
        
        if hotspots.exists():
            logger.info(f"Found {hotspots.count()} existing hotspots for prediction {prediction_id}")
            # Convert existing hotspots to GeoJSON
            for hotspot in hotspots:
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
            logger.info(f"Generating new hotspots for prediction {prediction_id} with source {source}")
            if source in ['all', 'local']:
                # Get the file path from the FileField
                file_path = prediction.file.path if prediction.file else None
                if not file_path:
                    raise ValueError("Prediction file not found")

                with rasterio.open(file_path) as src:
                    defor_data = src.read(1)
                    defor_mask = defor_data == 1
                    pixel_area_ha = abs(src.transform[0] * src.transform[4]) / 10000

                    shapes = features.shapes(
                        defor_data, 
                        mask=defor_mask,
                        transform=src.transform
                    )
                    
                    for geom, value in shapes:
                        if value == 1:
                            polygon = shape(geom)
                            area_ha = float(polygon.area / 10000)
                            perimeter_m = float(polygon.length)
                            
                            centroid = polygon.centroid
                            edge_density = float(perimeter_m / (area_ha * 10000))
                            compactness = float(4 * math.pi * polygon.area / (perimeter_m ** 2))
                            geojson_geometry = mapping(polygon)
                            
                           # Create database record
                            hotspot = DeforestationHotspot.objects.create(
                                prediction=prediction,
                                geometry=geojson_geometry,
                                area_ha=area_ha,
                                perimeter_m=perimeter_m,
                                compactness=compactness,
                                edge_density=edge_density,
                                centroid_lon=float(centroid.x),
                                centroid_lat=float(centroid.y),
                                source='local'
                            )
                            
                            feature = {
                                "type": "Feature",
                                "id": str(hotspot.id),
                                "geometry": geojson_geometry,
                                "properties": {
                                    "area_ha": round(area_ha, 2),
                                    "perimeter_m": round(perimeter_m, 2),
                                    "compactness": round(compactness, 3),
                                    "edge_density": round(edge_density, 3),
                                    "verification_status": None,
                                    "source": "local"
                                }
                            }
                            features_list.append(feature)

            logger.info(f"Done with local alerts")
            if source in ['all', 'gfw']:
                # Get project AOI
                project = prediction.project
                try:
                    # Handle different possible AOI formats
                    if isinstance(project.aoi, str):
                        aoi_geojson = json.loads(project.aoi)
                    else:
                        aoi_geojson = json.loads(project.aoi.json)
                    
                    aoi_shape = shape(aoi_geojson)
                    
                    # Process GFW alerts
                    logger.info(f"Processing GFW alerts for prediction {prediction_id}")
                    gfw_hotspots = process_gfw_alerts(prediction_id, aoi_shape)
                    
                    # Add GFW hotspots to features list
                    for hotspot in gfw_hotspots:
                        feature = {
                            "type": "Feature",
                            "id": str(hotspot.id),
                            "geometry": hotspot.geometry,
                            "properties": {
                                "id": str(hotspot.id),
                                "area_ha": round(hotspot.area_ha, 2),
                                "perimeter_m": round(hotspot.perimeter_m, 2),
                                "compactness": round(hotspot.compactness, 3),
                                "edge_density": round(hotspot.edge_density, 3),
                                "verification_status": hotspot.verification_status,
                                "source": 'gfw',
                                "confidence": hotspot.confidence
                            }
                        }
                        features_list.append(feature)
                except Exception as e:
                    logger.error(f"Error processing GFW alerts: {str(e)}")
                    logger.error(f"AOI data type: {type(project.aoi)}")
                    logger.error(f"AOI content: {project.aoi}")
                    raise

        # Filter hotspots by minimum area
        logger.info(f"Filtering hotspots by minimum area of {min_area_ha} ha for prediction {prediction_id}")
        features_list = [f for f in features_list if f["properties"]["area_ha"] >= min_area_ha]
        
        # Sort features by area
        logger.info(f"Sorting hotspots by area for prediction {prediction_id}")
        features_list.sort(key=lambda x: x["properties"]["area_ha"], reverse=True)
        
        # Calculate statistics by source
        logger.info(f"Calculating statistics by source for prediction {prediction_id}")
        local_hotspots = [f for f in features_list if f["properties"]["source"] == "local"]
        gfw_hotspots = [f for f in features_list if f["properties"]["source"] == "gfw"]
        
        metadata = {
            "total_hotspots": len(features_list),
            "min_area_ha": min_area_ha,
            "total_area_ha": sum(f["properties"]["area_ha"] for f in features_list),
            "prediction_id": prediction_id,
            "by_source": {
                "local": {
                    "count": len(local_hotspots),
                    "total_area_ha": sum(f["properties"]["area_ha"] for f in local_hotspots)
                },
                "gfw": {
                    "count": len(gfw_hotspots),
                    "total_area_ha": sum(f["properties"]["area_ha"] for f in gfw_hotspots)
                }
            }
        }
        
        return {
            "type": "FeatureCollection",
            "features": features_list,
            "metadata": metadata
        }
            
    except Exception as e:
        logger.error(f"Error in get_deforestation_hotspots: {str(e)}")
        raise

def decode_gfw_date(value):
    """Decode GFW alert date and confidence from pixel value"""
    if value == 0:
        return None, None
    
    # Convert to string for easier processing
    encoded_str = str(value)
    
    # Get confidence level from first digit
    confidence = int(encoded_str[0])
    
    # Get days since Dec 31, 2014
    days = int(encoded_str[1:])
    
    # Calculate date
    base_date = datetime(2014, 12, 31)
    alert_date = base_date + timedelta(days=days)

    # logger.info(f"Alert date: {alert_date} - str was: {encoded_str}")
    return alert_date, confidence

def process_gfw_alerts(prediction_id, aoi_shape):
    """Process GFW alerts for a given prediction's time period"""
    try:
        logger.info(f"Starting GFW alert processing for prediction {prediction_id}")
        
        # Get prediction details
        prediction = Prediction.objects.get(id=prediction_id)
        
        # Get date range from prediction
        start_date = datetime.strptime(prediction.summary_statistics['prediction1_date'], '%Y-%m')
        end_date = datetime.strptime(prediction.summary_statistics['prediction2_date'], '%Y-%m')
        logger.info(f"Processing alerts between {start_date} and {end_date}")

        # Transform AOI from Web Mercator (EPSG:3857) to WGS84 (EPSG:4326)
        project = Transformer.from_crs('EPSG:3857', 'EPSG:4326', always_xy=True).transform
        aoi_shape_4326 = transform(project, aoi_shape)
        logger.info(f"Transformed AOI to WGS84")

        # GFW tiles for Ecuador
        GFW_TILES = [
            ("https://data-api.globalforestwatch.org/dataset/gfw_integrated_alerts/latest/download/geotiff?grid=10/100000&tile_id=10N_080W&pixel_meaning=date_conf&x-api-key=2d60cd88-8348-4c0f-a6d5-bd9adb585a8c", "10N_080W.tif"),
            ("https://data-api.globalforestwatch.org/dataset/gfw_integrated_alerts/latest/download/geotiff?grid=10/100000&tile_id=00N_080W&pixel_meaning=date_conf&x-api-key=2d60cd88-8348-4c0f-a6d5-bd9adb585a8c", "00N_080W.tif"),
            ("https://data-api.globalforestwatch.org/dataset/gfw_integrated_alerts/latest/download/geotiff?grid=10/100000&tile_id=00N_090W&pixel_meaning=date_conf&x-api-key=2d60cd88-8348-4c0f-a6d5-bd9adb585a8c", "00N_090W.tif"),
            ("https://data-api.globalforestwatch.org/dataset/gfw_integrated_alerts/latest/download/geotiff?grid=10/100000&tile_id=10N_090W&pixel_meaning=date_conf&x-api-key=2d60cd88-8348-4c0f-a6d5-bd9adb585a8c", "10N_090W.tif")
        ]

        gfw_data_dir = os.path.join(settings.MEDIA_ROOT, 'gfw_alerts')
        os.makedirs(gfw_data_dir, exist_ok=True)

        features_list = []
        
        # Process each tile individually
        for url, filename in GFW_TILES:
            # Add date to filename (before extension)
            name, ext = os.path.splitext(filename)
            dated_filename = f"{name}_{datetime.now().strftime('%Y%m%d')}{ext}"
            tile_path = os.path.join(gfw_data_dir, dated_filename)
            
            # Download if doesn't exist
            if not os.path.exists(tile_path):
                logger.info(f"Downloading tile {filename} to {tile_path}")
                response = requests.get(url, stream=True)
                response.raise_for_status()
                
                with open(tile_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            
            # Process the tile
            with rasterio.open(tile_path) as src:
                logger.info(f"Processing tile {filename}")
                
                # Check if tile intersects with AOI
                tile_bounds = box(*src.bounds)
                if not tile_bounds.intersects(aoi_shape_4326):
                    logger.info(f"Tile {filename} does not intersect with AOI, skipping")
                    continue
                
                try:
                    clipped_data, clipped_transform = mask(src, [aoi_shape_4326], crop=True)

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

                    logger.info(f"Alert mask shape: {alert_mask.shape}")
                    non_zero_pixels = np.sum(clipped_data[0] > 0)
                    logger.info(f"Non-zero pixels in tile {filename}: {non_zero_pixels}")

                    # Get shapes from this tile
                    shapes = features.shapes(
                        alert_mask.astype(np.uint8),
                        mask=alert_mask,
                        transform=clipped_transform
                    )
                    
                    logger.info(f"Shapes from GFW alerts: {shapes}")
                    
                    # Process shapes from this tile
                    for geom, value in shapes:
                        if value == 1:
                           # logger.info(f"Processing shape from GFW alerts: {geom}")
                            polygon = shape(geom)

                            # Project to Web Mercator
                            project = Transformer.from_crs('EPSG:4326', 'EPSG:3857', always_xy=True).transform
                            polygon_3857 = transform(project, polygon)
                            
                            # Calculate area and other metrics in meters
                            area_ha = polygon_3857.area / 10000
                            
                            # Create hotspot record
                            hotspot = DeforestationHotspot.objects.create(
                                prediction_id=prediction_id,
                                geometry=mapping(polygon_3857),  # Store in Web Mercator
                                area_ha=float(area_ha),
                                perimeter_m=float(polygon_3857.length),
                                compactness=float(4 * math.pi * polygon_3857.area / (polygon_3857.length ** 2)),
                                edge_density=float(polygon_3857.length / (area_ha * 10000)),
                                centroid_lon=float(polygon.centroid.x),  # Store centroids in lat/long
                                centroid_lat=float(polygon.centroid.y),
                                source='gfw',
                                confidence=int(np.mean(confidence_data[features.rasterize(
                                    [(geom, 1)],
                                    out_shape=alert_mask.shape,
                                    transform=clipped_transform
                                ) == 1]))
                            )
                            
                            features_list.append(hotspot)
                
                except Exception as e:
                    logger.error(f"Error processing tile {filename}: {str(e)}")
                    continue
        
        if features_list:
            logger.info(f"Successfully processed {len(features_list)} hotspots from GFW alerts")
        else:
            logger.warning("No valid hotspots found in GFW alerts")
            
        return features_list
            
    except Exception as e:
        logger.error(f"Error processing GFW alerts: {str(e)}")
        raise
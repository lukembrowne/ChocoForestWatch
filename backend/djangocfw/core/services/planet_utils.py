import requests
from requests.auth import HTTPBasicAuth
from django.conf import settings
from loguru import logger
from django.core.files.base import ContentFile
import os
from ..exceptions import PlanetAPIError
from pyproj import Transformer


class PlanetUtils:
    PLANET_API_KEY = settings.PLANET_API_KEY

    @staticmethod
    def get_mosaic_id(mosaic_name):
        """Get mosaic ID from Planet API"""
        try:
            url = "https://api.planet.com/basemaps/v1/mosaics"
            params = {"name__is": mosaic_name}
            response = requests.get(
                url, 
                auth=HTTPBasicAuth(PlanetUtils.PLANET_API_KEY, ''), 
                params=params
            )
            
            if response.status_code == 401:
                raise PlanetAPIError("Invalid Planet API key. Please check your configuration.")
            
            response.raise_for_status()
            mosaics = response.json().get('mosaics', [])
            
            if not mosaics:
                raise PlanetAPIError(f"No mosaic found with name: {mosaic_name}")
            
            return mosaics[0]['id']
            
        except requests.exceptions.RequestException as e:
            raise PlanetAPIError(f"Error accessing Planet API: {str(e)}")

    @staticmethod
    def get_quad_info(mosaic_id, bbox):
        """Get quad information for a given mosaic and bounding box"""
       # Create transformer from Web Mercator to WGS84
        transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326")
        
        # Extract coordinates
        minx, miny, maxx, maxy = bbox
        
        # Transform coordinates
        # Note: transform() returns (lat, lon) so we need to swap them for (lon, lat)
        lat_min, lon_min = transformer.transform(minx, miny)
        lat_max, lon_max = transformer.transform(maxx, maxy)
        
        # Create bbox string in lon,lat format (WGS84)
        # Planet API expects: west,south,east,north
        bbox_comma = f"{lon_min},{lat_min},{lon_max},{lat_max}"

        url = f"https://api.planet.com/basemaps/v1/mosaics/{mosaic_id}/quads"
        params = {
            "bbox": bbox_comma,
            "minimal": "true"
        }

        response = requests.get(
            url, 
            auth=HTTPBasicAuth(PlanetUtils.PLANET_API_KEY, ''), 
            params=params
        )
        response.raise_for_status()
        return response.json().get('items', [])

    @staticmethod
    def download_and_process_quads(quads, year, month, storage):
        """Download and process Planet quads"""
        processed_quads = []

        for quad in quads:
            quad_id = quad['id']
            download_url = quad['_links']['download']
            
            relative_path = storage.get_year_month_path(year, month)
            filename = f"{quad_id}_{year}_{month}.tif"
            full_path = os.path.join(relative_path, filename)
            
            if storage.exists(full_path):
                logger.info(f"Quad {quad_id} already exists at {full_path}, skipping download")
                local_filename = storage.path(full_path)
            else:
                logger.info(f"Downloading quad {quad_id} for {year}-{month}")
                try:
                    response = requests.get(
                        download_url, 
                        auth=HTTPBasicAuth(PlanetUtils.PLANET_API_KEY, ''), 
                        stream=True
                    )
                    response.raise_for_status()
                    
                    quad_file = ContentFile(response.content)
                    saved_path = storage.save(full_path, quad_file)
                    local_filename = storage.path(saved_path)
                    
                    logger.success(f"Successfully downloaded quad {quad_id} to {local_filename}")
                    
                except Exception as e:
                    logger.error(f"Failed to download quad {quad_id}: {str(e)}")
                    continue
            
            processed_quads.append({
                'id': quad_id,
                'filename': local_filename,
                'bbox': quad['bbox']
            })
        
        return processed_quads 
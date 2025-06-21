#!/usr/bin/env python3
"""
Test script for the forest cover raster processing functionality.

This script validates the implementation without making actual changes
to the production environment.
"""

import sys
import tempfile
import numpy as np
from pathlib import Path
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds
import json

# Add ml_pipeline to path for imports
sys.path.append(str(Path(__file__).parent.parent / "ml_pipeline" / "src"))

from ml_pipeline.raster_utils import (
    validate_raster_integrity,
    create_optimized_cog,
    standardize_forest_labels,
    compute_file_checksum,
    get_raster_overview_info,
    compare_raster_statistics,
    pixels_to_labels
)

def create_test_raster(output_path: str, width: int = 100, height: int = 100) -> bool:
    """Create a simple test raster for validation"""
    try:
        # Create sample data - forest (value 1) and non-forest (value 0) with some nodata
        data = np.random.choice([0, 1, 255], size=(height, width), p=[0.4, 0.4, 0.2])
        
        # Set up geospatial properties (western Ecuador-like bounds)
        bounds = (-82, -5, -75, 2)  # Rough western Ecuador bounds
        transform = from_bounds(*bounds, width, height)
        
        profile = {
            'driver': 'GTiff',
            'dtype': 'uint8',
            'nodata': 255,
            'width': width,
            'height': height,
            'count': 1,
            'crs': CRS.from_epsg(4326),
            'transform': transform,
            'compress': 'lzw',
            'tiled': True,
            'blockxsize': 64,
            'blockysize': 64
        }
        
        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(data, 1)
        
        print(f"✅ Created test raster: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create test raster: {str(e)}")
        return False

def create_test_boundary_geojson(output_path: str) -> bool:
    """Create a test boundary GeoJSON file"""
    try:
        # Simple polygon covering part of western Ecuador
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [-81, -3],
                            [-77, -3],
                            [-77, 1],
                            [-81, 1],
                            [-81, -3]
                        ]]
                    }
                }
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(geojson, f)
        
        print(f"✅ Created test boundary: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create test boundary: {str(e)}")
        return False

def test_raster_validation():
    """Test raster validation functionality"""
    print("\n" + "="*50)
    print("Testing Raster Validation")
    print("="*50)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_raster = Path(tmpdir) / "test_raster.tif"
        
        # Create test raster
        if not create_test_raster(str(test_raster)):
            return False
        
        # Test validation
        results = validate_raster_integrity(test_raster)
        
        if results["valid"]:
            print("✅ Raster validation passed")
            print(f"   Dimensions: {results['metadata']['width']}x{results['metadata']['height']}")
            print(f"   CRS: {results['metadata']['crs']}")
            print(f"   Nodata: {results['metadata']['nodata']}")
            print(f"   Valid pixels: {results['statistics']['valid_pixels']}")
            print(f"   Missing pixels: {results['statistics']['missing_pixels']}")
            
            if results["warnings"]:
                print(f"   Warnings: {', '.join(results['warnings'])}")
            
            return True
        else:
            print(f"❌ Raster validation failed: {results['error']}")
            return False

def test_cog_creation():
    """Test COG creation functionality"""
    print("\n" + "="*50)
    print("Testing COG Creation")
    print("="*50)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        input_raster = Path(tmpdir) / "input.tif"
        output_cog = Path(tmpdir) / "output_cog.tif"
        
        # Create test raster
        if not create_test_raster(str(input_raster)):
            return False
        
        # Test COG creation
        success = create_optimized_cog(input_raster, output_cog)
        
        if success:
            print("✅ COG creation succeeded")
            
            # Validate the COG
            cog_info = get_raster_overview_info(output_cog)
            if cog_info["has_overviews"]:
                print(f"   Overviews: {cog_info['overview_count']} levels")
                print(f"   Overview levels: {cog_info['overview_levels']}")
            else:
                print("   ⚠️  No overviews found")
            
            return True
        else:
            print("❌ COG creation failed")
            return False

def test_label_standardization():
    """Test forest label standardization"""
    print("\n" + "="*50)
    print("Testing Label Standardization")
    print("="*50)
    
    try:
        # Test with Hansen data (>= 90 = forest)
        hansen_data = np.array([0, 50, 90, 95, 100, 255])
        hansen_labels = standardize_forest_labels(hansen_data, "benchmarks-hansen-tree-cover-2022")
        
        expected_hansen = np.array([-999, 0, 1, 1, 1, -999])
        
        if np.array_equal(hansen_labels, expected_hansen):
            print("✅ Hansen label standardization passed")
        else:
            print(f"❌ Hansen standardization failed: {hansen_labels} != {expected_hansen}")
            return False
        
        # Test with MapBiomes data (3,4,5,6 = forest)
        mapbiomes_data = np.array([1, 3, 4, 5, 6, 21, 27])
        mapbiomes_labels = standardize_forest_labels(mapbiomes_data, "benchmarks-mapbiomes-2022")
        
        expected_mapbiomes = np.array([0, 1, 1, 1, 1, 0, 0])
        
        if np.array_equal(mapbiomes_labels, expected_mapbiomes):
            print("✅ MapBiomes label standardization passed")
        else:
            print(f"❌ MapBiomes standardization failed: {mapbiomes_labels} != {expected_mapbiomes}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Label standardization test failed: {str(e)}")
        return False

def test_pixels_to_labels():
    """Test the existing pixels_to_labels function"""
    print("\n" + "="*50)
    print("Testing Pixels to Labels Function")
    print("="*50)
    
    try:
        # Test different datasets
        test_cases = [
            ("benchmarks-hansen-tree-cover-2022", [0, 50, 90, 100], ["Non-Forest", "Non-Forest", "Forest", "Forest"]),
            ("benchmarks-mapbiomes-2022", [1, 3, 4, 21], ["Non-Forest", "Forest", "Forest", "Non-Forest"]),
            ("benchmarks-esa-landcover-2020", [5, 10, 15], ["Non-Forest", "Forest", "Non-Forest"]),
            ("benchmarks-jrc-forestcover-2020", [0, 1, 2], ["Non-Forest", "Forest", "Non-Forest"]),
            ("benchmarks-palsar-2020", [0, 1, 2, 3], ["Non-Forest", "Forest", "Forest", "Non-Forest"]),
            ("benchmarks-wri-treecover-2020", [0, 50, 90, 100], ["Non-Forest", "Non-Forest", "Forest", "Forest"]),
        ]
        
        for collection_id, pixels, expected in test_cases:
            result = pixels_to_labels(collection_id, np.array(pixels))
            if np.array_equal(result, np.array(expected)):
                print(f"✅ {collection_id}: passed")
            else:
                print(f"❌ {collection_id}: failed - {result} != {expected}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Pixels to labels test failed: {str(e)}")
        return False

def test_file_operations():
    """Test file operation utilities"""
    print("\n" + "="*50)
    print("Testing File Operations")
    print("="*50)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test_file.txt"
        
        # Create a test file
        test_content = "This is a test file for checksum validation"
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        # Test checksum
        checksum1 = compute_file_checksum(test_file, 'md5')
        checksum2 = compute_file_checksum(test_file, 'md5')
        
        if checksum1 == checksum2:
            print(f"✅ Checksum consistency passed: {checksum1}")
        else:
            print("❌ Checksum consistency failed")
            return False
        
        # Test with different content
        with open(test_file, 'w') as f:
            f.write(test_content + " modified")
        
        checksum3 = compute_file_checksum(test_file, 'md5')
        
        if checksum1 != checksum3:
            print("✅ Checksum change detection passed")
        else:
            print("❌ Checksum change detection failed")
            return False
        
        return True

def test_comparison_functions():
    """Test raster comparison functionality"""
    print("\n" + "="*50)
    print("Testing Raster Comparison")
    print("="*50)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        raster1 = Path(tmpdir) / "raster1.tif"
        raster2 = Path(tmpdir) / "raster2.tif"
        
        # Create identical test rasters
        if not create_test_raster(str(raster1)):
            return False
        if not create_test_raster(str(raster2)):
            return False
        
        # Compare identical rasters
        comparison = compare_raster_statistics(raster1, raster2)
        
        if comparison["compatible"]:
            print("✅ Identical raster comparison passed")
        else:
            print(f"❌ Identical raster comparison failed: {comparison['differences']}")
            return False
        
        # Create different raster
        if not create_test_raster(str(raster2), width=200, height=200):
            return False
        
        # Compare different rasters
        comparison2 = compare_raster_statistics(raster1, raster2)
        
        if not comparison2["compatible"] and "Different dimensions" in comparison2["differences"]:
            print("✅ Different raster comparison passed")
        else:
            print("❌ Different raster comparison failed")
            return False
        
        return True

def main():
    """Run all tests"""
    print("Forest Cover Raster Processing - Test Suite")
    print("=" * 80)
    
    tests = [
        ("Raster Validation", test_raster_validation),
        ("COG Creation", test_cog_creation),
        ("Label Standardization", test_label_standardization),
        ("Pixels to Labels", test_pixels_to_labels),
        ("File Operations", test_file_operations),
        ("Raster Comparison", test_comparison_functions),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results[test_name] = success
        except Exception as e:
            print(f"❌ {test_name} test crashed: {str(e)}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The implementation is ready for use.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
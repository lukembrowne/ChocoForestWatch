"""
COG Processing Utilities

Standalone utilities for converting GeoTIFFs to Cloud Optimized GeoTIFFs
and performing validation operations.
"""

import subprocess
import logging
from pathlib import Path
import rasterio
from rasterio.cog import cog_validate
from rasterio.enums import Resampling

logger = logging.getLogger(__name__)

class COGProcessor:
    """Utility class for COG processing operations."""
    
    def __init__(self, compression='LZW', tile_size=512, overview_resampling='nearest'):
        """
        Initialize COG processor with default settings.
        
        Args:
            compression (str): Compression method ('LZW', 'DEFLATE', 'JPEG', etc.)
            tile_size (int): Internal tile size (must be power of 2)
            overview_resampling (str): Resampling method for overviews
        """
        self.compression = compression
        self.tile_size = tile_size
        self.overview_resampling = overview_resampling
    
    def convert_to_cog(self, input_file, output_file=None, overwrite=False):
        """
        Convert a GeoTIFF to Cloud Optimized GeoTIFF format using rio cogeo.
        
        Args:
            input_file (str): Path to input GeoTIFF
            output_file (str): Path to output COG file (optional)
            overwrite (bool): Whether to overwrite existing output file
            
        Returns:
            str: Path to the output COG file
        """
        input_path = Path(input_file)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        # Generate output filename if not provided
        if output_file is None:
            output_file = input_path.with_suffix('.cog.tif')
        
        output_path = Path(output_file)
        
        # Check if output already exists
        if output_path.exists() and not overwrite:
            logger.warning(f"Output file already exists: {output_file}")
            return str(output_path)
        
        try:
            # Use rio cogeo to convert to COG
            cmd = [
                'rio', 'cogeo', 'create',
                '--blocksize', str(self.tile_size),
                '--compress', self.compression,
                '--overview-resampling', self.overview_resampling,
                '--overview-level', '2',
                '--overview-level', '4', 
                '--overview-level', '8',
                '--overview-level', '16',
                str(input_path),
                str(output_path)
            ]
            
            if overwrite:
                cmd.extend(['--overwrite'])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"COG conversion failed: {result.stderr}")
                raise RuntimeError(f"COG conversion failed: {result.stderr}")
            
            logger.info(f"Successfully converted to COG: {output_file}")
            return str(output_path)
            
        except FileNotFoundError:
            logger.error("rio cogeo not found. Please install rasterio with: pip install rasterio[cogeo]")
            raise
        except Exception as e:
            logger.error(f"COG conversion failed: {e}")
            raise
    
    def validate_cog(self, file_path):
        """
        Validate that a file is a proper Cloud Optimized GeoTIFF.
        
        Args:
            file_path (str): Path to the file to validate
            
        Returns:
            dict: Validation results with 'is_valid' and 'errors' keys
        """
        try:
            with rasterio.open(file_path) as src:
                is_valid, errors, warnings = cog_validate(src)
                
                result = {
                    'is_valid': is_valid,
                    'errors': errors,
                    'warnings': warnings
                }
                
                if is_valid:
                    logger.info(f"Valid COG: {file_path}")
                else:
                    logger.warning(f"Invalid COG: {file_path}")
                    for error in errors:
                        logger.warning(f"  Error: {error}")
                    for warning in warnings:
                        logger.warning(f"  Warning: {warning}")
                
                return result
                
        except Exception as e:
            logger.error(f"COG validation failed: {e}")
            return {
                'is_valid': False,
                'errors': [str(e)],
                'warnings': []
            }
    
    def validate_cog_cli(self, file_path):
        """
        Validate COG using command line rio cogeo validate.
        
        Args:
            file_path (str): Path to the file to validate
            
        Returns:
            bool: True if valid COG, False otherwise
        """
        try:
            result = subprocess.run(['rio', 'cogeo', 'validate', file_path], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Valid COG: {file_path}")
                return True
            else:
                logger.warning(f"Invalid COG: {file_path}")
                logger.warning(result.stdout)
                return False
                
        except FileNotFoundError:
            logger.error("rio cogeo not found. Please install rasterio with: pip install rasterio[cogeo]")
            return False
        except Exception as e:
            logger.error(f"COG validation failed: {e}")
            return False
    
    def add_overviews(self, input_file, levels=None, resampling=None):
        """
        Add overviews to a GeoTIFF file.
        
        Args:
            input_file (str): Path to input GeoTIFF
            levels (list): Overview levels to create
            resampling (str): Resampling method
        """
        if levels is None:
            levels = [2, 4, 8, 16]
        
        if resampling is None:
            resampling = self.overview_resampling
        
        try:
            with rasterio.open(input_file, 'r+') as src:
                # Check if overviews already exist
                if src.overviews(1):
                    logger.info(f"Overviews already exist for: {input_file}")
                    return
                
                # Add overviews
                src.build_overviews(levels, Resampling[resampling])
                src.update_tags(ns='rio_overview', resampling=resampling)
                
                logger.info(f"Added overviews to: {input_file}")
                
        except Exception as e:
            logger.error(f"Failed to add overviews: {e}")
            raise
    
    def batch_convert_to_cog(self, input_directory, output_directory=None, 
                           file_pattern="*.tif", overwrite=False):
        """
        Convert multiple GeoTIFFs to COGs in batch.
        
        Args:
            input_directory (str): Directory containing input GeoTIFFs
            output_directory (str): Directory for output COGs (optional)
            file_pattern (str): Pattern to match input files
            overwrite (bool): Whether to overwrite existing files
            
        Returns:
            list: List of successfully converted files
        """
        input_dir = Path(input_directory)
        
        if not input_dir.exists():
            raise FileNotFoundError(f"Input directory not found: {input_directory}")
        
        # Use same directory for output if not specified
        if output_directory is None:
            output_dir = input_dir
        else:
            output_dir = Path(output_directory)
            output_dir.mkdir(exist_ok=True)
        
        # Find all matching files
        input_files = list(input_dir.glob(file_pattern))
        
        if not input_files:
            logger.warning(f"No files found matching pattern: {file_pattern}")
            return []
        
        converted_files = []
        
        for input_file in input_files:
            try:
                # Skip if already a COG
                if '.cog.' in input_file.name:
                    logger.info(f"Skipping COG file: {input_file}")
                    continue
                
                # Generate output filename
                output_file = output_dir / f"{input_file.stem}.cog.tif"
                
                # Convert to COG
                result = self.convert_to_cog(str(input_file), str(output_file), overwrite)
                converted_files.append(result)
                
            except Exception as e:
                logger.error(f"Failed to convert {input_file}: {e}")
                continue
        
        logger.info(f"Successfully converted {len(converted_files)} files to COG")
        return converted_files

def main():
    """Example usage of COG processor."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert GeoTIFFs to COGs")
    parser.add_argument('input', help='Input GeoTIFF file or directory')
    parser.add_argument('-o', '--output', help='Output file or directory')
    parser.add_argument('--validate', action='store_true', help='Validate COG after conversion')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing files')
    parser.add_argument('--batch', action='store_true', help='Process directory in batch mode')
    
    args = parser.parse_args()
    
    processor = COGProcessor()
    
    if args.batch:
        # Batch processing
        converted_files = processor.batch_convert_to_cog(
            args.input, 
            args.output, 
            overwrite=args.overwrite
        )
        
        if args.validate:
            for file_path in converted_files:
                processor.validate_cog(file_path)
    else:
        # Single file processing
        output_file = processor.convert_to_cog(
            args.input, 
            args.output, 
            overwrite=args.overwrite
        )
        
        if args.validate:
            processor.validate_cog(output_file)

if __name__ == "__main__":
    main()
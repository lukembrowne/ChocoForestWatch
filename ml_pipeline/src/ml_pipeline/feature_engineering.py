"""
ml_pipeline.feature_engineering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Feature engineering system for extracting derived features from satellite imagery bands.

This module provides a modular architecture for computing features like NDVI, NDWI,
spectral ratios, and temporal features that can be used alongside the base satellite bands
in machine learning models.

Classes
-------
FeatureExtractor : Abstract base class for all feature extractors
FeatureManager : Coordinates multiple feature extractors
NDVIExtractor : Computes Normalized Difference Vegetation Index
NDWIExtractor : Computes Normalized Difference Water Index
SpectralRatioExtractor : Computes various band ratios
TemporalExtractor : Extracts temporal features from dates

Dependencies
------------
numpy
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FeatureExtractor(ABC):
    """Abstract base class for all feature extractors.
    
    Each feature extractor should be able to:
    1. Extract features from raw pixel bands
    2. Provide feature names for interpretability
    3. Validate input data
    """
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def extract_features(self, X: np.ndarray) -> np.ndarray:
        """Extract features from raw pixel bands.
        
        Parameters
        ----------
        X : np.ndarray
            Input array of shape (n_pixels, n_bands) containing raw pixel values.
            For NICFI imagery, bands are typically [B, G, R, NIR] in that order.
        
        Returns
        -------
        np.ndarray
            Feature array of shape (n_pixels, n_features) containing extracted features.
        """
        pass
    
    @abstractmethod
    def get_feature_names(self) -> List[str]:
        """Return names of features this extractor produces.
        
        Returns
        -------
        List[str]
            List of feature names for interpretability and debugging.
        """
        pass
    
    def validate_input(self, X: np.ndarray) -> None:
        """Validate input array shape and content.
        
        Parameters
        ----------
        X : np.ndarray
            Input array to validate.
            
        Raises
        ------
        ValueError
            If input array is invalid.
        """
        if X.ndim != 2:
            raise ValueError(f"Input array must be 2D, got shape {X.shape}")
        
        if X.shape[1] < 4:
            raise ValueError(f"Input array must have at least 4 bands, got {X.shape[1]}")
        
        if np.any(np.isnan(X)) or np.any(np.isinf(X)):
            logger.warning("Input array contains NaN or infinite values")


class FeatureManager:
    """Coordinates multiple feature extractors and manages the feature pipeline.
    
    This class handles:
    1. Applying multiple feature extractors in sequence
    2. Concatenating base bands with derived features
    3. Providing feature names for the complete feature set
    4. Validating feature consistency
    """
    
    def __init__(self, feature_extractors: List[FeatureExtractor]):
        """Initialize the feature manager.
        
        Parameters
        ----------
        feature_extractors : List[FeatureExtractor]
            List of feature extractors to apply.
        """
        self.feature_extractors = feature_extractors
        self._validate_extractors()
    
    def _validate_extractors(self) -> None:
        """Validate that all extractors are properly configured."""
        extractor_names = [extractor.name for extractor in self.feature_extractors]
        if len(extractor_names) != len(set(extractor_names)):
            raise ValueError("Feature extractor names must be unique")
    
    def extract_all_features(self, X: np.ndarray) -> np.ndarray:
        """Extract all features and concatenate with base bands.
        
        Parameters
        ----------
        X : np.ndarray
            Input array of shape (n_pixels, n_bands) containing raw pixel values.
        
        Returns
        -------
        np.ndarray
            Feature array of shape (n_pixels, n_total_features) containing
            base bands plus all derived features.
        """
        # Start with base bands
        features = [X]
        
        # Apply each feature extractor
        for extractor in self.feature_extractors:
            try:
                extractor.validate_input(X)
                derived_features = extractor.extract_features(X)
                features.append(derived_features)
                logger.debug(f"Extracted {derived_features.shape[1]} features from {extractor.name}")
            except Exception as e:
                logger.error(f"Failed to extract features from {extractor.name}: {e}")
                raise
        
        # Concatenate all features
        result = np.concatenate(features, axis=1)
        # logger.info(f"Feature engineering complete: {X.shape[1]} base bands + "
        #            f"{result.shape[1] - X.shape[1]} derived features = {result.shape[1]} total features")
        
        return result
    
    def get_all_feature_names(self) -> List[str]:
        """Get names of all features including base bands.
        
        Returns
        -------
        List[str]
            List of all feature names in the order they appear in the feature array.
        """
        # Base band names (in NICFI order: B, G, R, NIR)
        names = ["blue", "green", "red", "nir"]
        
        # Add derived feature names
        for extractor in self.feature_extractors:
            names.extend(extractor.get_feature_names())
        
        return names
    
    def get_config(self) -> Dict[str, Any]:
        """Get configuration dictionary for serialization.
        
        Returns
        -------
        Dict[str, Any]
            Configuration dictionary containing extractor names and parameters.
        """
        return {
            "extractor_names": [extractor.name for extractor in self.feature_extractors],
            "n_extractors": len(self.feature_extractors),
            "feature_names": self.get_all_feature_names()
        }
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'FeatureManager':
        """Create FeatureManager from configuration dictionary.
        
        Parameters
        ----------
        config : Dict[str, Any]
            Configuration dictionary with extractor specifications.
            
        Returns
        -------
        FeatureManager
            Configured feature manager instance.
        """
        # This would need to be implemented based on how configs are structured
        # For now, return empty manager
        return cls([])


class NDVIExtractor(FeatureExtractor):
    """Extract Normalized Difference Vegetation Index (NDVI) from red and NIR bands.
    
    NDVI = (NIR - Red) / (NIR + Red)
    
    NDVI is a widely used vegetation index that ranges from -1 to 1:
    - Values near 1 indicate healthy vegetation
    - Values near 0 indicate bare soil or rock
    - Negative values often indicate water bodies
    """
    
    def __init__(self):
        super().__init__("NDVI")
    
    def extract_features(self, X: np.ndarray) -> np.ndarray:
        """Extract NDVI from red and NIR bands.
        
        Parameters
        ----------
        X : np.ndarray
            Input array of shape (n_pixels, n_bands) where bands are [B, G, R, NIR].
        
        Returns
        -------
        np.ndarray
            NDVI values of shape (n_pixels, 1).
        """
        # Extract red and NIR bands (NICFI order: B, G, R, NIR)
        red = X[:, 2].astype(np.float64)  # Red is index 2
        nir = X[:, 3].astype(np.float64)  # NIR is index 3
        
        # Calculate NDVI with epsilon to avoid division by zero
        epsilon = 1e-8
        ndvi = (nir - red) / (nir + red + epsilon)
        
        # Clip to valid range
        ndvi = np.clip(ndvi, -1.0, 1.0)
        
        return ndvi.reshape(-1, 1)
    
    def get_feature_names(self) -> List[str]:
        """Return feature names."""
        return ["ndvi"]


class NDWIExtractor(FeatureExtractor):
    """Extract Normalized Difference Water Index (NDWI) from green and NIR bands.
    
    NDWI = (Green - NIR) / (Green + NIR)
    
    NDWI is used to detect water bodies and ranges from -1 to 1:
    - Positive values indicate water bodies
    - Negative values indicate vegetation and dry surfaces
    """
    
    def __init__(self):
        super().__init__("NDWI")
    
    def extract_features(self, X: np.ndarray) -> np.ndarray:
        """Extract NDWI from green and NIR bands.
        
        Parameters
        ----------
        X : np.ndarray
            Input array of shape (n_pixels, n_bands) where bands are [B, G, R, NIR].
        
        Returns
        -------
        np.ndarray
            NDWI values of shape (n_pixels, 1).
        """
        # Extract green and NIR bands (NICFI order: B, G, R, NIR)
        green = X[:, 1].astype(np.float64)  # Green is index 1
        nir = X[:, 3].astype(np.float64)    # NIR is index 3
        
        # Calculate NDWI with epsilon to avoid division by zero
        epsilon = 1e-8
        ndwi = (green - nir) / (green + nir + epsilon)
        
        # Clip to valid range
        ndwi = np.clip(ndwi, -1.0, 1.0)
        
        return ndwi.reshape(-1, 1)
    
    def get_feature_names(self) -> List[str]:
        """Return feature names."""
        return ["ndwi"]


class SpectralRatioExtractor(FeatureExtractor):
    """Extract various spectral ratios from satellite bands.
    
    Computes useful band ratios that can help distinguish different land cover types.
    """
    
    def __init__(self, ratios: Optional[List[str]] = None):
        """Initialize spectral ratio extractor.
        
        Parameters
        ----------
        ratios : Optional[List[str]]
            List of ratio names to compute. If None, computes default ratios.
            Available ratios: 'red_nir', 'green_red', 'blue_red', 'nir_green'
        """
        super().__init__("SpectralRatio")
        self.ratios = ratios or ['red_nir', 'green_red', 'nir_green']
    
    def extract_features(self, X: np.ndarray) -> np.ndarray:
        """Extract spectral ratios.
        
        Parameters
        ----------
        X : np.ndarray
            Input array of shape (n_pixels, n_bands) where bands are [B, G, R, NIR].
        
        Returns
        -------
        np.ndarray
            Spectral ratio values of shape (n_pixels, n_ratios).
        """
        features = []
        epsilon = 1e-8
        
        # Extract bands (NICFI order: B, G, R, NIR)
        blue = X[:, 0].astype(np.float64)   # Blue is index 0
        green = X[:, 1].astype(np.float64)  # Green is index 1
        red = X[:, 2].astype(np.float64)    # Red is index 2
        nir = X[:, 3].astype(np.float64)    # NIR is index 3
        
        for ratio in self.ratios:
            if ratio == 'red_nir':
                features.append(red / (nir + epsilon))
            elif ratio == 'green_red':
                features.append(green / (red + epsilon))
            elif ratio == 'blue_red':
                features.append(blue / (red + epsilon))
            elif ratio == 'nir_green':
                features.append(nir / (green + epsilon))
            else:
                logger.warning(f"Unknown ratio type: {ratio}")
        
        return np.column_stack(features)
    
    def get_feature_names(self) -> List[str]:
        """Return feature names."""
        return [f"ratio_{ratio}" for ratio in self.ratios]


class TemporalExtractor(FeatureExtractor):
    """Extract temporal features from dates.
    
    Extracts cyclical temporal features that can capture seasonal patterns.
    """
    
    def __init__(self):
        super().__init__("Temporal")
    
    def extract_features(self, X: np.ndarray, dates: Optional[np.ndarray] = None) -> np.ndarray:
        """Extract temporal features from dates.
        
        Parameters
        ----------
        X : np.ndarray
            Input array of shape (n_pixels, n_bands) - used for shape reference.
        dates : Optional[np.ndarray]
            Array of date strings of shape (n_pixels,).
        
        Returns
        -------
        np.ndarray
            Temporal features of shape (n_pixels, n_temporal_features).
        """
        if dates is None:
            # Return zeros if no dates provided
            return np.zeros((X.shape[0], 4))
        
        features = []
        
        for date_str in dates:
            if not date_str:
                # Handle empty date strings
                features.append([0.0, 0.0, 0.0, 0.0])
                continue
                
            try:
                # Parse date string (assumes YYYY-MM format)
                year, month = date_str.split('-')[:2]
                year = int(year)
                month = int(month)
                
                # Create cyclical features
                month_sin = np.sin(2 * np.pi * month / 12)
                month_cos = np.cos(2 * np.pi * month / 12)
                
                # Normalize year (assuming years around 2020-2025)
                year_norm = (year - 2020) / 10.0
                
                # Day of year approximation
                day_of_year = month * 30  # Rough approximation
                day_sin = np.sin(2 * np.pi * day_of_year / 365)
                
                features.append([month_sin, month_cos, year_norm, day_sin])
                
            except (ValueError, IndexError):
                # Handle invalid date strings
                features.append([0.0, 0.0, 0.0, 0.0])
        
        return np.array(features)
    
    def get_feature_names(self) -> List[str]:
        """Return feature names."""
        return ["month_sin", "month_cos", "year_norm", "day_sin"]


class EviExtractor(FeatureExtractor):
    """Extract Enhanced Vegetation Index (EVI) from blue, red, and NIR bands.
    
    EVI = 2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)
    
    EVI is superior to NDVI for:
    - Reducing atmospheric effects through the blue band correction
    - Better performance in dense vegetation areas where NDVI saturates
    - More sensitive to canopy structural variations
    - Improved accuracy in tropical forest monitoring
    """
    
    def __init__(self):
        super().__init__("EVI")
    
    def extract_features(self, X: np.ndarray) -> np.ndarray:
        """Extract EVI from blue, red, and NIR bands.
        
        Parameters
        ----------
        X : np.ndarray
            Input array of shape (n_pixels, n_bands) where bands are [B, G, R, NIR].
        
        Returns
        -------
        np.ndarray
            EVI values of shape (n_pixels, 1).
        """
        # Extract bands (NICFI order: B, G, R, NIR)
        blue = X[:, 0].astype(np.float64)   # Blue is index 0
        red = X[:, 2].astype(np.float64)    # Red is index 2
        nir = X[:, 3].astype(np.float64)    # NIR is index 3
        
        # Calculate EVI with atmospheric correction
        epsilon = 1e-8
        numerator = 2.5 * (nir - red)
        denominator = nir + 6*red - 7.5*blue + 1 + epsilon
        evi = numerator / denominator
        
        # Clip to reasonable range (EVI typically ranges from -1 to 1)
        evi = np.clip(evi, -1.0, 1.0)
        
        return evi.reshape(-1, 1)
    
    def get_feature_names(self) -> List[str]:
        """Return feature names."""
        return ["evi"]


class SaviExtractor(FeatureExtractor):
    """Extract Soil-Adjusted Vegetation Index (SAVI) from red and NIR bands.
    
    SAVI = (NIR - Red) / (NIR + Red + L) * (1 + L)
    
    SAVI is valuable for:
    - Reducing soil background effects in sparse vegetation
    - Better performance in arid and semi-arid regions
    - Distinguishing between bare soil and low vegetation cover
    - Improved accuracy in early growth stage vegetation detection
    """
    
    def __init__(self, L: float = 0.5):
        """Initialize SAVI extractor.
        
        Parameters
        ----------
        L : float, default=0.5
            Soil brightness correction factor:
            - L=0 for dense vegetation (equivalent to NDVI)
            - L=0.5 for intermediate vegetation density
            - L=1 for sparse vegetation
        """
        super().__init__("SAVI")
        self.L = L
    
    def extract_features(self, X: np.ndarray) -> np.ndarray:
        """Extract SAVI from red and NIR bands.
        
        Parameters
        ----------
        X : np.ndarray
            Input array of shape (n_pixels, n_bands) where bands are [B, G, R, NIR].
        
        Returns
        -------
        np.ndarray
            SAVI values of shape (n_pixels, 1).
        """
        # Extract red and NIR bands (NICFI order: B, G, R, NIR)
        red = X[:, 2].astype(np.float64)    # Red is index 2
        nir = X[:, 3].astype(np.float64)    # NIR is index 3
        
        # Calculate SAVI with soil adjustment
        epsilon = 1e-8
        numerator = (nir - red) * (1 + self.L)
        denominator = nir + red + self.L + epsilon
        savi = numerator / denominator
        
        # Clip to valid range
        savi = np.clip(savi, -1.0, 1.0)
        
        return savi.reshape(-1, 1)
    
    def get_feature_names(self) -> List[str]:
        """Return feature names."""
        return ["savi"]


class BrightnessTempExtractor(FeatureExtractor):
    """Extract brightness temperature and textural features from NIR band.
    
    Computes:
    - Brightness: Overall reflectance intensity
    - Texture proxies: Local standard deviation to capture surface roughness
    
    These features help distinguish:
    - Urban areas (high brightness, high texture)
    - Water bodies (low brightness, low texture)
    - Forest canopy (moderate brightness, high texture from shadows)
    - Agricultural fields (variable brightness, low-moderate texture)
    """
    
    def __init__(self, texture_window: int = 3):
        """Initialize brightness and texture extractor.
        
        Parameters
        ----------
        texture_window : int, default=3
            Window size for texture calculation (not implemented for pixel-level data).
        """
        super().__init__("BrightnessTexture")
        self.texture_window = texture_window
    
    def extract_features(self, X: np.ndarray) -> np.ndarray:
        """Extract brightness and texture features.
        
        Parameters
        ----------
        X : np.ndarray
            Input array of shape (n_pixels, n_bands) where bands are [B, G, R, NIR].
        
        Returns
        -------
        np.ndarray
            Brightness and texture features of shape (n_pixels, 3).
        """
        # Extract all bands for brightness calculation
        blue = X[:, 0].astype(np.float64)
        green = X[:, 1].astype(np.float64)
        red = X[:, 2].astype(np.float64)
        nir = X[:, 3].astype(np.float64)
        
        # Overall brightness (mean of all bands)
        brightness = (blue + green + red + nir) / 4.0
        
        # NIR brightness (important for vegetation analysis)
        nir_brightness = nir
        
        # Spectral variability as texture proxy
        # Calculate standard deviation across bands for each pixel
        band_stack = np.column_stack([blue, green, red, nir])
        spectral_variance = np.std(band_stack, axis=1)
        
        features = np.column_stack([brightness, nir_brightness, spectral_variance])
        
        return features
    
    def get_feature_names(self) -> List[str]:
        """Return feature names."""
        return ["brightness", "nir_brightness", "spectral_variance"]

class WaterDetectionExtractor(FeatureExtractor):
    """Extract water detection indices for comprehensive water body identification.
    
    Computes:
    - Blue-NIR ratio: Simple but effective water detector
    
    These indices excel at:
    - Distinguishing water from shadows and dark surfaces
    - Detecting water under various atmospheric conditions
    - Separating permanent water from seasonal flooding
    - Identifying small water bodies and streams
    """
    
    def __init__(self):
        super().__init__("WaterDetection")
    
    def extract_features(self, X: np.ndarray) -> np.ndarray:
        """Extract water detection indices.
        
        Parameters
        ----------
        X : np.ndarray
            Input array of shape (n_pixels, n_bands) where bands are [B, G, R, NIR].
        
        Returns
        -------
        np.ndarray
            Water detection indices of shape (n_pixels, 3).
        """
        # Extract bands (NICFI order: B, G, R, NIR)
        blue = X[:, 0].astype(np.float64)
        green = X[:, 1].astype(np.float64)
        red = X[:, 2].astype(np.float64)
        nir = X[:, 3].astype(np.float64)
        
        epsilon = 1e-8
        
        # Blue-NIR ratio: Simple but effective water detector
        blue_nir_ratio = blue / (nir + epsilon)
        # Normalize using log transform to handle wide range
        blue_nir_log = np.log1p(blue_nir_ratio)  # log(1 + x) for numerical stability
        blue_nir_norm = np.tanh(blue_nir_log)  # Normalize to [-1, 1]
        
        features = np.column_stack([blue_nir_norm])
        
        return features
    
    def get_feature_names(self) -> List[str]:
        """Return feature names."""
        return ["blue_nir_water"]


class ShadowIndexExtractor(FeatureExtractor):
    """Extract shadow detection indices for improved classification accuracy.
    
    Computes shadow indices that help distinguish:
    - Topographic shadows in mountainous areas
    - Cloud shadows that can mask actual land cover
    - Building shadows in urban areas
    
    Proper shadow detection improves classification by:
    - Reducing misclassification of shadows as water
    - Enabling shadow-corrected vegetation analysis
    - Improving urban area delineation
    """
    
    def __init__(self):
        super().__init__("ShadowIndex")
    
    def extract_features(self, X: np.ndarray) -> np.ndarray:
        """Extract shadow detection indices.
        
        Parameters
        ----------
        X : np.ndarray
            Input array of shape (n_pixels, n_bands) where bands are [B, G, R, NIR].
        
        Returns
        -------
        np.ndarray
            Shadow indices of shape (n_pixels, 2).
        """
        # Extract bands (NICFI order: B, G, R, NIR)
        blue = X[:, 0].astype(np.float64)
        green = X[:, 1].astype(np.float64)
        red = X[:, 2].astype(np.float64)
        nir = X[:, 3].astype(np.float64)
        
        # Shadow index 1: Low overall brightness with consistent low values across bands
        total_brightness = blue + green + red + nir
        shadow_index1 = 1.0 / (total_brightness + 1e-8)  # Inverse brightness
        shadow_index1 = np.tanh(shadow_index1)  # Normalize
        
        # Shadow index 2: Blue-dominated spectral signature (shadows often appear bluish)
        blue_dominance = blue / (red + nir + 1e-8)
        shadow_index2 = np.tanh(blue_dominance / 2.0)  # Normalize
        
        features = np.column_stack([shadow_index1, shadow_index2])
        
        return features
    
    def get_feature_names(self) -> List[str]:
        """Return feature names."""
        return ["shadow_brightness", "shadow_blue_dom"]
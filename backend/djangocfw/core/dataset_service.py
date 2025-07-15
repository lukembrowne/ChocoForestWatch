"""
Dataset Service for JSON-based Configuration

This module provides utilities to load and serve dataset configuration
from the datasets.json file instead of a database.
"""

import json
import os
from typing import List, Dict, Optional
from pathlib import Path


class DatasetService:
    """Service for managing datasets from JSON configuration."""
    
    def __init__(self):
        self._datasets = None
        self._config_path = Path(__file__).parent / 'datasets.json'
    
    def _load_datasets(self) -> List[Dict]:
        """Load datasets from JSON file."""
        if self._datasets is None:
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self._datasets = config.get('datasets', [])
            except (FileNotFoundError, json.JSONDecodeError) as e:
                raise Exception(f"Failed to load datasets configuration: {str(e)}")
        
        return self._datasets
    
    def get_all_datasets(self) -> List[Dict]:
        """Get all datasets from configuration."""
        return self._load_datasets()
    
    def get_enabled_datasets(self, dataset_type: Optional[str] = None) -> List[Dict]:
        """Get enabled datasets, optionally filtered by type."""
        datasets = self._load_datasets()
        enabled = [d for d in datasets if d.get('enabled', True)]
        
        if dataset_type:
            enabled = [d for d in enabled if d.get('type') == dataset_type]
        
        return enabled
    
    def get_dataset_by_collection_id(self, collection_id: str) -> Optional[Dict]:
        """Get a specific dataset by collection ID."""
        datasets = self._load_datasets()
        for dataset in datasets:
            if dataset.get('collection_id') == collection_id:
                return dataset
        return None
    
    def get_enabled_collection_ids(self, dataset_type: Optional[str] = None) -> List[str]:
        """Get list of enabled collection IDs, optionally filtered by type."""
        enabled_datasets = self.get_enabled_datasets(dataset_type)
        return [d['collection_id'] for d in enabled_datasets]
    
    def get_expression_mapping(self) -> Dict[str, str]:
        """Get mapping of collection_id to TiTiler expression."""
        datasets = self.get_enabled_datasets()
        mapping = {}
        
        for dataset in datasets:
            expression = dataset.get('expression', '')
            if expression:
                mapping[dataset['collection_id']] = expression
        
        return mapping
    
    def get_datasets_by_type(self, dataset_type: str) -> List[Dict]:
        """Get all enabled datasets of a specific type."""
        return self.get_enabled_datasets(dataset_type)
    
    def is_valid_collection_id(self, collection_id: str) -> bool:
        """Check if a collection ID is valid and enabled."""
        return collection_id in self.get_enabled_collection_ids()
    
    def reload_config(self):
        """Force reload of the configuration from file."""
        self._datasets = None


# Global instance
dataset_service = DatasetService()


# Convenience functions for backward compatibility
def get_all_datasets():
    """Get all datasets from configuration."""
    return dataset_service.get_all_datasets()


def get_enabled_datasets(dataset_type=None):
    """Get enabled datasets, optionally filtered by type."""
    return dataset_service.get_enabled_datasets(dataset_type)


def get_enabled_collection_ids(dataset_type=None):
    """Get list of enabled collection IDs."""
    return dataset_service.get_enabled_collection_ids(dataset_type)


def get_expression_mapping():
    """Get mapping of collection_id to TiTiler expression."""
    return dataset_service.get_expression_mapping()


def is_valid_collection_id(collection_id):
    """Check if a collection ID is valid and enabled."""
    return dataset_service.is_valid_collection_id(collection_id)
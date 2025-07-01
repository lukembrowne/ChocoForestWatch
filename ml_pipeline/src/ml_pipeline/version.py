"""Version information for ML Pipeline."""

from datetime import datetime
import importlib.metadata

def get_pipeline_version():
    """Get the ML pipeline version from package metadata."""
    try:
        return importlib.metadata.version("ml-pipeline")
    except importlib.metadata.PackageNotFoundError:
        return "0.1.0"  # fallback version

def get_version_metadata():
    """Get version metadata for STAC items and collections."""
    return {
        "pipeline_version": get_pipeline_version(),
        "created_at": datetime.utcnow().isoformat() + "Z",
        "software": f"ChocoForestWatch ML Pipeline v{get_pipeline_version()}"
    }

__version__ = get_pipeline_version()
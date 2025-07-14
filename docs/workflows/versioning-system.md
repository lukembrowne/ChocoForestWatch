# Versioning System Update Guide

This document provides comprehensive instructions for updating and maintaining the ChocoForestWatch versioning system.

## Overview

ChocoForestWatch uses a dual versioning approach:
- **Application Versioning**: Semantic versioning for the entire application (e.g., 0.1.0)
- **Dataset Versioning**: Year-based versioning for datasets and models (e.g., 2024.01.0)

## Application Version Updates

### When to Update Application Version

- **MAJOR** (X.0.0): Breaking changes, incompatible API changes
- **MINOR** (0.X.0): New features, backward-compatible functionality
- **PATCH** (0.0.X): Bug fixes, minor improvements

### Step-by-Step Application Version Update

#### 1. Update Version Files

Update the version in all three locations:

**Frontend** (`frontend/package.json`):
```json
{
  "version": "0.2.0"
}
```

**Backend** (`backend/djangocfw/djangocfw/version.py`):
```python
VERSION = (0, 2, 0, 'final')
```

**ML Pipeline** (`ml_pipeline/pyproject.toml`):
```toml
[project]
version = "0.2.0"

[tool.poetry]
version = "0.2.0"
```

#### 2. Update Changelog

Add entry to `CHANGELOG.md`:
```markdown
## [0.2.0] - 2025-01-15

### Added
- New forest cover analysis features
- Enhanced dataset selection interface

### Changed
- Improved prediction accuracy algorithms
- Updated STAC collection metadata format

### Fixed
- Resolved memory issues in large area processing
```

#### 3. Verify Version Synchronization

Run this command to check all versions match:
```bash
# Check frontend version
grep '"version"' frontend/package.json

# Check backend version  
python -c "
import sys
sys.path.append('backend/djangocfw')
from djangocfw.version import __version__
print(f'Backend: {__version__}')
"

# Check ML pipeline version
grep 'version =' ml_pipeline/pyproject.toml
```

## Dataset Version Updates

### Dataset Version Format

**Format**: `YYYY.MM.patch`
- `YYYY`: Target prediction year (e.g., 2024)
- `MM`: Model iteration for that year (01, 02, 03...)
- `patch`: Minor corrections (0, 1, 2...)

**Examples**:
- `2024.01.0`: First model version for 2024 predictions
- `2024.01.1`: Minor correction to 2024.01.0
- `2024.02.0`: Second model iteration for 2024

### Updating Dataset Versions

#### 1. Update ML Pipeline Version Metadata

**File**: `ml_pipeline/src/ml_pipeline/version.py`

Add or update dataset version tracking:
```python
def get_dataset_version(year, model_iteration=1, patch=0):
    """Generate dataset version string."""
    return f"{year}.{model_iteration:02d}.{patch}"

def get_version_metadata(dataset_version=None):
    """Get version metadata for STAC items and collections."""
    return {
        "pipeline_version": get_pipeline_version(),
        "dataset_version": dataset_version,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "software": f"ChocoForestWatch ML Pipeline v{get_pipeline_version()}"
    }
```